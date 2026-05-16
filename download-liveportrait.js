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
        message: [
          "python -c \"import liveportrait\" >/dev/null 2>&1 || pip install -r requirements_lipsync.txt",
          "if [ -d LivePortrait-code/.git ]; then cd LivePortrait-code && git pull --ff-only && cd ..; elif [ -d LivePortrait-code ]; then echo 'ERROR: LivePortrait-code exists but is not a git repository. Remove it and retry.' && exit 1; else git clone https://github.com/KlingAIResearch/LivePortrait LivePortrait-code; fi",
          "git lfs install",
          "if [ -f LivePortrait/liveportrait/landmark.onnx ] && ! grep -q 'git-lfs.github.com/spec' LivePortrait/liveportrait/landmark.onnx; then echo 'LivePortrait models are already downloaded.'; elif [ -d LivePortrait/.git ]; then cd LivePortrait && git pull --ff-only && git lfs pull --include='liveportrait/**,insightface/**' && cd ..; elif [ -d LivePortrait ]; then echo 'ERROR: LivePortrait exists but is incomplete. Remove it and retry.' && exit 1; else git clone https://huggingface.co/KwaiVGI/LivePortrait && cd LivePortrait && git lfs pull --include='liveportrait/**,insightface/**' && cd ..; fi",
          "test -f LivePortrait/liveportrait/landmark.onnx",
          "! grep -q 'git-lfs.github.com/spec' LivePortrait/liveportrait/landmark.onnx"
        ]
      }
    }
  ]
}
