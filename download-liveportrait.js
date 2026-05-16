module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        conda: {
          path: "env",
          python: "3.12"
        },
        path: "app",
        message: "python ../pinokio_tasks.py liveportrait",
        on: [{
          event: "/PINOKIO_FLUXRT_LIVEPORTRAIT_READY/",
          kill: true
        }]
      }
    }
  ]
}
