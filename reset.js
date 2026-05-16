module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        bluefairy: "off",
        path: ".",
        message: [
          "rm -rf app"
        ]
      }
    }
  ]
}
