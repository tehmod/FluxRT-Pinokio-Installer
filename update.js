module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: ".",
        message: [
          "set -euo pipefail",
          "command -v git-lfs >/dev/null 2>&1 || conda install -y -c conda-forge git-lfs",
          "if [ -d app/.git ]; then git -C app fetch --all --prune && git -C app reset --hard origin/main; else echo 'ERROR: FluxRT is not installed. Run install first.' && exit 1; fi",
          "cd app && git-lfs install && git-lfs pull && cd .."
        ]
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
          "set -euo pipefail",
          "command -v git-lfs >/dev/null 2>&1 || conda install -y -c conda-forge git-lfs",
          "python -c \"import diffusers\" >/dev/null 2>&1 || pip install -r requirements.txt",
          "python -c \"import fluxrt\" >/dev/null 2>&1 || pip install -e .",
          "if [ -f RIFE-safetensors/flownet.safetensors ]; then echo 'RIFE-safetensors is already downloaded.'; elif [ -d RIFE-safetensors/.git ]; then cd RIFE-safetensors && git pull --ff-only && git-lfs pull && cd ..; elif [ -d RIFE-safetensors ]; then echo 'ERROR: RIFE-safetensors exists but is incomplete. Remove it and retry.' && exit 1; else GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/TensorForger/RIFE-safetensors RIFE-safetensors && cd RIFE-safetensors && git-lfs pull && cd ..; fi",
          "if [ -f FLUX.2-klein-4B/transformer/diffusion_pytorch_model.safetensors ]; then echo 'FLUX.2-klein-4B is already downloaded.'; elif [ -d FLUX.2-klein-4B/.git ]; then cd FLUX.2-klein-4B && git pull --ff-only && git-lfs pull && cd ..; elif [ -d FLUX.2-klein-4B ]; then echo 'ERROR: FLUX.2-klein-4B exists but is incomplete. Remove it and retry.' && exit 1; else GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/black-forest-labs/FLUX.2-klein-4B FLUX.2-klein-4B && cd FLUX.2-klein-4B && git-lfs pull && cd ..; fi",
          "mkdir -p loras"
        ]
      }
    }
  ]
}
