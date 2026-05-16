module.exports = {
  run: [
    {
      method: "input",
      params: {
        title: "Resolution Benchmark",
        description: "Runs a headless FluxRT benchmark sweep. Stop the web UI first so the GPU is not shared.",
        type: "modal",
        form: [{
          type: "textarea",
          key: "resolutions",
          title: "Resolutions",
          description: "Comma-separated WIDTHxHEIGHT values. Dimensions must be divisible by 16.",
          default: "384x384,512x512,640x640,768x768,1024x1024,432x240,576x320,720x400,864x480,1008x560,512x288,768x432,1024x576"
        }, {
          key: "dynamic_areas",
          title: "Dynamic areas",
          description: "Comma-separated fractions from 0 to 1.",
          default: "0,0.25,1.0"
        }, {
          key: "seconds",
          title: "Seconds per dynamic area",
          default: "6"
        }, {
          key: "warmup",
          title: "Warmup seconds per resolution",
          default: "4"
        }, {
          type: "checkbox",
          key: "int8",
          title: "Use int8 model"
        }, {
          type: "checkbox",
          key: "no_compile",
          title: "Disable TorchInductor compile"
        }, {
          type: "checkbox",
          key: "no_spatial_cache",
          title: "Disable spatial cache"
        }, {
          type: "checkbox",
          key: "measure_latency",
          title: "Run experimental visual latency probe"
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
        message: [
          "python -c \"import torch\" >/dev/null 2>&1 || pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128",
          "python -c \"import fluxrt\" >/dev/null 2>&1 || pip install -e .",
          "python ../patch_fluxrt.py",
          "python ../benchmark_resolutions.py --resolutions \"{{input.resolutions}}\" --dynamic-areas \"{{input.dynamic_areas}}\" --seconds \"{{input.seconds}}\" --warmup \"{{input.warmup}}\" {{input.int8 ? '--int8' : ''}} {{input.no_compile ? '--no-compile' : ''}} {{input.no_spatial_cache ? '--no-spatial-cache' : ''}} {{input.measure_latency ? '' : '--skip-latency'}}"
        ]
      }
    }
  ]
}
