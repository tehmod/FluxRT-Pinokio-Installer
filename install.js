module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: ".",
        message: "python pinokio_tasks.py source",
        on: [{
          event: "/PINOKIO_FLUXRT_SOURCE_READY/",
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
        message: "python ../pinokio_tasks.py deps",
        on: [{
          event: "/PINOKIO_FLUXRT_DEPS_READY/",
          kill: true
        }]
      }
    },
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: "app",
        message: "python ../pinokio_tasks.py models",
        on: [{
          event: "/PINOKIO_FLUXRT_MODELS_READY/",
          kill: true
        }]
      }
    }
  ]
}
