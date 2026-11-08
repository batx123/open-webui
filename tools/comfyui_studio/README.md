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
| `make_movie` | ffmpeg (in the Open WebUI pod) | seconds |
| `make_story_film` | all of the above: one sheet per character → per-shot keyframe edits (that shot's cast) → i2v → one soundtrack | ~1-1.5 min per shot (20 s film ≈ 6 min) |
| `redo_shot` | regenerates one shot (+ dependent `continue` shots), rebuilds the film with the same soundtrack | ~1-2 min |

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

## Story films

`make_story_film` takes a JSON shot list written by the model (`scene`, `action`, `cast`, optional `continue`), a
JSON list of `characters` (each described separately) and one `style`. Each character gets its own reference sheet;
every keyframe places exactly that shot's cast (Qwen-Image-Edit Picture 1-3) into the scene, so characters stay
identical and only appear when the story says so. A `continue` shot starts from the previous clip's last frame (and is
re-framed if it has its own `scene`). Each film saves a `comfy-film-*.json` project (shots, sheets, clips, soundtrack)
in the chat, which `redo_shot` uses to replace one shot without touching the others. Uniform
clips are joined with a stream copy (no re-encode, ~55 MB peak), and one ACE-Step soundtrack covers the whole film.
Give the Open WebUI container a 4Gi memory limit: at 2Gi it was OOM-killed during a film (it idles at ~1Gi).
