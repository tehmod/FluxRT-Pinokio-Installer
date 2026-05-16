import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"


def run(cmd, cwd=None, env=None):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def has_module(name):
    return subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def ensure_git_lfs():
    if shutil.which("git-lfs"):
        return
    run(["conda", "install", "-y", "-c", "conda-forge", "git-lfs"])


def is_real_file(path):
    path = Path(path)
    if not path.is_file():
        return False
    try:
        return b"git-lfs.github.com/spec" not in path.read_bytes()[:512]
    except OSError:
        return False


def migrate_nested_app():
    nested = APP / "app"
    for name in [
        "RIFE-safetensors",
        "FLUX.2-klein-4B",
        "FLUX.2-klein-4B-int8",
        "LivePortrait",
        "LivePortrait-code",
        "loras",
    ]:
        src = nested / name
        dst = APP / name
        if src.exists():
            if not dst.exists():
                print(f"Moving nested {src.relative_to(ROOT)} to {dst.relative_to(ROOT)}", flush=True)
                shutil.move(str(src), str(dst))
            else:
                print(f"WARNING: {src.relative_to(ROOT)} also exists; keeping both.", flush=True)
    if nested.is_dir() and not any(nested.iterdir()):
        nested.rmdir()


def clone_or_update_source(allow_clone):
    ensure_git_lfs()
    if (APP / ".git").is_dir():
        run(["git", "-C", "app", "fetch", "--all", "--prune"], cwd=ROOT)
        run(["git", "-C", "app", "reset", "--hard", "origin/main"], cwd=ROOT)
    elif APP.exists():
        raise SystemExit("ERROR: Existing app directory is not a git repo. Remove it and retry.")
    elif allow_clone:
        run(["git", "clone", "https://github.com/tensorforger/FluxRT", "app"], cwd=ROOT)
    else:
        raise SystemExit("ERROR: FluxRT is not installed. Run install first.")
    migrate_nested_app()
    run(["git-lfs", "install"], cwd=APP)
    run(["git-lfs", "pull"], cwd=APP)


def install_python_deps(full_install):
    if full_install and not has_module("torch"):
        run([
            sys.executable,
            "-m",
            "pip",
            "install",
            "torch",
            "torchvision",
            "--index-url",
            "https://download.pytorch.org/whl/cu128",
        ], cwd=APP)
    if not has_module("diffusers"):
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=APP)
    if not has_module("fluxrt"):
        run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=APP)


def sync_hf_repo(name, url, ready_file, lfs_args=None):
    ensure_git_lfs()
    repo = APP / name
    ready = APP / ready_file
    if is_real_file(ready):
        print(f"{name} is already downloaded.", flush=True)
        return
    if (repo / ".git").is_dir():
        run(["git", "pull", "--ff-only"], cwd=repo)
    elif repo.exists():
        raise SystemExit(f"ERROR: {name} exists but is incomplete. Remove it and retry.")
    else:
        env = os.environ.copy()
        env["GIT_LFS_SKIP_SMUDGE"] = "1"
        run(["git", "clone", url, name], cwd=APP, env=env)
    run(["git-lfs", "pull", *(lfs_args or [])], cwd=repo)
    if not is_real_file(ready):
        raise SystemExit(f"ERROR: {ready_file} is missing or still a Git LFS pointer.")


def install_models():
    sync_hf_repo(
        "RIFE-safetensors",
        "https://huggingface.co/TensorForger/RIFE-safetensors",
        "RIFE-safetensors/flownet.safetensors",
    )
    sync_hf_repo(
        "FLUX.2-klein-4B",
        "https://huggingface.co/black-forest-labs/FLUX.2-klein-4B",
        "FLUX.2-klein-4B/transformer/diffusion_pytorch_model.safetensors",
    )
    (APP / "loras").mkdir(exist_ok=True)
    run(["git-lfs", "install"], cwd=APP)
    run(["git-lfs", "pull"], cwd=APP)


def install_int8():
    sync_hf_repo(
        "FLUX.2-klein-4B-int8",
        "https://huggingface.co/aydin99/FLUX.2-klein-4B-int8",
        "FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors",
    )


def install_liveportrait():
    ensure_git_lfs()
    if not has_module("liveportrait"):
        run([sys.executable, "-m", "pip", "install", "-r", "requirements_lipsync.txt"], cwd=APP)
    code = APP / "LivePortrait-code"
    if (code / ".git").is_dir():
        run(["git", "pull", "--ff-only"], cwd=code)
    elif code.exists():
        raise SystemExit("ERROR: LivePortrait-code exists but is not a git repository. Remove it and retry.")
    else:
        run(["git", "clone", "https://github.com/KlingAIResearch/LivePortrait", "LivePortrait-code"], cwd=APP)
    sync_hf_repo(
        "LivePortrait",
        "https://huggingface.co/KwaiVGI/LivePortrait",
        "LivePortrait/liveportrait/landmark.onnx",
        ["--include=liveportrait/**,insightface/**"],
    )


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    if task == "source":
        clone_or_update_source(True)
        print("PINOKIO_FLUXRT_SOURCE_READY", flush=True)
    elif task == "deps":
        install_python_deps(True)
        print("PINOKIO_FLUXRT_DEPS_READY", flush=True)
    elif task == "models":
        install_models()
        print("PINOKIO_FLUXRT_MODELS_READY", flush=True)
    elif task == "update-source":
        clone_or_update_source(False)
        print("PINOKIO_FLUXRT_UPDATE_SOURCE_READY", flush=True)
    elif task == "update-deps":
        install_python_deps(False)
        install_models()
        print("PINOKIO_FLUXRT_UPDATE_DEPS_READY", flush=True)
    elif task == "migrate":
        migrate_nested_app()
        print("PINOKIO_FLUXRT_MIGRATION_READY", flush=True)
    elif task == "start-models":
        install_models()
        print("PINOKIO_FLUXRT_START_MODELS_READY", flush=True)
    elif task == "int8":
        install_int8()
        print("PINOKIO_FLUXRT_INT8_READY", flush=True)
    elif task == "liveportrait":
        install_liveportrait()
        print("PINOKIO_FLUXRT_LIVEPORTRAIT_READY", flush=True)
    else:
        raise SystemExit(f"Unknown task: {task}")


if __name__ == "__main__":
    main()
