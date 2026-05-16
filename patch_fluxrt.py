from pathlib import Path


APP = Path(__file__).resolve().parent / "app"
MODEL_FILE = APP / "src" / "fluxrt" / "stream_processor" / "model_inference_subprocess.py"
STREAM_FILE = APP / "src" / "fluxrt" / "stream_processor" / "stream_processor.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Could not patch {label}; upstream source changed.")
    return text.replace(old, new, 1)


def patch_model_file() -> None:
    text = MODEL_FILE.read_text()
    text = replace_once(
        text,
        '''        manager = Manager()
        self.command_queue = manager.Queue()
        self.shared_state = manager.dict()
        self.interpolation_exp = self.config.get("interpolation_exp", 1)
''',
        '''        manager = Manager()
        self.command_queue = manager.Queue()
        self.shared_state = manager.dict()
        self.shared_state["lora_status"] = "idle"
        self.shared_state["lora_path"] = ""
        self.shared_state["lora_error"] = ""
        self.interpolation_exp = self.config.get("interpolation_exp", 1)
''',
        "ModelInferenceSubprocess lora shared state",
    )
    text = replace_once(
        text,
        '''    def set_param(self, name: str, value) -> None:
        self.command_queue.put(("set_param", (name, value)))

    def set_reference_image(self, image: np.ndarray | None) -> None:
''',
        '''    def set_param(self, name: str, value) -> None:
        self.command_queue.put(("set_param", (name, value)))

    def set_config_param(self, name: str, value) -> None:
        self.command_queue.put(("set_config_param", (name, value)))

    def set_reference_image(self, image: np.ndarray | None) -> None:
''',
        "ModelInferenceSubprocess.set_config_param",
    )
    text = replace_once(
        text,
        '''    def set_lip_transfer(self, enabled: bool) -> None:
        self.command_queue.put(("set_lip_transfer", enabled))

    def update_process_state(self) -> None:
''',
        '''    def set_lip_transfer(self, enabled: bool) -> None:
        self.command_queue.put(("set_lip_transfer", enabled))

    def load_lora(self, path: str) -> None:
        self.shared_state["lora_status"] = "queued"
        self.shared_state["lora_path"] = path
        self.shared_state["lora_error"] = ""
        self.command_queue.put(("load_lora", path))

    def get_lora_status(self) -> dict:
        return {
            "status": self.shared_state.get("lora_status", "idle"),
            "path": self.shared_state.get("lora_path", ""),
            "error": self.shared_state.get("lora_error", ""),
        }

    def update_process_state(self) -> None:
''',
        "ModelInferenceSubprocess.load_lora",
    )
    text = replace_once(
        text,
        '''                    if name == "prompt":
                        self.update_prompt_embeds(value)
                elif cmd == "set_reference_image":
''',
        '''                    if name == "prompt":
                        self.update_prompt_embeds(value)
                    elif name in ("steps", "seed"):
                        self.update_controller.reset_cache()
                elif cmd == "set_config_param":
                    name, value = payload
                    self.config[name] = value
                    if name == "enable_spatial_cache":
                        self.update_controller.reset_cache()
                elif cmd == "set_reference_image":
''',
        "ModelInferenceSubprocess config command",
    )
    text = replace_once(
        text,
        '''                elif cmd == "set_lip_transfer":
                    self.lip_active = payload

        except Empty:
''',
        '''                elif cmd == "set_lip_transfer":
                    self.lip_active = payload
                elif cmd == "load_lora":
                    self.shared_state["lora_status"] = "loading"
                    self.shared_state["lora_path"] = payload
                    self.shared_state["lora_error"] = ""
                    try:
                        if hasattr(self.pipe, "unload_lora_weights"):
                            self.pipe.unload_lora_weights()
                        self.pipe.load_lora_weights(payload)
                    except Exception as exc:
                        self.config["use_lora"] = False
                        self.config["lora_weights_path"] = ""
                        self.shared_state["lora_status"] = "error"
                        self.shared_state["lora_error"] = str(exc).splitlines()[0]
                        print(f"LoRA load failed: {exc}", flush=True)
                    else:
                        self.config["use_lora"] = True
                        self.config["lora_weights_path"] = payload
                        self.shared_state["lora_status"] = "loaded"
                        self.update_controller.reset_cache()

        except Empty:
''',
        "ModelInferenceSubprocess load_lora command",
    )
    MODEL_FILE.write_text(text)


def patch_stream_file() -> None:
    text = STREAM_FILE.read_text()
    text = replace_once(
        text,
        '''    def set_param(self, name: str, value) -> None:
        self.model_inference_subprocess.set_param(name=name, value=value)

    def set_reference_image(self, image: np.ndarray | None) -> None:
''',
        '''    def set_param(self, name: str, value) -> None:
        self.model_inference_subprocess.set_param(name=name, value=value)

    def set_config_param(self, name: str, value) -> None:
        self.config[name] = value
        self.model_inference_subprocess.set_config_param(name=name, value=value)

    def set_reference_image(self, image: np.ndarray | None) -> None:
''',
        "StreamProcessor.set_config_param",
    )
    text = replace_once(
        text,
        '''    def set_lip_transfer(self, enabled: bool) -> None:
        self.model_inference_subprocess.set_lip_transfer(enabled)

    def enable_quantization(self) -> None:
''',
        '''    def set_lip_transfer(self, enabled: bool) -> None:
        self.model_inference_subprocess.set_lip_transfer(enabled)

    def load_lora(self, path: str) -> None:
        self.model_inference_subprocess.load_lora(path)

    def get_lora_status(self) -> dict:
        status = self.model_inference_subprocess.get_lora_status()
        if status.get("status") == "loaded":
            self.config["use_lora"] = True
            self.config["lora_weights_path"] = status.get("path", "")
        elif status.get("status") == "error":
            self.config["use_lora"] = False
            self.config["lora_weights_path"] = ""
        return status

    def enable_quantization(self) -> None:
''',
        "StreamProcessor.load_lora",
    )
    STREAM_FILE.write_text(text)


if __name__ == "__main__":
    patch_model_file()
    patch_stream_file()
    print("FluxRT runtime controls patched.")
