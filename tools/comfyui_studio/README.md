# ComfyUI Studio: Open WebUI tool

Adds image generation, image editing, short videos (optionally with a generated music
soundtrack) and music to Open WebUI chats, using a local ComfyUI server.

| Function | ComfyUI workflow | Typical time |
|---|---|---|
| `generate_image` | z-image-turbo | ~15 s |
| `edit_image` | Qwen-Image-Edit-2509 (Lightning 4-step) | ~15-35 s |
| `generate_video` | Wan2.2 14B text-to-video (lightx2v 4-step) | ~45 s per 3 s clip |
| `animate_image` | Wan2.2 14B image-to-video | ~45 s per 3 s clip |
| `generate_music` | ACE-Step 3.5B | ~10 s per 15 s |

`generate_video` and `animate_image` take an optional `music_style`. When it's set, the
ACE-Step graph is merged into the video graph and wired into `CreateVideo`'s audio input, so
ComfyUI returns a single MP4 with a soundtrack. `edit_image` and `animate_image` use the image
attached to the latest message, or otherwise the most recent image in the chat.

## Files

- `comfyui_studio_src.py`: the tool source. Edit this one.
- `build.py`: embeds the exported ComfyUI workflow JSONs (`comfyui_workflow_*.json`, read from
  the Ollama Studio project) into the source and writes `comfyui_studio.py`.
- `comfyui_studio.py`: the self-contained built tool. Paste it into Open WebUI
  (Workspace → Tools) or upload it via `POST /api/v1/tools/create`.

## Notes (Open WebUI 0.13.x)

- Images are attached to the assistant message as chat files. Assistant messages don't render
  video files, so video and audio are returned as an inline HTML embed (data-URI `<video>` /
  `<audio>`, sized via the `iframe:height` postMessage), plus a download card.
- Give it a dedicated model preset with only these tools enabled (no built-in or terminal
  tools). With ~50 competing tools, a 27B model picked the wrong one most of the time.
- Valve `COMFYUI_URL` defaults to the in-cluster service `http://comfyui.comfyui.svc.cluster.local:8188`.
