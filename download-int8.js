module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: "app",
        message: [
          "git lfs install",
          "if [ -f FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors ]; then echo 'FLUX.2-klein-4B-int8 is already downloaded.'; elif [ -d FLUX.2-klein-4B-int8/.git ]; then cd FLUX.2-klein-4B-int8 && git pull --ff-only && git lfs pull && cd ..; elif [ -d FLUX.2-klein-4B-int8 ]; then echo 'ERROR: FLUX.2-klein-4B-int8 exists but is not a git repository. Remove it and retry.' && exit 1; else git clone https://huggingface.co/aydin99/FLUX.2-klein-4B-int8 FLUX.2-klein-4B-int8; fi",
          "test -f FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors"
        ]
      }
    }
  ]
}
