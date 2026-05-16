module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: ".",
        message: "set -euo pipefail\nif [ -d app ]; then\n  if [ -d app/.git ]; then\n    cd app\n    git fetch --all --prune\n    git reset --hard origin/main\n    git lfs install\n    git lfs pull\n    cd ..\n  else\n    echo 'ERROR: Existing app directory is not a git repo. Remove it and retry.'\n    exit 1\n  fi\nelse\n  git clone https://github.com/tensorforger/FluxRT app\nfi"
      }
    },
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        conda: {
          path: "env",
          python: "3.12"
        },
        path: "app",
        message: [
          "python -c \"import torch\" >/dev/null 2>&1 || pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128",
          "python -c \"import diffusers\" >/dev/null 2>&1 || pip install -r requirements.txt",
          "python -c \"import fluxrt\" >/dev/null 2>&1 || pip install -e ."
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: "app",
        message: [
          "git lfs install",
          "if [ -f RIFE-safetensors/flownet.safetensors ]; then echo 'RIFE-safetensors is already downloaded.'; elif [ -d RIFE-safetensors/.git ]; then cd RIFE-safetensors && git pull --ff-only && git lfs pull && cd ..; elif [ -d RIFE-safetensors ]; then echo 'ERROR: RIFE-safetensors exists but is incomplete. Remove it and retry.' && exit 1; else git clone https://huggingface.co/TensorForger/RIFE-safetensors RIFE-safetensors; fi",
          "if [ -f FLUX.2-klein-4B/transformer/diffusion_pytorch_model.safetensors ]; then echo 'FLUX.2-klein-4B is already downloaded.'; elif [ -d FLUX.2-klein-4B/.git ]; then cd FLUX.2-klein-4B && git pull --ff-only && git lfs pull && cd ..; elif [ -d FLUX.2-klein-4B ]; then echo 'ERROR: FLUX.2-klein-4B exists but is incomplete. Remove it and retry.' && exit 1; else git clone https://huggingface.co/black-forest-labs/FLUX.2-klein-4B FLUX.2-klein-4B; fi",
          "mkdir -p loras"
        ]
      }
    }
  ]
}
