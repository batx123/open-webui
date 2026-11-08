"""Embed Ollama Studio's ComfyUI workflow templates into the Open WebUI tool.

    python3 build.py   ->  writes comfyui_studio.py (paste/upload that into Open WebUI)
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
WORKFLOWS = Path.home() / "testproject" / "streamlit"
NAMES = ["z_image_turbo", "qwen_image_edit", "wan22_t2v", "wan22_i2v", "ace_step_t2a"]

templates = {n: json.loads((WORKFLOWS / f"comfyui_workflow_{n}.json").read_text()) for n in NAMES}
src = (HERE / "comfyui_studio_src.py").read_text()
marker = "_TEMPLATES: dict = {}  # __TEMPLATES__"
assert src.count(marker) == 1
out = src.replace(marker, "_TEMPLATES: dict = json.loads(" + repr(json.dumps(templates)) + ")")
(HERE / "comfyui_studio.py").write_text(out)
compile(out, "comfyui_studio.py", "exec")
print(f"wrote comfyui_studio.py ({len(out)} bytes, {len(NAMES)} templates)")
