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
        bluefairy: "off",
        conda: {
          path: "env",
          python: "3.12"
        },
        path: "app",
        message: "python ../pinokio_tasks.py runtime-deps",
        on: [{
          event: "/PINOKIO_FLUXRT_RUNTIME_READY/",
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
        message: "python ../run_gradio_pinokio.py --server-name 127.0.0.1 --server-port {{port}} {{args.int8 ? '--int8' : ''}}",
        on: [{
          event: "/(http:\\/\\/[0-9.:]+)/",
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
