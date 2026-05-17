module.exports = {
  run: [
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
        message: [
          "uv pip install torch torchvision torchaudio {{args && args.xformers ? 'xformers' : ''}} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall",
          "{{args && args.triton ? 'uv pip install triton-windows' : ''}}",
          "{{args && args.sageattention ? 'uv pip install https://huggingface.co/cocktailpeanut/wheels/resolve/main/sageattention-2.1.1%2Bcu128torch2.7.1-cp310-cp310-win_amd64.whl' : ''}}",
          "{{args && args.flashattention ? 'uv pip install https://huggingface.co/cocktailpeanut/wheels/resolve/main/flash_attn-2.8.2%2Bcu128torch2.7-cp310-cp310-win_amd64.whl' : ''}}"
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
        message: [
          "uv pip install torch torchvision torchaudio {{args && args.xformers ? 'xformers' : ''}} --index-url https://download.pytorch.org/whl/cu128 --force-reinstall",
          "{{args && args.triton ? 'uv pip install triton' : ''}}",
          "{{args && args.sageattention ? 'uv pip install https://huggingface.co/cocktailpeanut/wheels/resolve/main/sageattention-2.1.1%2Bcu128torch2.7.1-cp310-cp310-linux_x86_64.whl' : ''}}",
          "{{args && args.flashattention ? 'uv pip install https://huggingface.co/cocktailpeanut/wheels/resolve/main/flash_attn-2.8.3%2Bcu128torch2.7-cp310-cp310-linux_x86_64.whl' : ''}}"
        ]
      },
      next: null
    },
    // amd windows
    {
      when: "{{gpu === 'amd' && platform === 'win32'}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "uv pip install torch torch-directml torchaudio torchvision numpy==1.26.4 --force-reinstall"
      },
      next: null
    },
    // amd linux (rocm)
    {
      when: "{{gpu === 'amd' && platform === 'linux'}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3 --force-reinstall"
      },
      next: null
    },
    // apple silicon mac
    {
      when: "{{platform === 'darwin' && arch === 'arm64'}}",
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "uv pip install torch torchvision torchaudio --force-reinstall"
      },
      next: null
    },
    // cpu fallback
    {
      method: "shell.run",
      params: {
        conda: {
          path: "{{args && args.conda && args.conda.path ? args.conda.path : 'env'}}",
          python: "{{args && args.conda && args.conda.python ? args.conda.python : '3.12'}}"
        },
        path: "{{args && args.path ? args.path : '.'}}",
        message: "uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --force-reinstall"
      }
    }
  ]
}
