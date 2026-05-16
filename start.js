module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: "app",
        message: [
          "set -euo pipefail",
          "command -v git-lfs >/dev/null 2>&1 || conda install -y -c conda-forge git-lfs",
          "if [ -f RIFE-safetensors/flownet.safetensors ]; then echo 'RIFE-safetensors is ready.'; elif [ -d RIFE-safetensors/.git ]; then cd RIFE-safetensors && git pull --ff-only && git-lfs pull && cd ..; elif [ -d RIFE-safetensors ]; then echo 'ERROR: RIFE-safetensors exists but is incomplete. Remove it and retry Install.' && exit 1; else GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/TensorForger/RIFE-safetensors RIFE-safetensors && cd RIFE-safetensors && git-lfs pull && cd ..; fi",
          "if [ -f FLUX.2-klein-4B/transformer/diffusion_pytorch_model.safetensors ]; then echo 'FLUX.2-klein-4B is ready.'; elif [ -d FLUX.2-klein-4B/.git ]; then cd FLUX.2-klein-4B && git pull --ff-only && git-lfs pull && cd ..; elif [ -d FLUX.2-klein-4B ]; then echo 'ERROR: FLUX.2-klein-4B exists but is incomplete. Remove it and retry Install.' && exit 1; else GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/black-forest-labs/FLUX.2-klein-4B FLUX.2-klein-4B && cd FLUX.2-klein-4B && git-lfs pull && cd ..; fi",
          "mkdir -p loras"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        conda: {
          path: "env",
          python: "3.12"
        },
        path: "app",
        message: [
          "python -c \"import torch\" >/dev/null 2>&1 || pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128",
          "python -c \"import cv2\" >/dev/null 2>&1 || pip install -r requirements.txt",
          "python -c \"import fluxrt\" >/dev/null 2>&1 || pip install -e .",
          "python ../patch_fluxrt.py",
          "python ../run_gradio_pinokio.py --server-name 127.0.0.1 --server-port {{port}} {{args.int8 ? '--int8' : ''}}"
        ],
        on: [{
          event: "/(http:\\/\\/[^\\s]+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    }
  ]
}
