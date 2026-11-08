"""
title: ComfyUI Studio
author: demo box (ported from Ollama Studio's comfyui_common.py)
version: 0.1.0
description: Generate images, edit images, make short videos (text or image to video) and music with the local ComfyUI server. Results appear inline in the chat.
"""

# Built from ~/open-webui/tools/comfyui_studio_src.py by build.py, which
# embeds the workflow templates from ~/testproject/streamlit. Edit the
# source + rebuild; do not edit the generated comfyui_studio.py by hand.

import asyncio
import base64
import io
import json
import random
import re
import time
import uuid
from typing import Any, Callable, Optional

import aiohttp
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

_TEMPLATES: dict = {}  # __TEMPLATES__

# Node IDs from the exported templates (same as Ollama Studio's comfyui_common.py).
_IMG = {"prompt": "57:27", "latent": "57:13", "sampler": "57:3", "save": "9"}
_EDIT = {"image": "78", "prompt": "435", "sampler": "433:3", "save": "60"}
_T2V = {"prompt": "89", "latent": "74", "sampler": "81", "createvideo": "88", "save": "80"}
_I2V = {"image": "97", "prompt": "129:93", "latent": "129:98", "sampler": "129:86",
        "lora": "129:131", "createvideo": "129:94", "save": "108"}
_T2A = {"encode": "14", "latent": "17", "sampler": "52", "decode": "18", "save": "59"}

_IMAGE_SIZES = {"square": (1024, 1024), "landscape": (1344, 768), "portrait": (768, 1344)}
_VIDEO_SIZES = {"square": (640, 640), "landscape": (832, 480), "portrait": (480, 832)}
_FILE_ID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


class ComfyError(Exception):
    pass


