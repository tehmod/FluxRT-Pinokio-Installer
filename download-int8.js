module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: "app",
        message: "python ../pinokio_tasks.py int8",
        on: [{
          event: "/PINOKIO_FLUXRT_INT8_READY/",
          kill: true
        }]
      }
    }
  ]
}
