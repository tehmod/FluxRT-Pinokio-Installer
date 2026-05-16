# FluxRT Pinokio Installer

This Pinokio package installs and runs FluxRT from the official GitHub repository.

> Status: this launcher has only been tested on Linux with an NVIDIA GPU. Windows and macOS are not currently validated.

## What it does

- clones `https://github.com/tensorforger/FluxRT` into `app`
- creates a local Conda environment at `app/env`
- installs PyTorch, project dependencies, and the editable `fluxrt` package
- downloads required models: `RIFE-safetensors` and `FLUX.2-klein-4B`
- can optionally download `FLUX.2-klein-4B-int8`
- starts the FluxRT Gradio demo in the OS default browser

## Launcher commands

- `Install` — clones the repository, installs dependencies, and downloads required standard model weights
- `Start` — launches the Gradio UI with the standard model
- `Start int8` — launches the Gradio UI with `--int8` after the int8 model has been downloaded
- `Download int8 model` — downloads or resumes `FLUX.2-klein-4B-int8`
- `LoRAs` — opens the `app/loras` folder where `.safetensors` LoRA files should be placed
- `Benchmark resolutions` — runs a headless FPS/VRAM sweep across configurable output resolutions
- `Download LivePortrait` / `Repair LivePortrait` — downloads the optional lip-transfer code and model files
- `Update` — pulls the latest FluxRT source, dependencies, and models
- `Reset` — removes the cloned `app` folder and installation environment

## Runtime options

The Pinokio Gradio wrapper exposes:

- prompt changes
- reference image swaps
- inference steps
- seed
- spatial cache on/off
- LivePortrait lip transfer on/off when the optional model files are present
- LoRA listing/loading from `app/loras`

The int8 model, model compilation, resolution, and interpolation factor are startup-time choices because FluxRT allocates models and shared tensors when the processor starts. Use `Start int8` for quantized inference. LoRAs can be loaded while the app is running from files saved under `app/loras`.

## Resolution benchmarking

Use `Benchmark resolutions` from the Pinokio menu while the web UI is stopped. The runner writes:

- `app/benchmark_resolutions_<mode>.md`
- `app/benchmark_resolutions_<mode>.json`

The benchmark form accepts comma-separated `WIDTHxHEIGHT` values. Dimensions should be divisible by `16` so FluxRT does not resize internally. The default sweep covers square sizes, the current `576x320`-style aspect ratio, and common 16:9-ish sizes. It reports cold ready time, FPS at selected dynamic-area levels, latent token count, and reserved VRAM.

The form also includes an optional visual latency probe. It is experimental because it watches for image changes in generated output, so interpolation, cache behavior, and prompt-dependent content can fool it. Use the FPS columns for reliable throughput comparisons.

Mode filenames include `regular` or `int8`, `compile` or `nocompile`, and `spatial` or `nospatial`. For example, `benchmark_resolutions_int8_compile_spatial.md` is an int8 run with TorchInductor compilation and spatial cache enabled.

## LoRA loading

1. Click the Pinokio `LoRAs` menu item to open `app/loras`.
2. Put one or more `.safetensors` LoRA files in that folder. Subfolders are supported.
3. Start FluxRT, or keep it running if it is already open.
4. Open the `LoRA` section in the Gradio UI.
5. Click `Refresh LoRAs`, select a file, then click `Load LoRA`.

The dropdown stores LoRA paths relative to `app`, such as `loras/example.safetensors`. The status panel reports `loaded_lora` after a load request. New frames use the selected LoRA after the FluxRT worker applies the request.

LoRAs must match the installed `FLUX.2-klein-4B` transformer. In practice, many Flux LoRAs target full-width Flux models with transformer width `4096`; `FLUX.2-klein-4B` uses width `3072`, so those files cannot be loaded into this model. The launcher checks `.safetensors` headers and rejects obvious width mismatches before they reach the worker.

## Gradio API

Once the app is running, open the Gradio footer API page for the exact live schema. The main named endpoints are:

- `/set_prompt`
- `/set_runtime_options`
- `/get_runtime_status`
- `/set_reference_image`
- `/list_loras`
- `/load_lora`
- `/start_local_video`
- `/process_webcam_frame`

JavaScript:

```javascript
import { Client } from "@gradio/client";

const app = await Client.connect("http://127.0.0.1:7860"); // replace with the opened URL if Pinokio chose another port
await app.predict("/set_prompt", ["soft cinematic light, clean studio background"]);
await app.predict("/set_runtime_options", [2, 52, true, false]);
await app.predict("/load_lora", ["loras/example.safetensors"]);
const status = await app.predict("/get_runtime_status", []);
console.log(status.data);
```

Python:

```python
from gradio_client import Client

client = Client("http://127.0.0.1:7860")  # replace with the opened URL if Pinokio chose another port
client.predict("soft cinematic light, clean studio background", api_name="/set_prompt")
client.predict(2, 52, True, False, api_name="/set_runtime_options")
client.predict("loras/example.safetensors", api_name="/load_lora")
print(client.predict(api_name="/get_runtime_status"))
```

Curl:

```bash
curl -X POST http://127.0.0.1:7860/gradio_api/call/set_runtime_options \
  -H "Content-Type: application/json" \
  -d '{"data":[2,52,true,false]}'
```

LoRA files should be referenced by their path relative to `app`, for example `loras/example.safetensors`.

## Notes

- This launcher is configured for Linux and has only been tested on Linux installs.
- The repository intentionally does not include FluxRT source, Conda environments, generated benchmark reports, Hugging Face model weights, LivePortrait weights, LoRAs, or other downloaded runtime files. The Pinokio scripts create/download those files during install.
- The Gradio UI launches on a local HTTP address and opens with `popout: true`, so it uses the OS default browser instead of Pinokio's embedded browser.
- If the repository already exists in `app`, the launcher updates the clone instead of re-downloading it.
- Hugging Face model repositories can use a lot of disk because Git LFS stores both checked-out model files and cached LFS objects under each model folder's `.git` directory.
