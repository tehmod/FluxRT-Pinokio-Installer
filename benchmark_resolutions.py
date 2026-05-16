import argparse
import copy
import json
import math
import time
from pathlib import Path

import numpy as np


DEFAULT_RESOLUTIONS = (
    "384x384,512x512,640x640,768x768,1024x1024,"
    "432x240,576x320,720x400,864x480,1008x560,"
    "512x288,768x432,1024x576"
)
DEFAULT_DYNAMIC_AREAS = "0,0.25,1.0"


def parse_resolutions(raw: str) -> list[tuple[int, int]]:
    values = []
    for item in raw.replace("\n", ",").split(","):
        item = item.strip().lower()
        if not item:
            continue
        if "x" not in item:
            raise ValueError(f"Resolution must look like WIDTHxHEIGHT, got {item!r}")
        width_raw, height_raw = item.split("x", 1)
        width = int(width_raw.strip())
        height = int(height_raw.strip())
        if width <= 0 or height <= 0:
            raise ValueError(f"Resolution must be positive, got {item!r}")
        if width % 16 or height % 16:
            raise ValueError(
                f"{width}x{height} is not divisible by 16. FluxRT will resize internally; "
                "use exact multiples of 16 for clean comparisons."
            )
        values.append((width, height))
    if not values:
        raise ValueError("At least one resolution is required.")
    return values


def parse_dynamic_areas(raw: str) -> list[float]:
    values = []
    for item in raw.replace("\n", ",").split(","):
        item = item.strip()
        if not item:
            continue
        value = float(item)
        if value < 0 or value > 1:
            raise ValueError(f"Dynamic area must be between 0 and 1, got {value}")
        values.append(value)
    if not values:
        raise ValueError("At least one dynamic area is required.")
    return values


def wait_for_ready(stream_processor, timeout: float) -> float:
    start = time.perf_counter()
    while not stream_processor.is_ready():
        if time.perf_counter() - start > timeout:
            raise TimeoutError(f"StreamProcessor did not become ready within {timeout:.1f}s")
        time.sleep(0.1)
    return time.perf_counter() - start


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def measure_dynamic_area(
    stream_processor,
    input_tensor,
    output_tensor,
    width: int,
    height: int,
    dynamic_area: float,
    seconds: float,
    sample_delay: float,
) -> dict:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    dynamic_width = int(width * dynamic_area)
    deadline = time.perf_counter() + seconds
    processing_times = []
    fps_values = []
    loops = 0

    while time.perf_counter() < deadline:
        loops += 1
        if dynamic_width > 0:
            frame[:, :dynamic_width, :] = (loops * 16) % 256
        input_tensor.copy_from(frame)
        output_tensor.to_numpy()
        processing_time = float(stream_processor.get_last_processing_time())
        if math.isfinite(processing_time) and processing_time > 0:
            processing_times.append(processing_time)
            fps = 1.0 / processing_time
            fps *= 2 ** stream_processor.config.get("interpolation_exp", 0)
            fps_values.append(fps)
        if sample_delay > 0:
            time.sleep(sample_delay)

    return {
        "dynamic_area": dynamic_area,
        "loops": loops,
        "samples": len(processing_times),
        "processing_time_s": average(processing_times),
        "fps": average(fps_values),
    }


