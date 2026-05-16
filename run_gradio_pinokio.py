import argparse
import json
import math
from pathlib import Path
import threading
import time

import cv2
import gradio as gr
import gradio.brotli_middleware as gradio_brotli
import gradio.routes as gradio_routes
from safetensors import safe_open

from fluxrt import StreamProcessor
from fluxrt.utils import crop_maximal_rectangle


default_prompt = "Turn this image into cyberpunk night, red and blue neon lamps, bokeh"
STREAM_HEIGHT = 384
APP_CSS = """
.stream-frame {
    min-height: 384px;
}

.stream-frame img,
.stream-frame video {
    object-fit: contain;
}
"""

stream_processor = None
input_tensor = None
output_tensor = None
resolution = None
use_int8 = False
ROOT = Path(__file__).resolve().parent
APP_ROOT = ROOT / "app"
LORAS_DIR = APP_ROOT / "loras"
TRANSFORMER_CONFIG = APP_ROOT / "FLUX.2-klein-4B" / "transformer" / "config.json"
LIVEPORTRAIT_REQUIRED_FILES = [
    APP_ROOT / "LivePortrait" / "liveportrait" / "landmark.onnx",
    APP_ROOT / "LivePortrait" / "liveportrait" / "base_models" / "appearance_feature_extractor.pth",
    APP_ROOT / "LivePortrait" / "liveportrait" / "base_models" / "motion_extractor.pth",
    APP_ROOT / "LivePortrait" / "liveportrait" / "base_models" / "spade_generator.pth",
    APP_ROOT / "LivePortrait" / "liveportrait" / "base_models" / "warping_module.pth",
    APP_ROOT / "LivePortrait" / "liveportrait" / "retargeting_models" / "stitching_retargeting_module.pth",
    APP_ROOT / "LivePortrait" / "insightface" / "models" / "buffalo_l" / "det_10g.onnx",
]

processor_lock = threading.Lock()
current_video_id = 0
current_video_id_lock = threading.Lock()

local_current_frame = None
local_processed_frame = None
local_frame_lock = threading.Lock()


