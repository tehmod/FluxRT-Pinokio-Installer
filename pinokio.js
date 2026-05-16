module.exports = {
  version: "5.0",
  title: "FluxRT Pinokio Installer",
  description: "Linux-tested Pinokio launcher for FluxRT with automatic model downloads.",
  icon: "icon.svg",
  menu: async (kernel, info) => {
    let sourceInstalled = await info.exists("app/.git")
    let envInstalled = await info.exists("app/env")
    let requiredModelsInstalled = await info.exists("app/RIFE-safetensors/flownet.safetensors")
      && await info.exists("app/FLUX.2-klein-4B/transformer/diffusion_pytorch_model.safetensors")
    let installed = sourceInstalled && envInstalled && requiredModelsInstalled
    let running = {
      install: info.running("install.js"),
      start: info.running("start.js"),
      update: info.running("update.js"),
      reset: info.running("reset.js"),
      int8: info.running("download-int8.js"),
      liveportrait: info.running("download-liveportrait.js"),
      benchmark: info.running("benchmark-resolutions.js")
    }
    let int8Installed = await info.exists("app/FLUX.2-klein-4B-int8/diffusion_pytorch_model.safetensors")
    let livePortraitInstalled = await info.exists("app/LivePortrait/liveportrait/landmark.onnx")
    let benchmarkReportExists = await info.exists("app/benchmark_resolutions_regular_compile_spatial.md")
      || await info.exists("app/benchmark_resolutions_int8_compile_spatial.md")
      || await info.exists("app/benchmark_resolutions.md")

    if (running.install) {
      return [{
        icon: "fa-solid fa-plug",
        text: "Installing",
        href: "install.js",
      }]
    }

    if (sourceInstalled && !installed) {
      return [{
        icon: "fa-solid fa-plug",
        text: "Resume Install",
        href: "install.js",
      }, {
        icon: "fa-regular fa-circle-xmark",
        text: "Reset",
        href: "reset.js",
        confirm: "Are you sure you wish to reset the installation?"
      }]
    }

    if (installed) {
      if (running.start) {
        let local = await info.local("start.js")
        if (local && local.url) {
          return [{
            icon: "fa-solid fa-rocket",
            text: "Open Web UI (Browser)",
            href: local.url,
            popout: true,
          }, {
            icon: "fa-regular fa-folder-open",
            text: "LoRAs",
            href: "app/loras",
            fs: true
          }, {
            icon: "fa-solid fa-terminal",
            text: "Terminal",
            href: "start.js",
          }]
        }
        return [{
          icon: "fa-solid fa-terminal",
          text: "Terminal",
          href: "start.js",
        }, {
          icon: "fa-regular fa-folder-open",
          text: "LoRAs",
          href: "app/loras",
          fs: true
        }]
      }
      if (running.update) {
        return [{
          icon: "fa-solid fa-plug",
          text: "Updating",
          href: "update.js",
        }]
      }
      if (running.reset) {
        return [{
          icon: "fa-solid fa-terminal",
          text: "Resetting",
          href: "reset.js",
        }]
      }
      if (running.int8) {
        return [{
          icon: "fa-solid fa-download",
          text: "Downloading int8 model",
          href: "download-int8.js",
        }]
      }
      if (running.liveportrait) {
        return [{
          icon: "fa-solid fa-download",
          text: "Downloading LivePortrait",
          href: "download-liveportrait.js",
        }]
      }
      if (running.benchmark) {
        return [{
          icon: "fa-solid fa-chart-line",
          text: "Benchmarking resolutions",
          href: "benchmark-resolutions.js",
        }]
      }

      let menu = [{
        icon: "fa-solid fa-power-off",
        text: "Start",
        href: "start.js",
      }]

      if (int8Installed) {
        menu.push({
          icon: "fa-solid fa-bolt",
          text: "Start int8",
          href: "start.js",
          params: {
            int8: true
          }
        })
      } else {
        menu.push({
          icon: "fa-solid fa-download",
          text: "Download int8 model",
          href: "download-int8.js",
          mode: "refresh",
        })
      }

      menu.push({
        icon: "fa-regular fa-folder-open",
        text: "LoRAs",
        href: "app/loras",
        fs: true
      }, {
        icon: "fa-solid fa-chart-line",
        text: "Benchmark resolutions",
        href: "benchmark-resolutions.js",
      })

      if (benchmarkReportExists) {
        menu.push({
          icon: "fa-regular fa-file-lines",
          text: "Open benchmark report",
          href: "app",
          fs: true
        })
      }

      menu.push({
        icon: livePortraitInstalled ? "fa-solid fa-face-smile" : "fa-solid fa-download",
        text: livePortraitInstalled ? "Repair LivePortrait" : "Download LivePortrait",
        href: "download-liveportrait.js",
        mode: "refresh",
      }, {
        icon: "fa-solid fa-plug",
        text: "Update",
        href: "update.js",
      }, {
        icon: "fa-regular fa-circle-xmark",
        text: "Reset",
        href: "reset.js",
        confirm: "Are you sure you wish to reset the installation?"
      }, {
        icon: "fa-solid fa-plug",
        text: "Install",
        href: "install.js",
      })
      return menu
    }

    return [{
      icon: "fa-solid fa-plug",
      text: "Install",
      href: "install.js",
    }]
  }
}