def measure_latency(stream_processor, input_tensor, output_tensor, width: int, height: int) -> float | None:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, : width // 2, :] = 255
    input_tensor.copy_from(frame)
    stream_processor.set_prompt("Repeat the image")

    baseline = None
    for _ in range(120):
        baseline = output_tensor.to_numpy().copy()
        time.sleep(0.01)

    if baseline is None:
        return None

    roi_end = min(width, width // 2 + 80)
    roi = np.s_[:, width // 2 + 4 : roi_end, :]
    baseline_roi = baseline[roi].astype(np.int16)
    if baseline_roi.size == 0:
        return None

    frame[:, : width // 2 + 16, :] = 255
    start = time.perf_counter()
    input_tensor.copy_from(frame)
    while time.perf_counter() - start <= 10:
        processed_frame = output_tensor.to_numpy()
        changed_roi = processed_frame[roi].astype(np.int16)
        mean_delta = float(np.mean(np.abs(changed_roi - baseline_roi)))
        if mean_delta > 8.0:
            return time.perf_counter() - start
        time.sleep(0.001)
    return None


def run_one_resolution(args, base_config: dict, width: int, height: int, temp_config: Path) -> dict:
    from fluxrt import StreamProcessor

    config = copy.deepcopy(base_config)
    config["resolution"] = {"height": height, "width": width}
    config["use_reference_image"] = False
    config["logging"] = False
    if args.no_compile:
        config["compile_models"] = False
    if args.no_spatial_cache:
        config["enable_spatial_cache"] = False

    temp_config.write_text(json.dumps(config, indent=2), encoding="utf-8")
    stream_processor = None
    started_at = time.perf_counter()

    try:
        stream_processor = StreamProcessor(str(temp_config))
        input_tensor = stream_processor.get_input_tensor()
        output_tensor = stream_processor.get_output_tensor()
        if args.int8:
            stream_processor.enable_quantization()
        stream_processor.start()
        ready_time = wait_for_ready(stream_processor, args.ready_timeout)
        cold_ready_time = time.perf_counter() - started_at
        time.sleep(args.warmup)

        dynamic_results = [
            measure_dynamic_area(
                stream_processor,
                input_tensor,
                output_tensor,
                width,
                height,
                dynamic_area,
                args.seconds,
                args.sample_delay,
            )
            for dynamic_area in args.dynamic_areas
        ]
        latency = None
        if not args.skip_latency:
            latency = measure_latency(stream_processor, input_tensor, output_tensor, width, height)
        reserved_memory_gb = stream_processor.get_reserved_memory() / 1024

        return {
            "resolution": f"{width}x{height}",
            "width": width,
            "height": height,
            "pixels": width * height,
            "latent_tokens": (width // 16) * (height // 16),
            "ready_wait_s": ready_time,
            "cold_ready_s": cold_ready_time,
            "dynamic_results": dynamic_results,
            "latency_s": latency,
            "reserved_memory_gb": reserved_memory_gb,
            "error": None,
        }
    except Exception as exc:
        return {
            "resolution": f"{width}x{height}",
            "width": width,
            "height": height,
            "pixels": width * height,
            "latent_tokens": (width // 16) * (height // 16),
            "ready_wait_s": None,
            "cold_ready_s": time.perf_counter() - started_at,
            "dynamic_results": [],
            "latency_s": None,
            "reserved_memory_gb": None,
            "error": str(exc),
        }
    finally:
        if stream_processor is not None:
            try:
                stream_processor.stop()
            except Exception as stop_exc:
                print(f"Warning: failed to stop StreamProcessor cleanly: {stop_exc}")
        try:
            temp_config.unlink()
        except FileNotFoundError:
            pass
        time.sleep(args.cooldown)


def fmt(value, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def build_report(args, base_config: dict, hardware_info: dict, results: list[dict]) -> str:
    include_latency = not args.skip_latency
    lines = []
    lines.append("# FluxRT Resolution Benchmark\n")
    lines.append("## Sweep Settings\n")
    lines.append("```json")
    lines.append(
        json.dumps(
            {
                "resolutions": [result["resolution"] for result in results],
                "dynamic_areas": args.dynamic_areas,
                "seconds_per_dynamic_area": args.seconds,
                "warmup_seconds": args.warmup,
                "sample_delay_seconds": args.sample_delay,
                "int8": args.int8,
                "latency_enabled": not args.skip_latency,
                "compile_models": not args.no_compile and base_config.get("compile_models", False),
                "spatial_cache": not args.no_spatial_cache
                and base_config.get("enable_spatial_cache", False),
            },
            indent=2,
        )
    )
    lines.append("```\n")

    lines.append("## Base Configuration\n")
    lines.append("```json")
    lines.append(json.dumps(base_config, indent=2, default=str))
    lines.append("```\n")

    lines.append("## Hardware Information\n")
    lines.append("```json")
    lines.append(json.dumps(hardware_info, indent=2, default=str))
    lines.append("```\n")

    area_labels = [f"{area * 100:.0f}% FPS" for area in args.dynamic_areas]
    headers = [
        "Resolution",
        "Pixels",
        "Latent Tokens",
        "Cold Ready (s)",
        *area_labels,
        "VRAM (GB)",
        "Error",
    ]
    if include_latency:
        headers.insert(-2, "Visual Latency Probe (s)")
    lines.append("## Results\n")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---:" for _ in headers]) + "|")

    for result in results:
        fps_by_area = {
            dynamic_result["dynamic_area"]: dynamic_result["fps"]
            for dynamic_result in result["dynamic_results"]
        }
        row = [
            result["resolution"],
            str(result["pixels"]),
            str(result["latent_tokens"]),
            fmt(result["cold_ready_s"]),
            *[fmt(fps_by_area.get(area), 2) for area in args.dynamic_areas],
            fmt(result["reserved_memory_gb"]),
            result["error"] or "",
        ]
        if include_latency:
            row.insert(-2, fmt(result["latency_s"]))
        lines.append("| " + " | ".join(row) + " |")

    if include_latency:
        lines.append("")
        lines.append(
            "Note: the visual latency probe watches for an output image change after an input change. "
            "It is experimental and can be fooled by generated content, interpolation, or cache behavior. "
            "Use FPS/processing-time columns for reliable throughput comparisons."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep FluxRT benchmark across resolutions.")
    parser.add_argument("--resolutions", default=DEFAULT_RESOLUTIONS)
    parser.add_argument("--dynamic-areas", default=DEFAULT_DYNAMIC_AREAS)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--warmup", type=float, default=4.0)
    parser.add_argument("--cooldown", type=float, default=2.0)
    parser.add_argument("--sample-delay", type=float, default=1 / 25)
    parser.add_argument("--ready-timeout", type=float, default=300.0)
    parser.add_argument("--int8", action="store_true")
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--no-spatial-cache", action="store_true")
    parser.add_argument("--skip-latency", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--json-output")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.resolutions = parse_resolutions(args.resolutions)
    args.dynamic_areas = parse_dynamic_areas(args.dynamic_areas)

    app_root = Path.cwd()
    base_config_path = app_root / "configs" / "benchmark_config.json"
    temp_config = app_root / "configs" / "_benchmark_resolution_sweep.json"
    base_config = json.loads(base_config_path.read_text(encoding="utf-8"))
    if not args.output or not args.json_output:
        mode_parts = ["int8" if args.int8 else "regular"]
        mode_parts.append("nocompile" if args.no_compile else "compile")
        mode_parts.append("nospatial" if args.no_spatial_cache else "spatial")
        mode_name = "_".join(mode_parts)
        if not args.output:
            args.output = f"benchmark_resolutions_{mode_name}.md"
        if not args.json_output:
            args.json_output = f"benchmark_resolutions_{mode_name}.json"

    print("Resolution sweep:")
    for width, height in args.resolutions:
        print(f"  - {width}x{height} ({(width // 16) * (height // 16)} latent tokens)")

    if args.dry_run:
        print("Dry run complete; no models were loaded.")
        return

    from fluxrt.utils.scan_hardware import scan_hardware

    hardware_info = scan_hardware()
    results = []
    for index, (width, height) in enumerate(args.resolutions, start=1):
        print(f"\n[{index}/{len(args.resolutions)}] Benchmarking {width}x{height}")
        result = run_one_resolution(args, base_config, width, height, temp_config)
        results.append(result)
        if result["error"]:
            print(f"  Error: {result['error']}")
        else:
            fps_summary = ", ".join(
                f"{item['dynamic_area'] * 100:.0f}%={fmt(item['fps'], 2)} FPS"
                for item in result["dynamic_results"]
            )
            summary_parts = [
                f"cold={fmt(result['cold_ready_s'])}s",
                fps_summary,
            ]
            if not args.skip_latency:
                summary_parts.append(f"visual latency probe={fmt(result['latency_s'])}s")
            summary_parts.append(f"vram={fmt(result['reserved_memory_gb'])} GB")
            print("  " + ", ".join(summary_parts))

    report = build_report(args, base_config, hardware_info, results)
    output_path = app_root / args.output
    json_output_path = app_root / args.json_output
    output_path.write_text(report, encoding="utf-8")
    json_output_path.write_text(
        json.dumps(
            {
                "hardware": hardware_info,
                "base_config": base_config,
                "results": results,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nReport saved to {output_path}")
    print(f"JSON saved to {json_output_path}")


if __name__ == "__main__":
    main()