def is_lfs_pointer(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("rb") as f:
            return b"git-lfs.github.com/spec" in f.read(128)
    except OSError:
        return False


def has_liveportrait_models() -> bool:
    return all(path.is_file() and not is_lfs_pointer(path) for path in LIVEPORTRAIT_REQUIRED_FILES)


def list_loras():
    LORAS_DIR.mkdir(parents=True, exist_ok=True)
    return [
        str(path.relative_to(APP_ROOT))
        for path in sorted(LORAS_DIR.rglob("*.safetensors"))
        if path.is_file()
    ]


def expected_transformer_width() -> int | None:
    try:
        with TRANSFORMER_CONFIG.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        return int(cfg["attention_head_dim"]) * int(cfg["num_attention_heads"])
    except (OSError, KeyError, TypeError, ValueError):
        return None


def infer_lora_width(path: Path) -> int | None:
    dims = []
    with safe_open(path, framework="pt", device="cpu") as f:
        for key in f.keys():
            if "lora_" not in key:
                continue
            for dim in f.get_slice(key).get_shape():
                if dim > 512:
                    dims.append(int(dim))
    if not dims:
        return None
    return math.gcd(*dims)


def validate_lora(path: Path) -> str | None:
    if path.suffix.lower() != ".safetensors":
        return "LoRA files must use the .safetensors format."

    expected_width = expected_transformer_width()
    try:
        lora_width = infer_lora_width(path)
    except Exception as exc:
        return f"Could not inspect LoRA file: {exc}"

    if expected_width and lora_width and lora_width != expected_width:
        return (
            f"Incompatible LoRA width: this file appears to target a Flux transformer "
            f"width of {lora_width}, but FLUX.2-klein-4B uses {expected_width}. "
            "Use LoRAs trained for FLUX.2-klein-4B, not full-width FLUX.2/Flux-dev models."
        )
    return None


def disable_gradio_response_compression() -> None:
    class NoCompressionMiddleware:
        def __init__(self, app, *args, **kwargs):
            self.app = app

        async def __call__(self, scope, receive, send):
            async def send_without_content_length(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    message = {
                        **message,
                        "headers": [
                            (key, value)
                            for key, value in headers
                            if key.lower() != b"content-length"
                        ],
                    }
                await send(message)

            await self.app(scope, receive, send_without_content_length)

    gradio_brotli.BrotliMiddleware = NoCompressionMiddleware
    gradio_routes.BrotliMiddleware = NoCompressionMiddleware


def get_processor():
    global stream_processor, input_tensor, output_tensor, resolution

    if stream_processor is None:
        stream_processor = StreamProcessor("configs/config_with_reference.json")
        if has_liveportrait_models():
            stream_processor.config["lip_transfer"] = {
                "enable": True,
                "models_dir": "LivePortrait/liveportrait",
            }
        if use_int8:
            stream_processor.enable_quantization()
        stream_processor.start()
        stream_processor.set_prompt(default_prompt)

        input_tensor = stream_processor.get_input_tensor()
        output_tensor = stream_processor.get_output_tensor()
        resolution = stream_processor.get_resolution()

    return stream_processor, input_tensor, output_tensor, resolution


def to_bgr(frame):
    if frame is None:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def to_rgb(frame):
    if frame is None:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def runtime_status():
    sp, _, _, res = get_processor()
    cfg = sp.config
    status = {
        "resolution": res,
        "int8": use_int8,
        "spatial_cache": bool(cfg.get("enable_spatial_cache", False)),
        "steps": int(cfg.get("default_steps", 2)),
        "seed": int(cfg.get("default_seed", 52)),
        "reference_image": bool(cfg.get("use_reference_image", False)),
        "lip_transfer_available": has_liveportrait_models(),
        "loaded_lora": cfg.get("lora_weights_path"),
        "reserved_gpu_memory_mb": sp.get_reserved_memory(),
    }
    if hasattr(sp, "get_lora_status"):
        status["lora_status"] = sp.get_lora_status()
    return status


def process_frame(frame):
    _, input_tensor, output_tensor, resolution = get_processor()
    frame = crop_maximal_rectangle(frame, resolution["height"], resolution["width"])

    with processor_lock:
        input_tensor.copy_from(frame)
        processed = output_tensor.to_numpy()
    return frame, processed


def set_prompt(prompt: str):
    sp, _, _, _ = get_processor()
    sp.set_prompt(prompt)
    return {"prompt": prompt}


def apply_runtime_options(steps: int, seed: int, enable_spatial_cache: bool, enable_lip_transfer: bool):
    sp, _, _, _ = get_processor()
    steps = int(steps)
    seed = int(seed)
    sp.set_steps(steps)
    sp.set_seed(seed)
    sp.set_config_param("enable_spatial_cache", bool(enable_spatial_cache))
    sp.set_lip_transfer(bool(enable_lip_transfer))
    sp.config["default_steps"] = steps
    sp.config["default_seed"] = seed
    return runtime_status()


def refresh_loras():
    return gr.update(choices=list_loras()), runtime_status()


def load_lora(lora_path: str | None):
    sp, _, _, _ = get_processor()
    if not lora_path:
        return {"loaded_lora": None, "message": "No LoRA selected."}

    full_path = (APP_ROOT / lora_path).resolve()
    loras_root = LORAS_DIR.resolve()
    if not full_path.is_file() or loras_root not in full_path.parents:
        return {
            "loaded_lora": None,
            "error": "LoRA must be a .safetensors file inside app/loras.",
        }
    validation_error = validate_lora(full_path)
    if validation_error:
        status = runtime_status()
        status["loaded_lora"] = None
        status["error"] = validation_error
        return status

    sp.load_lora(str(full_path))
    status = runtime_status()
    status["message"] = "LoRA load requested. The next generated frames will use it once the worker applies the request."
    return status


def set_reference_image_ui(image):
    sp, _, _, _ = get_processor()
    sp.set_reference_image(image)
    return {"reference_image_set": image is not None}


def _video_loop(video_path: str, video_id: int):
    global local_current_frame, local_processed_frame
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_time = 1.0 / fps
    try:
        while True:
            with current_video_id_lock:
                if current_video_id != video_id:
                    break
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            start = time.time()
            input_frame, processed = process_frame(frame)
            with local_frame_lock:
                local_current_frame = to_rgb(input_frame)
                local_processed_frame = to_rgb(processed)
            time.sleep(max(0, frame_time - (time.time() - start)))
    finally:
        cap.release()


def start_local_video(video_path: str | None):
    global current_video_id, local_current_frame, local_processed_frame
    with current_video_id_lock:
        current_video_id += 1
        my_id = current_video_id
    with local_frame_lock:
        local_current_frame = None
        local_processed_frame = None
    if not video_path:
        return {"local_video": "cleared"}
    t = threading.Thread(target=_video_loop, args=(video_path, my_id), daemon=True)
    t.start()
    return {"local_video": video_path}


def poll_local_video():
    with local_frame_lock:
        return local_current_frame, local_processed_frame


def switch_mode(mode: str, request: gr.Request | None):
    global current_video_id, local_current_frame, local_processed_frame
    if mode == "webcam":
        with current_video_id_lock:
            current_video_id += 1
        with local_frame_lock:
            local_current_frame = None
            local_processed_frame = None

    webcam_visible = mode == "webcam"
    local_visible = mode == "local"
    return (
        gr.update(visible=webcam_visible),
        gr.update(visible=local_visible),
        gr.update(visible=webcam_visible),
        gr.update(visible=local_visible),
        gr.update(active=local_visible),
    )


def process_webcam(frame):
    if frame is None:
        return None

    _, processed = process_frame(to_bgr(frame))
    return to_rgb(processed)


def main():
    global use_int8
    parser = argparse.ArgumentParser(description="Run FluxRT Gradio demo for Pinokio.")
    parser.add_argument("--int8", action="store_true", help="Enable int8 quantization")
    parser.add_argument("--server-name", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=7860)
    args, _ = parser.parse_known_args()
    use_int8 = args.int8

    get_processor()
    cfg = stream_processor.config
    use_reference_image = cfg.get("use_reference_image", False)
    lip_transfer_available = has_liveportrait_models()
    disable_gradio_response_compression()

    with gr.Blocks(css=APP_CSS) as demo:
        mode = gr.Radio(
            choices=["webcam", "local"],
            value="webcam",
            label="Mode",
        )

        with gr.Column(visible=True) as webcam_output_col:
            webcam_output = gr.Image(
                label="Processed stream",
                height=STREAM_HEIGHT,
                elem_classes=["stream-frame"],
            )

        with gr.Column(visible=False) as local_output_col:
            local_output = gr.Image(
                label="Processed stream",
                height=STREAM_HEIGHT,
                elem_classes=["stream-frame"],
            )

        local_timer = gr.Timer(value=0.04, active=False)

        with gr.Row():
            with gr.Column(visible=True) as webcam_input_col:
                webcam_input = gr.Image(
                    sources=["webcam"],
                    streaming=True,
                    type="numpy",
                    label="Webcam",
                    height=STREAM_HEIGHT,
                    elem_classes=["stream-frame"],
                )

            with gr.Column(visible=False) as local_input_col:
                video_file = gr.File(
                    label="Choose local video",
                    file_count="single",
                    file_types=["video"],
                    type="filepath",
                )
                local_input = gr.Image(
                    label="Input stream",
                    height=STREAM_HEIGHT,
                    elem_classes=["stream-frame"],
                )

            prompt = gr.Textbox(
                value=default_prompt,
                label="Prompt",
                lines=3,
            )

            if use_reference_image:
                ref_image_input = gr.Image(
                    label="Reference Image",
                    type="numpy",
                    sources=["upload"],
                    image_mode="RGB",
                    height=STREAM_HEIGHT,
                    elem_classes=["stream-frame"],
                )

        with gr.Accordion("Runtime settings", open=False):
            with gr.Row():
                steps = gr.Slider(
                    minimum=1,
                    maximum=8,
                    step=1,
                    value=int(cfg.get("default_steps", 2)),
                    label="Steps",
                )
                seed = gr.Number(
                    value=int(cfg.get("default_seed", 52)),
                    precision=0,
                    label="Seed",
                )
                spatial_cache = gr.Checkbox(
                    value=bool(cfg.get("enable_spatial_cache", True)),
                    label="Spatial cache",
                )
                lip_transfer = gr.Checkbox(
                    value=False,
                    label="LivePortrait lips",
                    visible=lip_transfer_available,
                )
            apply_settings = gr.Button("Apply settings")
            refresh_status = gr.Button("Refresh status")
            settings_status = gr.JSON(label="Status", value=runtime_status())

        with gr.Accordion("LoRA", open=False):
            lora_select = gr.Dropdown(
                choices=list_loras(),
                label="LoRA file",
                interactive=True,
            )
            with gr.Row():
                refresh_lora_list = gr.Button("Refresh LoRAs")
                load_lora_button = gr.Button("Load LoRA")

        mode.change(
            switch_mode,
            inputs=mode,
            outputs=[
                webcam_output_col,
                local_output_col,
                webcam_input_col,
                local_input_col,
                local_timer,
            ],
            scroll_to_output=False,
            api_name="set_mode",
        )

        webcam_input.stream(
            process_webcam,
            inputs=webcam_input,
            outputs=[webcam_output],
            stream_every=0.04,
            concurrency_limit=1,
            scroll_to_output=False,
            api_name="process_webcam_frame",
        )

        video_file.change(
            start_local_video,
            inputs=video_file,
            outputs=[settings_status],
            scroll_to_output=False,
            api_name="start_local_video",
        )

        local_timer.tick(
            poll_local_video,
            outputs=[local_input, local_output],
            scroll_to_output=False,
        )

        prompt.change(
            set_prompt,
            inputs=prompt,
            outputs=[settings_status],
            scroll_to_output=False,
            api_name="set_prompt",
        )

        apply_settings.click(
            apply_runtime_options,
            inputs=[steps, seed, spatial_cache, lip_transfer],
            outputs=[settings_status],
            scroll_to_output=False,
            api_name="set_runtime_options",
        )

        refresh_status.click(
            runtime_status,
            outputs=[settings_status],
            scroll_to_output=False,
            api_name="get_runtime_status",
        )

        refresh_lora_list.click(
            refresh_loras,
            outputs=[lora_select, settings_status],
            scroll_to_output=False,
            api_name="list_loras",
        )

        load_lora_button.click(
            load_lora,
            inputs=lora_select,
            outputs=[settings_status],
            scroll_to_output=False,
            api_name="load_lora",
        )

        if use_reference_image:
            ref_image_input.change(
                set_reference_image_ui,
                inputs=ref_image_input,
                outputs=[settings_status],
                scroll_to_output=False,
                api_name="set_reference_image",
            )

    demo.queue(default_concurrency_limit=1).launch(
        server_name=args.server_name,
        server_port=args.server_port,
    )


if __name__ == "__main__":
    main()