class Tools:
    class Valves(BaseModel):
        COMFYUI_URL: str = Field(
            default="http://comfyui.comfyui.svc.cluster.local:8188",
            description="Base URL of the ComfyUI server, as seen from the Open WebUI pod.",
        )
        IMAGE_TIMEOUT: int = Field(default=300, description="Seconds to wait for an image or edit.")
        VIDEO_TIMEOUT: int = Field(default=1200, description="Seconds to wait for a video.")
        AUDIO_TIMEOUT: int = Field(default=900, description="Seconds to wait for music.")
        MAX_VIDEO_SECONDS: int = Field(default=8, description="Wan2.2 degrades past ~8 s per clip.")
        MAX_MUSIC_SECONDS: int = Field(default=240, description="Upper limit for generated music.")

    def __init__(self):
        self.valves = self.Valves()

    # ------------------------------------------------------------------ tools

    async def generate_image(
        self,
        prompt: str,
        orientation: str = "square",
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        This tool IS the image/video/music generator for this chat: call it directly. Do not write code,
        use the terminal, or load skills (e.g. image-processor) to make media instead.
        Generate an image from a text description with the local ComfyUI server (z-image-turbo, a few seconds).
        Use this whenever the user asks to create, draw, render or generate a picture or image.

        :param prompt: A detailed visual description of the image (subject, style, lighting, composition).
        :param orientation: One of "square", "landscape" or "portrait". Default "square".
        :return: Status JSON. The image is already shown to the user in the chat.
        """
        w, h = _IMAGE_SIZES.get((orientation or "square").lower(), _IMAGE_SIZES["square"])
        wf = self._template("z_image_turbo")
        wf[_IMG["prompt"]]["inputs"]["text"] = prompt
        wf[_IMG["latent"]]["inputs"]["width"] = w
        wf[_IMG["latent"]]["inputs"]["height"] = h
        wf[_IMG["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        return await self._run(
            "image", wf, _IMG["save"], "image/png", self.valves.IMAGE_TIMEOUT,
            f"Generating image ({w}x{h})",
            __request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__,
        )

    async def edit_image(
        self,
        instruction: str,
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        This tool IS the image editor/animator for this chat: call it directly. Do not write code,
        use the terminal, or load skills (e.g. image-processor) for this instead.
        Edit an existing image following an instruction (Qwen-Image-Edit, ~15 s). Uses the image the user
        attached to their latest message, or otherwise the most recent image in this chat (including one
        you generated earlier). Use for requests like "make it night time", "replace the cat with a dog",
        "remove the person on the left", "turn this into a watercolor".

        :param instruction: The edit to make, written as an instruction (e.g. "Replace the cat with a dalmatian").
        :return: Status JSON. The edited image is already shown to the user in the chat.
        """
        try:
            src, src_name = await self._latest_image(__user__, __metadata__, __chat_id__, __message_id__)
        except ComfyError as e:
            return self._error(str(e))
        await self._status(__event_emitter__, f"Uploading {src_name} to ComfyUI")
        try:
            uploaded = await self._upload(src)
        except Exception as e:
            return self._error(f"Could not upload the source image to ComfyUI: {e}")
        wf = self._template("qwen_image_edit")
        wf[_EDIT["image"]]["inputs"]["image"] = uploaded
        wf[_EDIT["prompt"]]["inputs"]["value"] = instruction
        wf[_EDIT["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        return await self._run(
            "image", wf, _EDIT["save"], "image/png", self.valves.IMAGE_TIMEOUT,
            f"Editing {src_name}",
            __request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__,
        )

    async def generate_video(
        self,
        prompt: str,
        seconds: int = 5,
        orientation: str = "landscape",
        music_style: str = "",
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        This tool IS the image/video/music generator for this chat: call it directly. Do not write code,
        use the terminal, or load skills (e.g. image-processor) to make media instead.
        Generate a short video clip from a text description (Wan2.2 14B, 16 fps, about 1-2 minutes).
        Use when the user asks for a video, clip or animation of something described in words.

        :param prompt: A detailed description of the scene and the motion/camera movement.
        :param seconds: Clip length in seconds, 1-8. Default 5.
        :param orientation: One of "landscape", "portrait" or "square". Default "landscape".
        :param music_style: Optional. To give the clip a generated music soundtrack (one MP4 with sound), set this to
            comma-separated music style tags, e.g. "cinematic ambient, soft strings, slow". Use it whenever the user asks
            for sound, music or a soundtrack with the video. Leave empty for a silent clip. (Music only, not sound effects.)
        :return: Status JSON. The video is already shown to the user in the chat.
        """
        secs = max(1, min(int(seconds or 5), self.valves.MAX_VIDEO_SECONDS))
        w, h = _VIDEO_SIZES.get((orientation or "landscape").lower(), _VIDEO_SIZES["landscape"])
        wf = self._template("wan22_t2v")
        wf[_T2V["prompt"]]["inputs"]["text"] = prompt
        wf[_T2V["latent"]]["inputs"]["width"] = w
        wf[_T2V["latent"]]["inputs"]["height"] = h
        wf[_T2V["latent"]]["inputs"]["length"] = secs * 16 + 1
        wf[_T2V["sampler"]]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
        sound = bool((music_style or "").strip())
        if sound:
            wf = self._with_soundtrack(wf, music_style, secs, _T2V["createvideo"])
        return await self._run(
            "video", wf, _T2V["save"], "video/mp4", self.valves.VIDEO_TIMEOUT,
            f"Generating {secs}s video ({w}x{h}){' with soundtrack' if sound else ''}",
            __request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__,
            sound=sound,
        )

    async def animate_image(
        self,
        prompt: str,
        seconds: int = 5,
        music_style: str = "",
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        This tool IS the image editor/animator for this chat: call it directly. Do not write code,
        use the terminal, or load skills (e.g. image-processor) for this instead.
        Turn an existing image into a short video, using it as the first frame (Wan2.2 14B image-to-video,
        about 1-2 minutes). Uses the image attached to the user's latest message, or otherwise the most
        recent image in this chat. Use for "animate this", "bring this picture to life", "make a video from this image".

        :param prompt: What should happen in the clip (motion, camera movement, action).
        :param seconds: Clip length in seconds, 1-8. Default 5.
        :param music_style: Optional. To give the clip a generated music soundtrack (one MP4 with sound), set this to
            comma-separated music style tags, e.g. "cinematic ambient, soft strings, slow". Use it whenever the user asks
            for sound, music or a soundtrack with the video. Leave empty for a silent clip. (Music only, not sound effects.)
        :return: Status JSON. The video is already shown to the user in the chat.
        """
        try:
            src, src_name = await self._latest_image(__user__, __metadata__, __chat_id__, __message_id__)
        except ComfyError as e:
            return self._error(str(e))
        secs = max(1, min(int(seconds or 5), self.valves.MAX_VIDEO_SECONDS))
        w, h = self._video_size_for(src)
        await self._status(__event_emitter__, f"Uploading {src_name} to ComfyUI")
        try:
            uploaded = await self._upload(src)
        except Exception as e:
            return self._error(f"Could not upload the source image to ComfyUI: {e}")
        wf = self._template("wan22_i2v")
        wf[_I2V["image"]]["inputs"]["image"] = uploaded
        wf[_I2V["prompt"]]["inputs"]["text"] = prompt
        wf[_I2V["latent"]]["inputs"]["width"] = w
        wf[_I2V["latent"]]["inputs"]["height"] = h
        wf[_I2V["latent"]]["inputs"]["length"] = secs * 16 + 1
        wf[_I2V["lora"]]["inputs"]["value"] = True  # 4-step lightx2v path
        wf[_I2V["sampler"]]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
        sound = bool((music_style or "").strip())
        if sound:
            wf = self._with_soundtrack(wf, music_style, secs, _I2V["createvideo"])
        return await self._run(
            "video", wf, _I2V["save"], "video/mp4", self.valves.VIDEO_TIMEOUT,
            f"Animating {src_name} into a {secs}s video ({w}x{h}){' with soundtrack' if sound else ''}",
            __request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__,
            sound=sound,
        )

    async def generate_music(
        self,
        style_tags: str,
        lyrics: str = "",
        seconds: int = 30,
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> Any:
        """
        This tool IS the image/video/music generator for this chat: call it directly. Do not write code,
        use the terminal, or load skills (e.g. image-processor) to make media instead.
        Generate a song or instrumental track (ACE-Step 3.5B). Use when the user asks for music, a song,
        a jingle, a beat or a soundtrack.

        :param style_tags: Comma-separated style description: genre, mood, instruments, vocals, tempo (e.g. "lofi hip hop, mellow, piano, vinyl crackle, 80 bpm").
        :param lyrics: Optional song lyrics, with section markers like [verse] and [chorus]. Leave empty for an instrumental.
        :param seconds: Track length in seconds, 10-240. Default 30.
        :return: Status JSON plus an inline audio player shown to the user.
        """
        secs = max(10, min(int(seconds or 30), self.valves.MAX_MUSIC_SECONDS))
        wf = self._template("ace_step_t2a")
        wf[_T2A["encode"]]["inputs"]["tags"] = style_tags
        wf[_T2A["encode"]]["inputs"]["lyrics"] = (lyrics or "").strip() or "[inst]"
        wf[_T2A["latent"]]["inputs"]["seconds"] = secs
        wf[_T2A["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        return await self._run(
            "audio", wf, _T2A["save"], "audio/mpeg", self.valves.AUDIO_TIMEOUT,
            f"Generating {secs}s of music",
            __request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__,
        )

    # --------------------------------------------------------------- helpers

    def _template(self, name: str) -> dict:
        return json.loads(json.dumps(_TEMPLATES[name]))

    def _with_soundtrack(self, video_wf: dict, music_style: str, secs: int, createvideo_node: str) -> dict:
        """Merge the ACE-Step graph into a video graph so SaveVideo muxes a soundtrack into the MP4.

        Port of Ollama Studio's comfyui_common._merge_audio_into_video_workflow: audio node ids get an
        "a" prefix (and their internal links are rewritten), SaveAudioMP3 is dropped, and the decoded
        AUDIO output feeds CreateVideo's optional `audio` input. Soundtrack length = clip length.
        """
        audio = self._template("ace_step_t2a")
        audio[_T2A["encode"]]["inputs"]["tags"] = music_style
        audio[_T2A["encode"]]["inputs"]["lyrics"] = "[inst]"
        audio[_T2A["latent"]]["inputs"]["seconds"] = max(1, int(secs))
        audio[_T2A["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        del audio[_T2A["save"]]
        merged = dict(video_wf)
        for nid, node in audio.items():
            for key, val in node["inputs"].items():
                if isinstance(val, list) and len(val) == 2 and val[0] in audio:
                    node["inputs"][key] = [f"a{val[0]}", val[1]]
            merged[f"a{nid}"] = node
        merged[createvideo_node]["inputs"]["audio"] = [f"a{_T2A['decode']}", 0]
        return merged

    @staticmethod
    def _error(msg: str) -> str:
        return json.dumps({"status": "error", "message": msg})

    @staticmethod
    async def _status(emitter, description: str, done: bool = False):
        if emitter:
            await emitter({"type": "status", "data": {"description": description, "done": done}})

    def _video_size_for(self, image_bytes: bytes) -> tuple:
        try:
            from PIL import Image

            w, h = Image.open(io.BytesIO(image_bytes)).size
            ratio = w / h
        except Exception:
            ratio = 1.0
        if ratio > 1.2:
            return _VIDEO_SIZES["landscape"]
        if ratio < 0.83:
            return _VIDEO_SIZES["portrait"]
        return _VIDEO_SIZES["square"]

    async def _upload(self, image_bytes: bytes) -> str:
        form = aiohttp.FormData()
        form.add_field("image", image_bytes, filename=f"owui_{uuid.uuid4().hex}.png",
                       content_type="image/png")
        form.add_field("type", "input")
        form.add_field("overwrite", "true")
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{self.valves.COMFYUI_URL}/upload/image", data=form,
                              timeout=aiohttp.ClientTimeout(total=60)) as r:
                r.raise_for_status()
                body = await r.json()
        sub = body.get("subfolder", "")
        return f"{sub}/{body['name']}" if sub else body["name"]

    async def _comfy(self, workflow: dict, save_node: str, timeout: int, label: str, emitter) -> bytes:
        base = self.valves.COMFYUI_URL
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{base}/prompt", json={"prompt": workflow, "client_id": uuid.uuid4().hex},
                              timeout=aiohttp.ClientTimeout(total=30)) as r:
                body = await r.json(content_type=None)
                if r.status >= 400 or body.get("node_errors"):
                    raise ComfyError(f"ComfyUI rejected the workflow: {body.get('error') or body.get('node_errors')}")
                prompt_id = body["prompt_id"]

            start = time.monotonic()
            last_note = 0.0
            while time.monotonic() - start < timeout:
                async with s.get(f"{base}/history/{prompt_id}", timeout=aiohttp.ClientTimeout(total=15)) as r:
                    entry = (await r.json()).get(prompt_id)
                if entry:
                    st = entry.get("status", {})
                    if st.get("status_str") == "error":
                        msgs = [m[1].get("exception_message", "") for m in st.get("messages", [])
                                if m and m[0] == "execution_error"]
                        raise ComfyError("ComfyUI failed: " + ("; ".join(msgs) or "unknown error"))
                    if st.get("completed"):
                        out = entry["outputs"].get(save_node, {})
                        for key in ("images", "videos", "gifs", "audio"):
                            if out.get(key):
                                f = out[key][0]
                                params = {"filename": f["filename"], "subfolder": f.get("subfolder", ""),
                                          "type": f.get("type", "output")}
                                async with s.get(f"{base}/view", params=params,
                                                 timeout=aiohttp.ClientTimeout(total=120)) as v:
                                    v.raise_for_status()
                                    return await v.read()
                        raise ComfyError(f"ComfyUI finished but produced no output on node {save_node}")
                elapsed = time.monotonic() - start
                if elapsed - last_note >= 5:
                    last_note = elapsed
                    await self._status(emitter, f"{label}... {int(elapsed)}s")
                await asyncio.sleep(1)
        raise ComfyError(f"ComfyUI did not finish within {timeout}s")

    async def _run(self, kind, workflow, save_node, content_type, timeout, label,
                   request, user, metadata, chat_id, message_id, emitter, sound=False):
        await self._status(emitter, label)
        t0 = time.monotonic()
        try:
            data = await self._comfy(workflow, save_node, timeout, label, emitter)
        except Exception as e:
            await self._status(emitter, f"{label}: failed", done=True)
            return self._error(f"{type(e).__name__}: {e}")
        took = round(time.monotonic() - t0, 1)

        try:
            await self._publish(kind, data, content_type, request, user, metadata, chat_id, message_id, emitter)
        except Exception as e:
            await self._status(emitter, f"{label}: could not save result", done=True)
            return self._error(f"Generated, but saving to Open WebUI failed: {type(e).__name__}: {e}")

        await self._status(emitter, f"{label}: done in {took}s", done=True)
        shown = {"image": "The image", "video": "The video player", "audio": "The audio player"}[kind]
        status_json = json.dumps({
            "status": "success",
            "seconds_taken": took,
            "message": f"{shown} is already visible to the user in the chat. Do not repeat links or "
                       f"markdown for it; just briefly describe what was made.",
        })
        if kind == "image":
            return status_json
        # Assistant messages render image files inline but show other files only as a
        # download card (video: not at all), so play audio/video from an inline embed.
        return HTMLResponse(content=self._media_embed(kind, data, content_type, sound),
                            headers={"Content-Disposition": "inline"}), status_json

    @staticmethod
    def _media_embed(kind: str, data: bytes, content_type: str, sound: bool = False) -> str:
        src = f"data:{content_type};base64,{base64.b64encode(data).decode()}"
        if kind == "video":
            # Silent clips autoplay muted on a loop; clips with a soundtrack wait for the user to press play
            # (browsers block unmuted autoplay anyway).
            attrs = "controls loop playsinline preload='auto'" + ("" if sound else " autoplay muted")
            el = (f"<video {attrs} "
                  f"style='display:block;width:100%;max-width:768px;height:auto;border-radius:12px' src='{src}'></video>")
        else:
            el = f"<audio controls preload='metadata' style='display:block;width:100%' src='{src}'></audio>"
        # Open WebUI sizes embed iframes from an {type: 'iframe:height'} postMessage.
        script = (
            "<script>function h(){parent.postMessage({type:'iframe:height',"
            "height:Math.ceil(document.body.getBoundingClientRect().height)+8},'*')}"
            "addEventListener('load',h);document.querySelector('video,audio')"
            ".addEventListener('loadedmetadata',h);new ResizeObserver(h).observe(document.body)</script>"
        )
        return ("<!doctype html><html><body style='margin:0;padding:4px 0;background:transparent'>"
                f"{el}{script}</body></html>")

    async def _publish(self, kind, data, content_type, request, user, metadata, chat_id, message_id, emitter):
        from fastapi import UploadFile
        from open_webui.models.chats import Chats
        from open_webui.models.users import UserModel
        from open_webui.routers.files import upload_file_handler
        from open_webui.utils.chat_id import is_saved_chat_id

        user_model = UserModel(**user)
        meta = {k: (metadata or {}).get(k) for k in ("chat_id", "message_id", "session_id")}
        ext = {"image/png": ".png", "video/mp4": ".mp4", "audio/mpeg": ".mp3"}.get(content_type, "")
        name = f"comfy-{kind}-{time.strftime('%Y%m%d-%H%M%S')}{ext}"
        upload = UploadFile(file=io.BytesIO(data), filename=name, headers={"content-type": content_type})
        item = await upload_file_handler(request, file=upload, metadata=meta, process=False, user=user_model)
        if chat_id and message_id and is_saved_chat_id(chat_id):
            await Chats.insert_chat_files(chat_id=chat_id, message_id=message_id,
                                          file_ids=[item.id], user_id=user_model.id)
        info = {
            "id": item.id,
            "url": request.app.url_path_for("get_file_content_by_id", id=item.id),
            "name": name,
            "content_type": content_type,
        }
        files = [{"type": "image" if kind == "image" else "file", **info}]
        if is_saved_chat_id(chat_id) and message_id:
            saved = await Chats.add_message_files_by_id_and_message_id(chat_id, message_id, files)
            if saved is not None:
                files = saved
        if emitter:
            await emitter({"type": "chat:message:files", "data": {"files": files}})

    async def _latest_image(self, user, metadata, chat_id, message_id) -> tuple:
        """Return (bytes, name) of the newest image: current attachments first, then chat history."""
        candidates = []
        for f in reversed((metadata or {}).get("files") or []):
            candidates.append(f)
        if chat_id:
            try:
                from open_webui.models.chats import Chats

                chat = await Chats.get_chat_by_id(chat_id)
                history = (chat.chat or {}).get("history", {}) if chat else {}
                msgs = history.get("messages", {}) or {}
                mid = message_id if message_id in msgs else history.get("currentId")
                seen = set()
                while mid and mid in msgs and mid not in seen:
                    seen.add(mid)
                    m = msgs[mid]
                    candidates.extend(reversed(m.get("files") or []))
                    mid = m.get("parentId")
            except Exception:
                pass

        for f in candidates:
            if not isinstance(f, dict):
                continue
            ctype = str(f.get("content_type") or ((f.get("file") or {}).get("meta") or {}).get("content_type") or "")
            if not (f.get("type") == "image" or ctype.startswith("image/")):
                continue
            url = str(f.get("url") or "")
            if url.startswith("data:image/"):
                return base64.b64decode(url.split(",", 1)[1]), f.get("name") or "the image"
            fid = f.get("id") or (f.get("file") or {}).get("id")
            if not fid:
                m = _FILE_ID_RE.search(url)
                fid = m.group(1) if m else None
            if not fid:
                continue
            data = await self._read_file(fid, user)
            if data:
                return data, f.get("name") or "the image"
        raise ComfyError("No image found. Ask the user to attach an image (or generate one first).")

    @staticmethod
    async def _read_file(file_id: str, user: dict) -> Optional[bytes]:
        from open_webui.models.files import Files
        from open_webui.storage.provider import Storage

        f = await Files.get_file_by_id(file_id)
        if not f:
            return None
        if f.user_id != (user or {}).get("id") and (user or {}).get("role") != "admin":
            return None
        path = await asyncio.to_thread(Storage.get_file, f.path)
        with open(path, "rb") as fh:
            return fh.read()
