module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: ".",
        message: "python pinokio_tasks.py migrate",
        on: [{
          event: "/PINOKIO_FLUXRT_MIGRATION_READY/",
          kill: true
        }]
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
        message: "python ../pinokio_tasks.py start-models",
        on: [{
          event: "/PINOKIO_FLUXRT_START_MODELS_READY/",
          kill: true
        }]
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
