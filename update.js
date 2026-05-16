module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: ".",
        message: "python pinokio_tasks.py update-source",
        on: [{
          event: "/PINOKIO_FLUXRT_UPDATE_SOURCE_READY/",
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
        message: "python ../pinokio_tasks.py update-deps",
        on: [{
          event: "/PINOKIO_FLUXRT_UPDATE_DEPS_READY/",
          kill: true
        }]
      }
    }
  ]
}
