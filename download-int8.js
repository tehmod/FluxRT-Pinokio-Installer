module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: "app",
        message: [
          "set -euo pipefail",
          "command -v git-lfs >/dev/null 2>&1 || conda install -y -c conda-forge git-lfs",
          "git-lfs install",
          "if [ -f FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors ] && ! grep -q 'git-lfs.github.com/spec' FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors; then echo 'FLUX.2-klein-4B-int8 is already downloaded.'; elif [ -d FLUX.2-klein-4B-int8/.git ]; then cd FLUX.2-klein-4B-int8 && git pull --ff-only && git-lfs pull && cd ..; elif [ -d FLUX.2-klein-4B-int8 ]; then echo 'ERROR: FLUX.2-klein-4B-int8 exists but is not a git repository. Remove it and retry.' && exit 1; else GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/aydin99/FLUX.2-klein-4B-int8 FLUX.2-klein-4B-int8 && cd FLUX.2-klein-4B-int8 && git-lfs pull && cd ..; fi",
          "test -f FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors",
          "! grep -q 'git-lfs.github.com/spec' FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors",
          "echo PINOKIO_FLUXRT_INT8_READY"
        ],
        on: [{
          event: "/PINOKIO_FLUXRT_INT8_READY/",
          kill: true
        }]
      }
    }
  ]
}
