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

_TEMPLATES: dict = json.loads('{"z_image_turbo": {"9": {"inputs": {"filename_prefix": "z-image-turbo", "images": ["57:8", 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}}, "57:30": {"inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2", "device": "default"}, "class_type": "CLIPLoader", "_meta": {"title": "Load CLIP"}}, "57:29": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}}, "57:33": {"inputs": {"conditioning": ["57:27", 0]}, "class_type": "ConditioningZeroOut", "_meta": {"title": "ConditioningZeroOut"}}, "57:8": {"inputs": {"samples": ["57:3", 0], "vae": ["57:29", 0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}}, "57:28": {"inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader", "_meta": {"title": "Load Diffusion Model"}}, "57:27": {"inputs": {"text": "Latina female with thick wavy hair, harbor boats and pastel houses behind. Breezy seaside light, warm tones, cinematic close-up. ", "clip": ["57:30", 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}}, "57:13": {"inputs": {"width": 1024, "height": 1024, "batch_size": 1}, "class_type": "EmptySD3LatentImage", "_meta": {"title": "EmptySD3LatentImage"}}, "57:11": {"inputs": {"shift": 3, "model": ["57:28", 0]}, "class_type": "ModelSamplingAuraFlow", "_meta": {"title": "ModelSamplingAuraFlow"}}, "57:3": {"inputs": {"seed": 0, "steps": 8, "cfg": 1, "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1, "model": ["57:11", 0], "positive": ["57:27", 0], "negative": ["57:33", 0], "latent_image": ["57:13", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}}}, "qwen_image_edit": {"60": {"inputs": {"filename_prefix": "ComfyUI", "images": ["433:8", 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}}, "78": {"inputs": {"image": "church.png"}, "class_type": "LoadImage", "_meta": {"title": "Load Image"}}, "435": {"inputs": {"value": "Replace the cat with a dalmatian"}, "class_type": "PrimitiveStringMultiline", "_meta": {"title": "Prompt"}}, "433:75": {"inputs": {"strength": 1, "model": ["433:66", 0]}, "class_type": "CFGNorm", "_meta": {"title": "CFGNorm"}}, "433:39": {"inputs": {"vae_name": "qwen_image_vae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}}, "433:38": {"inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}, "class_type": "CLIPLoader", "_meta": {"title": "Load CLIP"}}, "433:37": {"inputs": {"unet_name": "qwen_image_edit_2509_fp8_e4m3fn.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader", "_meta": {"title": "Load Diffusion Model"}}, "433:110": {"inputs": {"prompt": "", "clip": ["433:38", 0], "vae": ["433:39", 0], "image1": ["433:117", 0]}, "class_type": "TextEncodeQwenImageEditPlus", "_meta": {"title": "TextEncodeQwenImageEditPlus"}}, "433:66": {"inputs": {"shift": 3, "model": ["433:89", 0]}, "class_type": "ModelSamplingAuraFlow", "_meta": {"title": "ModelSamplingAuraFlow"}}, "433:111": {"inputs": {"prompt": ["435", 0], "clip": ["433:38", 0], "vae": ["433:39", 0], "image1": ["433:117", 0]}, "class_type": "TextEncodeQwenImageEditPlus", "_meta": {"title": "TextEncodeQwenImageEditPlus"}}, "433:88": {"inputs": {"pixels": ["433:117", 0], "vae": ["433:39", 0]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode"}}, "433:8": {"inputs": {"samples": ["433:3", 0], "vae": ["433:39", 0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}}, "433:89": {"inputs": {"lora_name": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1, "model": ["433:37", 0]}, "class_type": "LoraLoaderModelOnly", "_meta": {"title": "Load LoRA"}}, "433:117": {"inputs": {"image": ["78", 0]}, "class_type": "FluxKontextImageScale", "_meta": {"title": "FluxKontextImageScale"}}, "433:3": {"inputs": {"seed": 428347202510199, "steps": 4, "cfg": 1, "sampler_name": "euler", "scheduler": "simple", "denoise": 1, "model": ["433:75", 0], "positive": ["433:111", 0], "negative": ["433:110", 0], "latent_image": ["433:88", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}}}, "wan22_t2v": {"71": {"inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}, "class_type": "CLIPLoader", "_meta": {"title": "Load CLIP"}}, "72": {"inputs": {"text": "\\u8272\\u8c03\\u8273\\u4e3d\\uff0c\\u8fc7\\u66dd\\uff0c\\u9759\\u6001\\uff0c\\u7ec6\\u8282\\u6a21\\u7cca\\u4e0d\\u6e05\\uff0c\\u5b57\\u5e55\\uff0c\\u98ce\\u683c\\uff0c\\u4f5c\\u54c1\\uff0c\\u753b\\u4f5c\\uff0c\\u753b\\u9762\\uff0c\\u9759\\u6b62\\uff0c\\u6574\\u4f53\\u53d1\\u7070\\uff0c\\u6700\\u5dee\\u8d28\\u91cf\\uff0c\\u4f4e\\u8d28\\u91cf\\uff0cJPEG\\u538b\\u7f29\\u6b8b\\u7559\\uff0c\\u4e11\\u964b\\u7684\\uff0c\\u6b8b\\u7f3a\\u7684\\uff0c\\u591a\\u4f59\\u7684\\u624b\\u6307\\uff0c\\u753b\\u5f97\\u4e0d\\u597d\\u7684\\u624b\\u90e8\\uff0c\\u753b\\u5f97\\u4e0d\\u597d\\u7684\\u8138\\u90e8\\uff0c\\u7578\\u5f62\\u7684\\uff0c\\u6bc1\\u5bb9\\u7684\\uff0c\\u5f62\\u6001\\u7578\\u5f62\\u7684\\u80a2\\u4f53\\uff0c\\u624b\\u6307\\u878d\\u5408\\uff0c\\u9759\\u6b62\\u4e0d\\u52a8\\u7684\\u753b\\u9762\\uff0c\\u6742\\u4e71\\u7684\\u80cc\\u666f\\uff0c\\u4e09\\u6761\\u817f\\uff0c\\u80cc\\u666f\\u4eba\\u5f88\\u591a\\uff0c\\u5012\\u7740\\u8d70\\uff0c\\u88f8\\u9732\\uff0cNSFW", "clip": ["71", 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Negative Prompt)"}}, "73": {"inputs": {"vae_name": "wan_2.1_vae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}}, "74": {"inputs": {"width": 640, "height": 640, "length": 81, "batch_size": 1}, "class_type": "EmptyHunyuanLatentVideo", "_meta": {"title": "Empty HunyuanVideo 1.0 Latent"}}, "75": {"inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader", "_meta": {"title": "Load Diffusion Model"}}, "76": {"inputs": {"unet_name": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader", "_meta": {"title": "Load Diffusion Model"}}, "78": {"inputs": {"add_noise": "disable", "noise_seed": 0, "steps": 4, "cfg": 1, "sampler_name": "euler", "scheduler": "simple", "start_at_step": 2, "end_at_step": 4, "return_with_leftover_noise": "disable", "model": ["86", 0], "positive": ["89", 0], "negative": ["72", 0], "latent_image": ["81", 0]}, "class_type": "KSamplerAdvanced", "_meta": {"title": "KSampler (Advanced)"}}, "80": {"inputs": {"filename_prefix": "video/ComfyUI", "format": "auto", "codec": "auto", "video-preview": "", "video": ["88", 0]}, "class_type": "SaveVideo", "_meta": {"title": "Save Video"}}, "81": {"inputs": {"add_noise": "enable", "noise_seed": 1025340499108337, "steps": 4, "cfg": 1, "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable", "model": ["82", 0], "positive": ["89", 0], "negative": ["72", 0], "latent_image": ["74", 0]}, "class_type": "KSamplerAdvanced", "_meta": {"title": "KSampler (Advanced)"}}, "82": {"inputs": {"shift": 5.000000000000001, "model": ["83", 0]}, "class_type": "ModelSamplingSD3", "_meta": {"title": "ModelSamplingSD3"}}, "83": {"inputs": {"lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "strength_model": 1.0000000000000002, "model": ["75", 0]}, "class_type": "LoraLoaderModelOnly", "_meta": {"title": "Load LoRA"}}, "85": {"inputs": {"lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors", "strength_model": 1.0000000000000002, "model": ["76", 0]}, "class_type": "LoraLoaderModelOnly", "_meta": {"title": "Load LoRA"}}, "86": {"inputs": {"shift": 5.000000000000001, "model": ["85", 0]}, "class_type": "ModelSamplingSD3", "_meta": {"title": "ModelSamplingSD3"}}, "87": {"inputs": {"samples": ["78", 0], "vae": ["73", 0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}}, "88": {"inputs": {"fps": 16, "images": ["87", 0]}, "class_type": "CreateVideo", "_meta": {"title": "Create Video"}}, "89": {"inputs": {"text": "Beautiful young European woman with honey blonde hair gracefully turning her head back over shoulder, gentle smile, bright eyes looking at camera. Hair flowing in slow motion as she turns. Soft natural lighting, clean background, cinematic slow-motion portrait.", "clip": ["71", 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Positive Prompt)"}}}, "wan22_i2v": {"97": {"inputs": {"image": "video_wan2_2_14B_i2v_input_image.jpg"}, "class_type": "LoadImage", "_meta": {"title": "Load Image"}}, "108": {"inputs": {"filename_prefix": "video/Wan2.2_i2v", "format": "auto", "codec": "auto", "video": ["129:94", 0]}, "class_type": "SaveVideo", "_meta": {"title": "Save Video"}}, "129:98": {"inputs": {"width": 640, "height": 640, "length": 81, "batch_size": 1, "positive": ["129:93", 0], "negative": ["129:89", 0], "vae": ["129:90", 0], "start_image": ["97", 0]}, "class_type": "WanImageToVideo", "_meta": {"title": "WanImageToVideo"}}, "129:94": {"inputs": {"fps": 16, "images": ["129:87", 0]}, "class_type": "CreateVideo", "_meta": {"title": "Create Video"}}, "129:104": {"inputs": {"shift": 5.000000000000001, "model": ["129:116", 0]}, "class_type": "ModelSamplingSD3", "_meta": {"title": "ModelSamplingSD3"}}, "129:89": {"inputs": {"text": "\\u8272\\u8c03\\u8273\\u4e3d\\uff0c\\u8fc7\\u66dd\\uff0c\\u9759\\u6001\\uff0c\\u7ec6\\u8282\\u6a21\\u7cca\\u4e0d\\u6e05\\uff0c\\u5b57\\u5e55\\uff0c\\u98ce\\u683c\\uff0c\\u4f5c\\u54c1\\uff0c\\u753b\\u4f5c\\uff0c\\u753b\\u9762\\uff0c\\u9759\\u6b62\\uff0c\\u6574\\u4f53\\u53d1\\u7070\\uff0c\\u6700\\u5dee\\u8d28\\u91cf\\uff0c\\u4f4e\\u8d28\\u91cf\\uff0cJPEG\\u538b\\u7f29\\u6b8b\\u7559\\uff0c\\u4e11\\u964b\\u7684\\uff0c\\u6b8b\\u7f3a\\u7684\\uff0c\\u591a\\u4f59\\u7684\\u624b\\u6307\\uff0c\\u753b\\u5f97\\u4e0d\\u597d\\u7684\\u624b\\u90e8\\uff0c\\u753b\\u5f97\\u4e0d\\u597d\\u7684\\u8138\\u90e8\\uff0c\\u7578\\u5f62\\u7684\\uff0c\\u6bc1\\u5bb9\\u7684\\uff0c\\u5f62\\u6001\\u7578\\u5f62\\u7684\\u80a2\\u4f53\\uff0c\\u624b\\u6307\\u878d\\u5408\\uff0c\\u9759\\u6b62\\u4e0d\\u52a8\\u7684\\u753b\\u9762\\uff0c\\u6742\\u4e71\\u7684\\u80cc\\u666f\\uff0c\\u4e09\\u6761\\u817f\\uff0c\\u80cc\\u666f\\u4eba\\u5f88\\u591a\\uff0c\\u5012\\u7740\\u8d70", "clip": ["129:84", 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Negative Prompt)"}}, "129:128": {"inputs": {"value": 20}, "class_type": "PrimitiveInt", "_meta": {"title": "Steps"}}, "129:87": {"inputs": {"samples": ["129:85", 0], "vae": ["129:90", 0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}}, "129:93": {"inputs": {"text": "The white dragon warrior stands still, eyes full of determination and strength. The camera slowly moves closer or circles around the warrior, highlighting the powerful presence and heroic spirit of the character.", "clip": ["129:84", 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Positive Prompt)"}}, "129:131": {"inputs": {"value": true}, "class_type": "PrimitiveBoolean", "_meta": {"title": "Enable 4steps LoRA?"}}, "129:90": {"inputs": {"vae_name": "wan_2.1_vae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}}, "129:84": {"inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}, "class_type": "CLIPLoader", "_meta": {"title": "Load CLIP"}}, "129:96": {"inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader", "_meta": {"title": "Load Diffusion Model"}}, "129:95": {"inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader", "_meta": {"title": "Load Diffusion Model"}}, "129:127": {"inputs": {"value": 10}, "class_type": "PrimitiveInt", "_meta": {"title": "split_step"}}, "129:126": {"inputs": {"value": 3.5}, "class_type": "PrimitiveFloat", "_meta": {"title": "CFG"}}, "129:102": {"inputs": {"lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", "strength_model": 1.0000000000000002, "model": ["129:96", 0]}, "class_type": "LoraLoaderModelOnly", "_meta": {"title": "Load LoRA"}}, "129:101": {"inputs": {"lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", "strength_model": 1.0000000000000002, "model": ["129:95", 0]}, "class_type": "LoraLoaderModelOnly", "_meta": {"title": "Load LoRA"}}, "129:86": {"inputs": {"add_noise": "enable", "noise_seed": 264244520398999, "steps": ["129:119", 0], "cfg": ["129:120", 0], "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0, "end_at_step": ["129:125", 0], "return_with_leftover_noise": "enable", "model": ["129:104", 0], "positive": ["129:98", 0], "negative": ["129:98", 1], "latent_image": ["129:98", 2]}, "class_type": "KSamplerAdvanced", "_meta": {"title": "KSampler (Advanced)"}}, "129:85": {"inputs": {"add_noise": "disable", "noise_seed": 0, "steps": ["129:119", 0], "cfg": ["129:120", 0], "sampler_name": "euler", "scheduler": "simple", "start_at_step": ["129:125", 0], "end_at_step": ["129:119", 0], "return_with_leftover_noise": "disable", "model": ["129:103", 0], "positive": ["129:98", 0], "negative": ["129:98", 1], "latent_image": ["129:86", 0]}, "class_type": "KSamplerAdvanced", "_meta": {"title": "KSampler (Advanced)"}}, "129:122": {"inputs": {"value": 1}, "class_type": "PrimitiveFloat", "_meta": {"title": "CFG"}}, "129:124": {"inputs": {"value": 2}, "class_type": "PrimitiveInt", "_meta": {"title": "split_step"}}, "129:118": {"inputs": {"value": 4}, "class_type": "PrimitiveInt", "_meta": {"title": "Steps"}}, "129:116": {"inputs": {"switch": ["129:131", 0], "on_false": ["129:95", 0], "on_true": ["129:101", 0]}, "class_type": "ComfySwitchNode", "_meta": {"title": "Switch (Model)"}}, "129:125": {"inputs": {"switch": ["129:131", 0], "on_false": ["129:127", 0], "on_true": ["129:124", 0]}, "class_type": "ComfySwitchNode", "_meta": {"title": "Switch (Split Step)"}}, "129:119": {"inputs": {"switch": ["129:131", 0], "on_false": ["129:128", 0], "on_true": ["129:118", 0]}, "class_type": "ComfySwitchNode", "_meta": {"title": "Switch (Steps)"}}, "129:120": {"inputs": {"switch": ["129:131", 0], "on_false": ["129:126", 0], "on_true": ["129:122", 0]}, "class_type": "ComfySwitchNode", "_meta": {"title": "Switch (CFG)"}}, "129:103": {"inputs": {"shift": 5.000000000000001, "model": ["129:117", 0]}, "class_type": "ModelSamplingSD3", "_meta": {"title": "ModelSamplingSD3"}}, "129:117": {"inputs": {"switch": ["129:131", 0], "on_false": ["129:96", 0], "on_true": ["129:102", 0]}, "class_type": "ComfySwitchNode", "_meta": {"title": "Switch (Model)"}}}, "ace_step_t2a": {"14": {"inputs": {"tags": "anime, soft female vocals, kawaii pop, j-pop, childish, piano, guitar, synthesizer, fast, happy, cheerful, lighthearted", "lyrics": "Verse\\nNeon rain on my screen,\\nDreams compile in silver sheen.\\nNo weight, just motion,\\nI\'m plugged into emotion.\\n\\nChorus\\nComfy Cloud \\u2014 breathing light,\\nCode and color, spark and wire.\\nDrift through data, feel alive,\\nIn your circuits, I arrive.", "lyrics_strength": 0.9900000000000002, "clip": ["40", 1]}, "class_type": "TextEncodeAceStepAudio", "_meta": {"title": "TextEncodeAceStepAudio"}}, "17": {"inputs": {"seconds": 120, "batch_size": 1}, "class_type": "EmptyAceStepLatentAudio", "_meta": {"title": "Empty Ace Step 1.0 Latent Audio"}}, "18": {"inputs": {"samples": ["52", 0], "vae": ["40", 2]}, "class_type": "VAEDecodeAudio", "_meta": {"title": "VAE Decode Audio"}}, "40": {"inputs": {"ckpt_name": "ace_step_v1_3.5b.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load Checkpoint"}}, "44": {"inputs": {"conditioning": ["14", 0]}, "class_type": "ConditioningZeroOut", "_meta": {"title": "ConditioningZeroOut"}}, "49": {"inputs": {"model": ["51", 0], "operation": ["50", 0]}, "class_type": "LatentApplyOperationCFG", "_meta": {"title": "LatentApplyOperationCFG"}}, "50": {"inputs": {"multiplier": 1.0000000000000002}, "class_type": "LatentOperationTonemapReinhard", "_meta": {"title": "LatentOperationTonemapReinhard"}}, "51": {"inputs": {"shift": 5.000000000000001, "model": ["40", 0]}, "class_type": "ModelSamplingSD3", "_meta": {"title": "ModelSamplingSD3"}}, "52": {"inputs": {"seed": 336319031743227, "steps": 50, "cfg": 5, "sampler_name": "euler", "scheduler": "simple", "denoise": 1, "model": ["49", 0], "positive": ["14", 0], "negative": ["44", 0], "latent_image": ["17", 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}}, "59": {"inputs": {"filename_prefix": "audio/ComfyUI", "quality": "V0", "audioUI": "", "audio": ["18", 0]}, "class_type": "SaveAudioMP3", "_meta": {"title": "Save Audio (MP3)"}}}}')

