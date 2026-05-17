module.exports = {
  run: [
    // nvidia windows with optional Triton
    {
      when: "{{gpu === 'nvidia' && platform === 'win32' && args && args.triton}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: [
          "uv pip install torch torchvision torchaudio {{args && args.xformers ? 'xformers' : ''}} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall",
          "uv pip install triton-windows"
        ]
      },
      next: null
    },
    // nvidia windows
    {
      when: "{{gpu === 'nvidia' && platform === 'win32'}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "uv pip install torch torchvision torchaudio {{args && args.xformers ? 'xformers' : ''}} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall"
      },
      next: null
    },
    // nvidia linux with optional Triton
    {
      when: "{{gpu === 'nvidia' && platform === 'linux' && args && args.triton}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: [
          "uv pip install torch torchvision torchaudio {{args && args.xformers ? 'xformers' : ''}} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall",
          "uv pip install triton"
        ]
      },
      next: null
    },
    // nvidia linux
    {
      when: "{{gpu === 'nvidia' && platform === 'linux'}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "uv pip install torch torchvision torchaudio {{args && args.xformers ? 'xformers' : ''}} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall"
      },
      next: null
    },
    // unsupported GPU fallback
    {
      when: "{{platform === 'win32' || platform === 'linux'}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "python -c \"raise SystemExit('ERROR: FluxRT Pinokio Installer currently supports NVIDIA GPUs on Windows and Linux only.')\""
      }
    }
  ]
}