# Node IDs from the exported templates (same as Ollama Studio's comfyui_common.py).
_IMG = {"prompt": "57:27", "latent": "57:13", "sampler": "57:3", "save": "9"}
_EDIT = {"image": "78", "prompt": "435", "sampler": "433:3", "save": "60",
         "encoders": ("433:110", "433:111")}  # TextEncodeQwenImageEditPlus (neg, pos): image2/image3 = extra refs
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
        image_ref: str = "latest",
        character_refs: str = "",
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
            Say explicitly what must stay unchanged (e.g. "keep the robot's brass color and design").
        :param image_ref: Which image to start from: "latest" (default: the newest image in the chat, or the one the user
            just attached), "previous", "first", or an image number such as "1" (every image result reports its number).
            To keep a character consistent in a new scene, pass the number of the image that shows that character best.
        :param character_refs: Optional. Up to 2 more image numbers (e.g. "1" or "1,3") used as identity references, so a
            character/object looks the same as in those images. The base image (image_ref) is "Picture 1" and the
            references are "Picture 2" and "Picture 3": refer to them that way in the instruction, e.g. "Show the robot from
            Picture 2 walking in a sunny park; keep its brass color and blue eyes exactly as in Picture 2".
        :return: Status JSON. The edited image is already shown to the user in the chat.
        """
        try:
            src, src_name = await self._pick_image(__user__, __metadata__, __chat_id__, __message_id__, image_ref)
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
        ref_names = []
        for n, ref in enumerate([r for r in re.split(r"[^0-9]+", character_refs or "") if r][:2], start=2):
            try:
                ref_bytes, ref_name = await self._pick_image(__user__, __metadata__, __chat_id__, __message_id__, ref)
                ref_up = await self._upload(ref_bytes)
            except Exception as e:
                return self._error(f"character_refs: {e}")
            wf[f"ref{n}"] = {"class_type": "LoadImage", "inputs": {"image": ref_up}}
            for enc in _EDIT["encoders"]:
                wf[enc]["inputs"][f"image{n}"] = [f"ref{n}", 0]
            ref_names.append(ref_name)
        return await self._run(
            "image", wf, _EDIT["save"], "image/png", self.valves.IMAGE_TIMEOUT,
            f"Editing {src_name}" + (f" with {' and '.join(ref_names)} as character reference" if ref_names else ""),
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
        image_ref: str = "latest",
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
        :param image_ref: Which image to start from: "latest" (default: the newest image in the chat, or the one the user
            just attached), "previous", "first", or an image number such as "1" (every image result reports its number).
            To keep a character consistent in a new scene, pass the number of the image that shows that character best.
        :return: Status JSON. The video is already shown to the user in the chat.
        """
        try:
            src, src_name = await self._pick_image(__user__, __metadata__, __chat_id__, __message_id__, image_ref)
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

    async def make_movie(
        self,
        video_refs: str = "all",
        soundtrack: str = "clips",
        song_ref: str = "latest",
        music_style: str = "",
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> Any:
        """
        Combine video clips from this chat into one movie (in order), e.g. to finish a story. Runs ffmpeg; no new
        video is generated, so it takes seconds (a new soundtrack adds ~10-20 s).

        :param video_refs: "all" (default: every video in the chat, oldest first) or video numbers in the order to use, e.g. "1,2,3".
        :param soundtrack: "clips" (default: keep each clip's own audio), "song" (use a music track already made in this chat, see song_ref),
            "new" (generate one continuous track for the whole movie from music_style) or "none" (silent).
        :param song_ref: For soundtrack="song": "latest" (default) or an audio number.
        :param music_style: For soundtrack="new": music style tags, e.g. "warm hopeful orchestral, strings, piano".
        :return: Status JSON. The movie is already shown to the user in the chat.
        """
        import os
        import tempfile

        videos = await self._chat_media(__metadata__, __chat_id__, __message_id__, "video/")
        if not videos:
            return self._error("There are no videos in this chat yet.")
        ref = (video_refs or "all").strip().lower()
        if ref in ("", "all"):
            chosen = list(range(len(videos)))
        else:
            chosen = [int(n) - 1 for n in re.split(r"[^0-9]+", ref) if n]
            bad = [i + 1 for i in chosen if not 0 <= i < len(videos)]
            if bad or not chosen:
                return self._error(f"video_refs {video_refs!r}: this chat has {len(videos)} video(s), numbered 1-{len(videos)}.")
        mode = (soundtrack or "clips").strip().lower()
        if mode not in ("clips", "song", "new", "none"):
            return self._error('soundtrack must be "clips", "song", "new" or "none".')
        label = f"Making a movie from {len(chosen)} clip(s)"
        await self._status(__event_emitter__, label)
        t0 = time.monotonic()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                clips = []
                for k, i in enumerate(chosen):
                    data = await self._read_file(videos[i]["id"], __user__) if videos[i]["id"] else None
                    if not data:
                        return self._error(f"Could not read video #{i + 1}.")
                    path = os.path.join(tmp, f"clip{k}.mp4")
                    open(path, "wb").write(data)
                    clips.append(path)
                w, h = await self._probe_size(clips[0])
                parts = []
                for k, c in enumerate(clips):  # normalise size/fps, give every clip an audio track
                    out = os.path.join(tmp, f"norm{k}.mp4")
                    has_audio = await self._has_audio(c)
                    cmd = ["ffmpeg", "-y", "-v", "error", "-i", c]
                    if not has_audio:
                        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
                    cmd += ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps=16,format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-ar", "44100", "-ac", "2"]
                    if not has_audio:
                        cmd += ["-shortest"]
                    await self._ffmpeg(cmd + [out])
                    parts.append(out)
                listing = os.path.join(tmp, "list.txt")
                open(listing, "w").write("".join(f"file '{p}'\n" for p in parts))
                joined = os.path.join(tmp, "joined.mp4")
                await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", joined])
                total = await self._duration(joined)
                final = joined
                if mode in ("song", "new", "none"):
                    final = os.path.join(tmp, "final.mp4")
                    if mode == "none":
                        await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-i", joined, "-an", "-c:v", "copy", final])
                    else:
                        if mode == "song":
                            songs = await self._chat_media(__metadata__, __chat_id__, __message_id__, "audio/")
                            if not songs:
                                return self._error('No music in this chat yet: use soundtrack="new" or generate_music first.')
                            r = (song_ref or "latest").strip().lower().lstrip("#")
                            si = len(songs) - 1 if r in ("", "latest", "last") else int(r) - 1 if r.isdigit() else -1
                            if not 0 <= si < len(songs):
                                return self._error(f"song_ref {song_ref!r}: this chat has {len(songs)} audio track(s).")
                            audio = await self._read_file(songs[si]["id"], __user__)
                        else:
                            if not (music_style or "").strip():
                                return self._error('soundtrack="new" needs music_style.')
                            await self._status(__event_emitter__, f"{label}: composing a {round(total)}s soundtrack")
                            awf = self._template("ace_step_t2a")
                            awf[_T2A["encode"]]["inputs"]["tags"] = music_style
                            awf[_T2A["encode"]]["inputs"]["lyrics"] = "[inst]"
                            awf[_T2A["latent"]]["inputs"]["seconds"] = max(5, int(total + 1))
                            awf[_T2A["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
                            audio = await self._comfy(awf, _T2A["save"], self.valves.AUDIO_TIMEOUT, label, __event_emitter__)
                        apath = os.path.join(tmp, "music.mp3")
                        open(apath, "wb").write(audio)
                        fade = max(0.0, total - 1.5)
                        await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-i", joined, "-i", apath, "-map", "0:v", "-map", "1:a",
                                            "-c:v", "copy", "-af", f"afade=t=out:st={fade:.2f}:d=1.5", "-c:a", "aac",
                                            "-t", f"{total:.3f}", final])
                movie = open(final, "rb").read()
        except ComfyError as e:
            await self._status(__event_emitter__, f"{label}: failed", done=True)
            return self._error(str(e))
        took = round(time.monotonic() - t0, 1)
        try:
            new_id = await self._publish("video", movie, "video/mp4", __request__, __user__, __metadata__,
                                         __chat_id__, __message_id__, __event_emitter__)
        except Exception as e:
            return self._error(f"Movie made, but saving to Open WebUI failed: {type(e).__name__}: {e}")
        await self._status(__event_emitter__, f"{label}: {round(total, 1)}s movie in {took}s", done=True)
        status = {"status": "success", "seconds_taken": took, "movie_seconds": round(total, 1),
                  "clips": [i + 1 for i in chosen], "soundtrack": mode,
                  "message": "The movie player is already visible to the user in the chat. Do not repeat links; "
                             "briefly describe the finished movie."}
        return HTMLResponse(content=self._media_embed("video", movie, "video/mp4", mode != "none"),
                            headers={"Content-Disposition": "inline"}), json.dumps(status)

    # --------------------------------------------------------------- ffmpeg helpers

    @staticmethod
    async def _ffmpeg(cmd: list, capture: bool = False) -> str:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise ComfyError(f"{cmd[0]} failed: {err.decode(errors='replace')[-300:]}")
        return out.decode()

    async def _probe_size(self, path: str) -> tuple:
        out = await self._ffmpeg(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                  "-of", "csv=p=0", path])
        w, h = out.strip().split(",")[:2]
        return int(w), int(h)

    async def _has_audio(self, path: str) -> bool:
        out = await self._ffmpeg(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                  "-of", "csv=p=0", path])
        return bool(out.strip())

    async def _duration(self, path: str) -> float:
        out = await self._ffmpeg(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
        return float(out.strip())

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
            new_id = await self._publish(kind, data, content_type, request, user, metadata, chat_id, message_id, emitter)
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
        try:
            ids = [i["id"] for i in await self._chat_media(metadata, chat_id, message_id, content_type.split("/")[0] + "/")]
            number = ids.index(new_id) + 1 if new_id in ids else None
        except Exception:
            number = None
        if number:
            status = json.loads(status_json)
            status[f"{kind}_number"] = number
            hint = {"image": f"pass image_ref=\"{number}\" (or character_refs) to edit_image/animate_image to use it later.",
                    "video": f"make_movie can combine videos by number (video_refs).",
                    "audio": f"make_movie can use it as the film's soundtrack (soundtrack=\"song\", song_ref=\"{number}\")."}[kind]
            status["message"] += f" This is {kind} #{number} in the chat; {hint}"
            status_json = json.dumps(status)
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
        return item.id

    async def _chat_images(self, metadata, chat_id, message_id) -> list:
        return await self._chat_media(metadata, chat_id, message_id, "image/")

    async def _chat_media(self, metadata, chat_id, message_id, prefix="image/") -> list:
        """All files of one media type in this chat (attachments + generated), oldest first, de-duplicated."""
        per_message = []
        if chat_id:
            try:
                from open_webui.models.chats import Chats

                chat = await Chats.get_chat_by_id(chat_id)
                history = (chat.chat or {}).get("history", {}) if chat else {}
                msgs = history.get("messages", {}) or {}
                mid = message_id if message_id in msgs else history.get("currentId")
                seen = set()
                while mid and mid in msgs and mid not in seen:  # newest -> root
                    seen.add(mid)
                    per_message.append(msgs[mid].get("files") or [])
                    mid = msgs[mid].get("parentId")
            except Exception:
                pass
        ordered = [f for files in reversed(per_message) for f in files]
        ordered += list((metadata or {}).get("files") or [])  # current attachments (may not be saved yet)

        images, ids = [], set()
        for f in ordered:
            if not isinstance(f, dict):
                continue
            ctype = str(f.get("content_type") or ((f.get("file") or {}).get("meta") or {}).get("content_type") or "")
            if not (ctype.startswith(prefix) or (prefix == "image/" and f.get("type") == "image")):
                continue
            url = str(f.get("url") or "")
            fid = f.get("id") or (f.get("file") or {}).get("id")
            if not fid and not url.startswith("data:"):
                m = _FILE_ID_RE.search(url)
                fid = m.group(1) if m else None
            key = fid or url[:200]
            if not key or key in ids:
                continue
            ids.add(key)
            images.append({"id": fid, "url": url, "name": f.get("name") or "image"})
        return images

    async def _pick_image(self, user, metadata, chat_id, message_id, ref="latest") -> tuple:
        """Return (bytes, label) for image_ref: latest / previous / first / a 1-based image number."""
        images = await self._chat_images(metadata, chat_id, message_id)
        if not images:
            raise ComfyError("No image found. Ask the user to attach an image (or generate one first).")
        r = str(ref or "latest").strip().lower().lstrip("#").replace("image", "").strip()
        if r in ("", "latest", "last", "newest", "current"):
            idx = len(images) - 1
        elif r in ("previous", "prev", "second-to-last"):
            idx = max(0, len(images) - 2)
        elif r in ("first", "original"):
            idx = 0
        elif r.isdigit() and 1 <= int(r) <= len(images):
            idx = int(r) - 1
        else:
            raise ComfyError(f"image_ref {ref!r} not found: this chat has {len(images)} image(s), numbered 1-{len(images)}.")
        img = images[idx]
        if img["url"].startswith("data:image/"):
            data = base64.b64decode(img["url"].split(",", 1)[1])
        else:
            data = await self._read_file(img["id"], user) if img["id"] else None
        if not data:
            raise ComfyError(f"Could not read image #{idx + 1} ({img['name']}).")
        return data, f"image #{idx + 1}"

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
