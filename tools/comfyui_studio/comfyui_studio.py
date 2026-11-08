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
        QA_ENABLED: bool = Field(default=True, description="Check story-film keyframes with a vision model and redraw failures.")
        QA_RETRIES: int = Field(default=1, description="How many times a failed keyframe is redrawn.")
        QA_MODEL: str = Field(default="qwen3.8:27b", description="Ollama vision model used for keyframe checks.")
        OLLAMA_URL: str = Field(default="http://ollama-service:11434", description="Ollama API base URL, as seen from the Open WebUI pod.")
        QA_TIMEOUT: int = Field(default=180, description="Seconds to wait for one keyframe check.")

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
        Combine video clips already in this chat into one movie (in order). Runs ffmpeg; no new video is
        generated, so it takes seconds (a new soundtrack adds ~10-20 s). To make a whole new multi-shot film
        from a story, use make_story_film instead.

        :param video_refs: "all" (default: every video in the chat, oldest first) or video numbers in the order to use, e.g. "1,2,3".
        :param soundtrack: "clips" (default: keep each clip's own audio), "song" (use a music track already made in this chat, see song_ref),
            "new" (generate one continuous track for the whole movie from music_style) or "none" (silent).
        :param song_ref: For soundtrack="song": "latest" (default) or an audio number.
        :param music_style: For soundtrack="new": music style tags, e.g. "warm hopeful orchestral, strings, piano".
        :return: Status JSON. The movie is already shown to the user in the chat.
        """
        videos = await self._chat_media(__metadata__, __chat_id__, __message_id__, "video/")
        if not videos:
            return self._error("There are no videos in this chat yet.")
        ref = (video_refs or "all").strip().lower()
        if ref in ("", "all"):
            chosen = list(range(len(videos)))
        else:
            chosen = [int(n) - 1 for n in re.split(r"[^0-9]+", ref) if n]
            if not chosen or any(not 0 <= i < len(videos) for i in chosen):
                return self._error(f"video_refs {video_refs!r}: this chat has {len(videos)} video(s), numbered 1-{len(videos)}.")
        mode = (soundtrack or "clips").strip().lower()
        if mode not in ("clips", "song", "new", "none"):
            return self._error('soundtrack must be "clips", "song", "new" or "none".')
        label = f"Making a movie from {len(chosen)} clip(s)"
        await self._status(__event_emitter__, label)
        t0 = time.monotonic()
        try:
            clips = []
            for i in chosen:
                data = await self._read_file(videos[i]["id"], __user__) if videos[i]["id"] else None
                if not data:
                    return self._error(f"Could not read video #{i + 1}.")
                clips.append(data)
            audio = None
            if mode == "song":
                songs = await self._chat_media(__metadata__, __chat_id__, __message_id__, "audio/")
                if not songs:
                    return self._error('No music in this chat yet: use soundtrack="new" or generate_music first.')
                r = (song_ref or "latest").strip().lower().lstrip("#")
                si = len(songs) - 1 if r in ("", "latest", "last") else int(r) - 1 if r.isdigit() else -1
                if not 0 <= si < len(songs):
                    return self._error(f"song_ref {song_ref!r}: this chat has {len(songs)} audio track(s).")
                audio = await self._read_file(songs[si]["id"], __user__)
            elif mode == "new" and not (music_style or "").strip():
                return self._error('soundtrack="new" needs music_style.')
            movie, total, _ = await self._assemble(clips, mode, audio, music_style, "", label, __event_emitter__)
        except ComfyError as e:
            await self._status(__event_emitter__, f"{label}: failed", done=True)
            return self._error(str(e))
        took = round(time.monotonic() - t0, 1)
        try:
            await self._publish("video", movie, "video/mp4", __request__, __user__, __metadata__,
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

    async def make_story_film(
        self,
        shots: str,
        characters: str = "",
        style: str = "cinematic photoreal, soft natural lighting, shallow depth of field",
        seconds_per_shot: int = 4,
        music_style: str = "",
        lyrics: str = "",
        character: str = "",
        transitions: str = "cut",
        storyboard_only: bool = False,
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> Any:
        """
        Make a complete short film (about 15-30 s) from a story: several shots of 3-5 s each, the same characters
        throughout, and one continuous soundtrack. Use this whenever the user wants a story video, short film or anything
        longer than one clip. Takes about 1-1.5 minutes per shot. Afterwards, single shots can be changed with redo_shot.
        With storyboard_only=true it stops after the character sheets and keyframes (~15 s per shot) so the user can review
        and fix them (redo_shot) before animate_storyboard turns them into the film.

        :param shots: JSON array of 4-8 shots in story order, e.g.
            [{"scene": "wide shot: the robot stands alone in a rainy neon alley at night", "action": "rain falls, slow push-in", "expression": "lonely, wistful", "cast": ["robot"]},
             {"scene": "close-up: the robot crouches and reaches toward the kitten", "action": "...", "expression": "the kitten frightened, the robot gentle", "cast": ["robot", "kitten"], "continue": true}].
            "scene" = what the keyframe shows (setting, pose, framing/shot size, lighting); "action" = the motion and camera
            movement; "expression" = the characters' emotions/facial expressions in this shot; "cast" = names (from characters)
            visible in this shot, max 3, [] for none. "continue": true = follows straight on from the previous shot in the same
            place (starts from its last frame; with "scene" given, re-framed/changed as described).
        :param characters: JSON array of the recurring characters (people, animals, or important objects like a car), each
            described separately and in fixed, specific detail (body, colors, materials, face/eyes, clothing, size), e.g.
            [{"name": "robot", "description": "a small knee-high robot with a polished brass body, dome head, two round glowing blue eyes"},
             {"name": "kitten", "description": "a tiny fluffy grey-and-white kitten with green eyes"}].
            Optional per character: "image_ref" = an image number already in the chat to use as that character's sheet.
        :param style: One visual style for the whole film, repeated in every prompt. Default "cinematic photoreal, soft natural lighting, shallow depth of field".
        :param seconds_per_shot: 3-5 seconds per shot. Default 4.
        :param music_style: Music style tags for one continuous soundtrack under the whole film. Empty = an instrumental cinematic score.
        :param lyrics: Optional song lyrics for the soundtrack ([verse]/[chorus] markers). Leave empty for instrumental.
        :param character: Deprecated single-character description (use characters instead).
        :param transitions: "cut" (default: hard cuts) or "crossfade" (a short 0.4 s dissolve between shots: softer, dreamier).
        :param storyboard_only: true = only make the character sheets + keyframes for review (no animation yet). Use it when
            the user wants to see/approve a storyboard first.
        :return: Status JSON. The film (or storyboard), character sheets and keyframes are already shown to the user.
        """
        ctx = (__request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__)
        try:
            plan = self._parse_shots(shots)
            cast_list = self._parse_characters(characters, character)
        except ComfyError as e:
            return self._error(str(e))
        if not 2 <= len(plan) <= 10:
            return self._error(f"Give 2-10 shots (got {len(plan)}); 4-8 shots of 3-5 s make a 15-30 s film.")
        names = [c["name"] for c in cast_list]
        for shot in plan:
            shot["cast"] = self._match_cast(shot["cast"], cast_list) if "cast" in shot else names[:3]
        plan[0]["continue"] = False
        secs = max(3, min(int(seconds_per_shot or 4), 5))
        fade = 0.4 if str(transitions).strip().lower().startswith("cross") else 0.0
        style = (style or "").strip() or "cinematic photoreal"
        music = (music_style or "").strip() or "cinematic orchestral score, emotional, strings, piano"
        sb = str(storyboard_only).strip().lower() in ("true", "1", "yes")
        label = f"Story {'storyboard' if sb else 'film'}: {len(plan)} shots" + ("" if sb else f" x {secs}s")
        await self._status(__event_emitter__, label)
        t0 = time.monotonic()
        try:
            await self._make_sheets(cast_list, style, label, ctx)
            project = {"version": 3, "status": "storyboard", "style": style, "seconds_per_shot": secs, "crossfade": fade,
                       "music_style": music, "lyrics": lyrics, "characters": cast_list, "shots": plan}
            if sb:
                prev_kf = None
                for i, shot in enumerate(plan, start=1):
                    kf, kf_id = await self._shot_keyframe(i, len(plan), shot, prev_kf if shot.get("continue") else None,
                                                          cast_list, style, label, ctx)
                    shot["keyframe_file"] = kf_id
                    prev_kf = kf or prev_kf
                return await self._finish_storyboard(project, time.monotonic() - t0, label, ctx)
            movie, total = await self._animate_project(project, label, ctx, use_keyframes=False)
        except ComfyError as e:
            await self._status(__event_emitter__, f"{label}: failed", done=True)
            return self._error(str(e))
        return await self._finish_film(movie, total, project, time.monotonic() - t0, label, ctx,
                                       [{"shot": i, "cast": s["cast"], "start": "continues" if s.get("continue") else "new keyframe"}
                                        for i, s in enumerate(plan, start=1)])

    async def animate_storyboard(
        self,
        film_ref: str = "latest",
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> Any:
        """
        Turn an approved storyboard (made with make_story_film storyboard_only=true) into the finished film: animates every
        keyframe as shown, adds the continuous soundtrack. Takes about 1 minute per shot. Use when the user approves the
        storyboard ("looks good, animate it").

        :param film_ref: Which storyboard: "latest" (default) or a film number.
        :return: Status JSON. The film is already shown to the user in the chat.
        """
        ctx = (__request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__)
        try:
            project = await self._load_project(film_ref, __metadata__, __chat_id__, __message_id__, __user__)
        except ComfyError as e:
            return self._error(str(e))
        if project.get("status") != "storyboard":
            return self._error("That one is already a film. Use redo_shot to change shots, or make_story_film for a new one.")
        label = f"Animating storyboard: {len(project['shots'])} shots x {project['seconds_per_shot']}s"
        await self._status(__event_emitter__, label)
        t0 = time.monotonic()
        try:
            await self._upload_sheets(project["characters"], __user__)
            movie, total = await self._animate_project(project, label, ctx, use_keyframes=True)
        except ComfyError as e:
            await self._status(__event_emitter__, f"{label}: failed", done=True)
            return self._error(str(e))
        return await self._finish_film(movie, total, project, time.monotonic() - t0, label, ctx,
                                       [{"shot": i, "start": "storyboard keyframe" if s.get("keyframe_file") else "continues"}
                                        for i, s in enumerate(project["shots"], start=1)])

    async def redo_shot(
        self,
        shot: int,
        scene: str = "",
        action: str = "",
        expression: str = "",
        cast: str = "",
        film_ref: str = "latest",
        __request__=None,
        __user__: dict = None,
        __metadata__: dict = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> Any:
        """
        Change one shot of a storyboard or film made with make_story_film. On a storyboard it redraws just that keyframe
        (~15 s). On a finished film it regenerates the shot (and any following "continue" shots that depend on it) and
        rebuilds the film with the same soundtrack (~1-2 min). Use for "redo shot 3", "make the last shot zoom out more".

        :param shot: Shot number to redo (1 = first shot).
        :param scene: New keyframe description for the shot. Empty = keep the current one (just re-roll).
        :param action: New motion/camera description for the shot. Empty = keep the current one.
        :param expression: New emotions/facial expressions for the shot (e.g. "tense, Clyde shouting, the teller terrified"). Empty = keep.
        :param cast: Comma-separated character names in the shot (e.g. "robot" or "robot, kitten"). Empty = keep.
        :param film_ref: Which storyboard/film: "latest" (default) or a film number.
        :return: Status JSON. The updated storyboard keyframe or film is already shown to the user in the chat.
        """
        ctx = (__request__, __user__, __metadata__, __chat_id__, __message_id__, __event_emitter__)
        try:
            project = await self._load_project(film_ref, __metadata__, __chat_id__, __message_id__, __user__)
        except ComfyError as e:
            return self._error(str(e))
        plan, cast_list = project["shots"], project["characters"]
        k = int(shot or 0)
        if not 1 <= k <= len(plan):
            return self._error(f"shot must be 1-{len(plan)}.")
        for key, val in (("scene", scene), ("action", action), ("expression", expression)):
            if (val or "").strip():
                plan[k - 1][key] = val.strip()
        if (cast or "").strip():
            matched = self._match_cast(cast, cast_list)
            if not matched:
                return self._error(f"cast {cast!r} matches none of the characters: {', '.join(c['name'] for c in cast_list)}.")
            plan[k - 1]["cast"] = matched
        style = project["style"]
        label = f"Redoing shot {k}"
        t0 = time.monotonic()
        try:
            await self._upload_sheets(cast_list, __user__)
            if project.get("status") == "storyboard":
                label = f"Redrawing storyboard shot {k}"
                await self._status(__event_emitter__, label)
                prev_kf = None
                if plan[k - 1].get("continue"):
                    for j in range(k - 1, 0, -1):
                        if plan[j - 1].get("keyframe_file"):
                            prev_kf = await self._read_file(plan[j - 1]["keyframe_file"], __user__)
                            break
                kf, kf_id = await self._shot_keyframe(k, len(plan), plan[k - 1], prev_kf, cast_list, style, label, ctx)
                if kf_id:
                    plan[k - 1]["keyframe_file"] = kf_id
                return await self._finish_storyboard(project, time.monotonic() - t0, label, ctx)
            redo = [k] + [j for j in range(k + 1, len(plan) + 1)
                          if all(plan[x - 1].get("continue") for x in range(k + 1, j + 1))]
            label = f"Redoing shot {k}" + (f" (+ continuing shot{'s' if len(redo) > 2 else ''} {', '.join(map(str, redo[1:]))})" if len(redo) > 1 else "")
            await self._status(__event_emitter__, label)
            secs = self._shot_secs(project)
            clips = [await self._read_file(s["clip_file"], __user__) for s in plan]
            for j in redo:
                prev = clips[j - 2] if j > 1 else None
                start, kf_id = await self._shot_start(j, len(plan), plan[j - 1], prev, cast_list, style, label, ctx,
                                                      use_keyframe=False)
                plan[j - 1]["keyframe_file"] = kf_id
                clip = await self._animate_shot(j, len(plan), plan[j - 1], start, cast_list, style, secs, label, ctx)
                plan[j - 1]["clip_file"] = await self._store_hidden(clip, "video/mp4", f"comfy-shot{j}.mp4", __request__, __user__)
                clips[j - 1] = clip
            audio = await self._read_file(project["soundtrack_file"], __user__)
            movie, total, _ = await self._assemble(clips, "song", audio, "", "", label, __event_emitter__,
                                                   float(project.get("crossfade") or 0))
        except ComfyError as e:
            await self._status(__event_emitter__, f"{label}: failed", done=True)
            return self._error(str(e))
        return await self._finish_film(movie, total, project, time.monotonic() - t0, label, ctx, [{"redone_shots": redo}])

    # --------------------------------------------------------------- story film internals

    @staticmethod
    def _parse_shots(shots) -> list:
        try:
            plan = json.loads(shots) if isinstance(shots, str) else shots
            if isinstance(plan, dict):
                plan = plan.get("shots") or []
        except Exception:
            plan = [{"scene": l.strip(" -*"), "action": l.strip(" -*")} for l in str(shots).splitlines() if l.strip()]
        if not isinstance(plan, list):
            raise ComfyError("shots must be a JSON array.")
        out = []
        for p in plan:
            p = dict(p) if isinstance(p, dict) else {"scene": str(p), "action": str(p)}
            if isinstance(p.get("cast"), str):
                p["cast"] = [x.strip() for x in p["cast"].split(",") if x.strip()]
            out.append(p)
        return out

    @staticmethod
    def _parse_characters(characters, character) -> list:
        cl = []
        if characters:
            try:
                cl = json.loads(characters) if isinstance(characters, str) else characters
            except Exception:
                raise ComfyError('characters must be a JSON array like [{"name": "robot", "description": "..."}].')
            if isinstance(cl, dict):
                cl = [{"name": k, "description": v} for k, v in cl.items()]
        elif (character or "").strip():
            cl = [{"name": "main character", "description": character.strip()}]
        cl = [dict(c) for c in cl if isinstance(c, dict) and str(c.get("description", "")).strip()]
        if not cl:
            raise ComfyError("Describe at least one character (characters).")
        if len(cl) > 4:
            raise ComfyError("At most 4 recurring characters.")
        for i, c in enumerate(cl):
            c["name"] = str(c.get("name") or f"character {i + 1}").strip()
            c["description"] = str(c["description"]).strip()
        return cl

    @staticmethod
    def _norm(name) -> str:
        n = re.sub(r"\s+", " ", str(name or "")).strip().lower()
        return n[4:] if n.startswith("the ") else n

    def _match_cast(self, wanted, cast_list) -> list:
        """Canonical names (story order) for a cast given in any case/spacing, e.g. "Mira, the Pip" -> ["mira", "pip"]."""
        if isinstance(wanted, str):
            wanted = [w for w in wanted.split(",")]
        want = {self._norm(w) for w in (wanted or [])}
        return [c["name"] for c in cast_list if self._norm(c["name"]) in want][:3]

    @staticmethod
    def _shot_secs(project) -> float:
        n = len(project["shots"])
        fade = float(project.get("crossfade") or 0)
        return project["seconds_per_shot"] + fade * (n - 1) / n  # each dissolve overlaps two shots

    async def _make_sheets(self, cast_list, style, label, ctx):
        request, user, metadata, chat_id, message_id, emitter = ctx
        for c in cast_list:
            if c.get("image_ref"):
                data, _ = await self._pick_image(user, metadata, chat_id, message_id, str(c["image_ref"]))
            else:
                await self._status(emitter, f"{label}: {c['name']} reference sheet")
                w, h = _IMAGE_SIZES["landscape"]
                data = await self._comfy(self._t2i_wf(
                    f"Character reference image: {c['description']}. Only this one character, full body, standing in a "
                    f"relaxed natural three-quarter view, neutral expression, clearly visible, plain simple neutral "
                    f"background. {style}.", w, h),
                    _IMG["save"], self.valves.IMAGE_TIMEOUT, f"{label}: {c['name']} sheet", emitter)
            c["sheet_file"] = await self._publish("image", data, "image/png", *ctx)
            c["_up"] = await self._upload(data)
            c["_img"] = data

    async def _upload_sheets(self, cast_list, user):
        for c in cast_list:
            c["_img"] = await self._read_file(c["sheet_file"], user)
            c["_up"] = await self._upload(c["_img"])

    async def _load_project(self, film_ref, metadata, chat_id, message_id, user) -> dict:
        projects = [p for p in await self._chat_media(metadata, chat_id, message_id, "application/json")
                    if str(p.get("name", "")).startswith("comfy-film")]
        if not projects:
            raise ComfyError("No storyboard or film made with make_story_film in this chat yet.")
        r = str(film_ref or "latest").strip().lower().lstrip("#")
        idx = len(projects) - 1 if r in ("", "latest", "last") else int(r) - 1 if r.isdigit() else -1
        if not 0 <= idx < len(projects):
            raise ComfyError(f"film_ref {film_ref!r}: this chat has {len(projects)} storyboard/film version(s).")
        return json.loads((await self._read_file(projects[idx]["id"], user)).decode())

    async def _last_frame(self, clip: bytes) -> bytes:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "prev.mp4"); open(p, "wb").write(clip)
            f = os.path.join(tmp, "last.png")
            await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.15", "-i", p, "-frames:v", "1", "-update", "1", f])
            return open(f, "rb").read()

    def _prompt_bits(self, shot, cast_list):
        wanted = {self._norm(c) for c in shot.get("cast", [])}
        # keep the story's character order (main character first): Picture 1 is the edit's base image and its
        # features leak most, so it should not depend on how a shot happens to list its cast
        cast = [c for c in cast_list if self._norm(c["name"]) in wanted][:3]
        who = "; ".join(f"the {c['name']} is {c['description']}" for c in cast)
        expr = str(shot.get("expression") or "").strip()
        lock = ("Each character keeps exactly its own design, colors, materials and proportions; colored lights, "
                "reflections and props must not change any character's colors. Each character has only its own anatomy "
                "and features as in its picture: wings, horns, tails, fur, scales, colors or clothes of one character never "
                "appear on another.")
        candid = ("This is a candid frame from a film, not a portrait: the characters are caught mid-action, in the poses "
                  "and with the expressions the scene calls for, looking at each other or at what is happening, never "
                  "at the camera and never posing or smiling for the camera.")
        feel = f"Facial expressions and mood: {expr}." if expr else ""
        if cast:
            names = ", ".join(c["name"] for c in cast)
            others = [c["name"] for c in cast_list if c not in cast]
            lock += (f" Each of {names} appears exactly once and is clearly visible and recognizable (face, hair and "
                     f"outfit exactly as in its picture), even when small or inside a vehicle (seen through a window). "
                     f"Any other people in the scene (extras such as a bank teller, police or passers-by) are clearly "
                     f"different people who look nothing like {names}: different age, face, hair and clothes; nobody "
                     f"else wears their outfits.")
            if others:
                lock += f" {', '.join(others)} {'is' if len(others) == 1 else 'are'} not in this shot."
        return cast, who, lock, candid, feel

    async def _shot_keyframe(self, i, n, shot, base, cast_list, style, label, ctx) -> tuple:
        """Keyframe for one shot -> (png bytes or None, published file id or None).

        base = image to continue from (previous clip's last frame, or in a storyboard the previous keyframe) for
        "continue" shots; a continue shot without its own scene has no keyframe of its own (returns None, None).
        With QA_ENABLED, the keyframe is checked by a vision model against the shot plan and redrawn once with the
        reported problems as extra instructions."""
        emitter = ctx[5]
        cast, who, lock, candid, feel = self._prompt_bits(shot, cast_list)
        scene = str(shot.get("scene") or "").strip()
        tag = f"{label}: shot {i}/{n}"
        if shot.get("continue") and base is not None and not scene:
            return None, None
        base_up = await self._upload(base) if (shot.get("continue") and base is not None) else None

        async def draw(fix: str) -> bytes:
            fix = f" Fix these problems from the previous attempt: {fix}." if fix else ""
            if base_up:
                pics = "".join(f" The {c['name']} must look exactly like the one in Picture {k + 2}." for k, c in enumerate(cast[:2]))
                return await self._comfy(self._edit_wf(base_up,
                    f"Continue this exact moment from Picture 1 (same place, same characters, same lighting): {scene}.{pics} "
                    f"{who + '. ' if who else ''}{feel}{fix} {candid} {lock} Style: {style}.", [c["_up"] for c in cast][:2]),
                    _EDIT["save"], self.valves.IMAGE_TIMEOUT, f"{tag}: keyframe", emitter)
            if cast:
                pics = " and ".join(f"the {c['name']} from Picture {k + 1}" for k, c in enumerate(cast))
                return await self._comfy(self._edit_wf(cast[0]["_up"],
                    f"Create a new image showing {pics} in this scene: {scene}. {who}. Keep every character exactly as in its "
                    f"picture, but in the pose the scene describes. {feel}{fix} Replace the whole background with the scene. "
                    f"No other recurring characters appear. {candid} {lock} Style: {style}.", [c["_up"] for c in cast[1:]]),
                    _EDIT["save"], self.valves.IMAGE_TIMEOUT, f"{tag}: keyframe", emitter)
            w, h = _IMAGE_SIZES["landscape"]  # no recurring character (establishing shot, landscape, ...)
            return await self._comfy(self._t2i_wf(f"{scene}. {feel}{fix} {style}.", w, h), _IMG["save"],
                                     self.valves.IMAGE_TIMEOUT, f"{tag}: keyframe", emitter)

        await self._status(emitter, f"{tag}: keyframe" + (" (continuing)" if base_up else ""))
        img = await draw("")
        if self.valves.QA_ENABLED:
            ok, problems = await self._qa_check(img, shot, cast, cast_list, tag, emitter)
            if ok:
                shot["qa"] = "passed"
            else:
                first = problems
                for _ in range(max(0, int(self.valves.QA_RETRIES))):
                    await self._status(emitter, f"{tag}: redrawing keyframe ({'; '.join(problems)[:120]})")
                    img = await draw("; ".join(problems))
                    ok, problems = await self._qa_check(img, shot, cast, cast_list, tag, emitter)
                    if ok:
                        break
                shot["qa"] = ("fixed: " + "; ".join(first)) if ok else ("unresolved: " + "; ".join(problems))
        return img, await self._publish("image", img, "image/png", *ctx)

    async def _qa_check(self, img: bytes, shot: dict, cast: list, cast_list: list, tag: str, emitter) -> tuple:
        """Ask a vision model whether a keyframe matches its shot plan -> (ok, [problems]). Errors count as ok."""
        try:
            await self._status(emitter, f"{tag}: checking keyframe")
            refs = [c for c in cast if c.get("_img")]
            absent = [c["name"] for c in cast_list if c not in cast]
            lines = [f"{k + 1}) {c['name']}: {c['description']}" for k, c in enumerate(refs)]
            prompt = (
                "You check one keyframe of a short film against its shot plan. "
                + (f"The first {len(refs)} image(s) are reference pictures of the recurring characters, in this order:\n"
                   + "\n".join(lines) + "\n" if refs else "")
                + "The LAST image is the keyframe to check.\n"
                f"Shot plan - scene: {shot.get('scene') or '(continues the previous shot)'}\n"
                f"expression/mood: {shot.get('expression') or '-'}\n"
                f"must show (each exactly once): {', '.join(c['name'] for c in cast) or 'none of the recurring characters'}\n"
                f"must NOT show: {', '.join(absent) or '-'}\n"
                "Fail ONLY for these serious problems: (1) a listed character is missing, appears more than once, or clearly "
                "does not resemble its reference picture (face, hair, outfit, colors, body shape); (2) another person or "
                "creature is a look-alike copy of a listed character; (3) a character that must not be shown appears; "
                "(4) a character has body parts or features it does not have in its reference picture, especially ones "
                "belonging to another character (e.g. wings, horns, tail, armor); (5) the setting is completely wrong, or "
                "the camera viewpoint/direction contradicts the plan; (6) the characters pose or smile for the camera.\n"
                "Do NOT fail for poses, hand positions, props, exact expressions, lighting or composition details.\n"
                'Reply with JSON only: {"pass": true or false, "problems": ["short, specific instruction that would fix it", ...]}. '
                "problems must be empty when pass is true."
            )
            images = [self._small_b64(c["_img"], 448) for c in refs] + [self._small_b64(img, 896)]
            base = self.valves.OLLAMA_URL.rstrip("/")
            async with aiohttp.ClientSession() as s:
                num_ctx = None
                async with s.get(f"{base}/api/ps", timeout=aiohttp.ClientTimeout(total=10)) as r:
                    for m in (await r.json()).get("models", []):
                        if m.get("name") == self.valves.QA_MODEL:
                            num_ctx = m.get("context_length")  # reuse it so Ollama doesn't reload the model
                body = {"model": self.valves.QA_MODEL, "stream": False, "think": False, "format": "json",
                        "messages": [{"role": "user", "content": prompt, "images": images}],
                        "options": {"temperature": 0, **({"num_ctx": num_ctx} if num_ctx else {})}}
                async with s.post(f"{base}/api/chat", json=body,
                                  timeout=aiohttp.ClientTimeout(total=self.valves.QA_TIMEOUT)) as r:
                    out = (await r.json()).get("message", {}).get("content", "")
            verdict = json.loads(out[out.find("{"): out.rfind("}") + 1])
            problems = [str(p) for p in verdict.get("problems") or [] if str(p).strip()][:4]
            ok = bool(verdict.get("pass")) or not problems
            return ok, problems
        except Exception:
            return True, []

    @staticmethod
    def _small_b64(data: bytes, max_side: int) -> str:
        try:
            from PIL import Image

            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((max_side, max_side))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85)
            data = buf.getvalue()
        except Exception:
            pass
        return base64.b64encode(data).decode()

    async def _shot_start(self, i, n, shot, prev_clip, cast_list, style, label, ctx, use_keyframe) -> tuple:
        """Start frame for animating a shot -> (png bytes, keyframe file id or None)."""
        if use_keyframe and shot.get("keyframe_file"):
            return await self._read_file(shot["keyframe_file"], ctx[1]), shot["keyframe_file"]
        base = await self._last_frame(prev_clip) if shot.get("continue") and prev_clip is not None else None
        img, kf_id = await self._shot_keyframe(i, n, shot, base, cast_list, style, label, ctx)
        return (img if img is not None else base), kf_id

    async def _animate_shot(self, i, n, shot, start, cast_list, style, secs, label, ctx) -> bytes:
        cast, who, lock, candid, feel = self._prompt_bits(shot, cast_list)
        action = str(shot.get("action") or shot.get("scene") or "subtle natural movement").strip()
        w, h = self._video_size_for(start)
        tag = f"{label}: shot {i}/{n}"
        await self._status(ctx[5], f"{tag}: animating")
        return await self._comfy(self._i2v_wf(await self._upload(start),
            f"{action}. {who + '. ' if who else ''}{feel} The characters act naturally and never look at the camera. "
            f"Only the people, animals and objects already in the first frame appear: nobody new enters or appears in the "
            f"foreground. {lock} {style}. Smooth, natural, clearly visible motion.", w, h, secs),
            _I2V["save"], self.valves.VIDEO_TIMEOUT, f"{tag}: animating", ctx[5])

    async def _animate_project(self, project, label, ctx, use_keyframes) -> tuple:
        """Animate every shot of a project (making keyframes unless use_keyframes) + soundtrack. Updates project."""
        request, user = ctx[0], ctx[1]
        plan, cast_list, style = project["shots"], project["characters"], project["style"]
        secs = self._shot_secs(project)
        clips, prev = [], None
        for i, shot in enumerate(plan, start=1):
            start, kf_id = await self._shot_start(i, len(plan), shot, prev, cast_list, style, label, ctx, use_keyframes)
            shot["keyframe_file"] = kf_id
            clip = await self._animate_shot(i, len(plan), shot, start, cast_list, style, secs, label, ctx)
            shot["clip_file"] = await self._store_hidden(clip, "video/mp4", f"comfy-shot{i}.mp4", request, user)
            clips.append(clip)
            prev = clip
        movie, total, audio = await self._assemble(clips, "new", None, project["music_style"], project.get("lyrics", ""),
                                                   label, ctx[5], float(project.get("crossfade") or 0))
        project["soundtrack_file"] = await self._store_hidden(audio, "audio/mpeg", "comfy-soundtrack.mp3", request, user)
        project["status"] = "film"
        return movie, total

    def _clean_project(self, project) -> bytes:
        p = dict(project)
        p["characters"] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in project.get("characters", [])]
        return json.dumps(p, indent=1, default=str).encode()

    async def _finish_storyboard(self, project, took, label, ctx) -> Any:
        request, user, metadata, chat_id, message_id, emitter = ctx
        try:
            await self._publish("film", self._clean_project(project), "application/json", *ctx)
        except Exception as e:
            return self._error(f"Storyboard made, but saving to Open WebUI failed: {type(e).__name__}: {e}")
        await self._status(emitter, f"{label}: done in {round(took)}s", done=True)
        shots = [{"shot": i, "keyframe": bool(s.get("keyframe_file")), "cast": s.get("cast"), "check": s.get("qa", "-"),
                  "note": "" if s.get("keyframe_file") else "continues from the previous shot (no keyframe of its own)"}
                 for i, s in enumerate(project["shots"], start=1)]
        return json.dumps({"status": "success", "storyboard": True, "seconds_taken": round(took), "shots": shots,
                           "message": "The storyboard (character sheets + one keyframe per shot) is already visible to the "
                                      "user. Do not repeat links. List the shots briefly by number (mention any shot whose "
                                      "automatic check is 'unresolved' and what is wrong) and ask the user to "
                                      "approve or request changes. Changes: redo_shot(shot=N, scene/expression/cast...). "
                                      "When approved: animate_storyboard(). Do NOT call any tool now: wait for the "
                                      "user's reply."})

    async def _finish_film(self, movie, total, project, took, label, ctx, report) -> Any:
        request, user, metadata, chat_id, message_id, emitter = ctx
        try:
            await self._publish("video", movie, "video/mp4", *ctx)
            await self._publish("film", self._clean_project(project), "application/json", *ctx)
            films = [p for p in await self._chat_media(metadata, chat_id, message_id, "application/json")
                     if str(p.get("name", "")).startswith("comfy-film")]
        except Exception as e:
            return self._error(f"Film made, but saving to Open WebUI failed: {type(e).__name__}: {e}")
        await self._status(emitter, f"{label}: {round(total, 1)}s film in {round(took / 60, 1)} min", done=True)
        checks = {i: s.get("qa") for i, s in enumerate(project["shots"], start=1)
                  if s.get("qa") and str(s.get("qa")).startswith("unresolved")}
        status = {"status": "success", "minutes_taken": round(took / 60, 1), "film_seconds": round(total, 1),
                  "film_number": len(films), "shots": report, "keyframe_checks": checks or "all passed",
                  "message": "The finished film (with soundtrack) and the keyframes are already visible to the user. "
                             "Do not repeat links; briefly describe the film shot by shot (shot numbers), and mention "
                             "that any single shot can be changed with redo_shot. keyframe_checks is information for the "
                             "user only: mention any unresolved item in one line, but do NOT call redo_shot or any other "
                             "tool unless the user asks for it in their next message."}
        return HTMLResponse(content=self._media_embed("video", movie, "video/mp4", True),
                            headers={"Content-Disposition": "inline"}), json.dumps(status)

    async def _store_hidden(self, data: bytes, content_type: str, name: str, request, user) -> str:
        """Save bytes as an Open WebUI file without attaching it to the chat (used for film project parts)."""
        from fastapi import UploadFile
        from open_webui.models.users import UserModel
        from open_webui.routers.files import upload_file_handler

        upload = UploadFile(file=io.BytesIO(data), filename=name, headers={"content-type": content_type})
        item = await upload_file_handler(request, file=upload, metadata={}, process=False, user=UserModel(**user))
        return item.id

    # --------------------------------------------------------------- film helpers

    def _t2i_wf(self, prompt: str, w: int, h: int) -> dict:
        wf = self._template("z_image_turbo")
        wf[_IMG["prompt"]]["inputs"]["text"] = prompt
        wf[_IMG["latent"]]["inputs"]["width"] = w
        wf[_IMG["latent"]]["inputs"]["height"] = h
        wf[_IMG["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        return wf

    def _edit_wf(self, base_uploaded: str, instruction: str, refs: list = None) -> dict:
        """Qwen edit with Picture 1 = base and up to 2 extra reference images (Picture 2/3)."""
        wf = self._template("qwen_image_edit")
        wf[_EDIT["image"]]["inputs"]["image"] = base_uploaded
        wf[_EDIT["prompt"]]["inputs"]["value"] = instruction
        wf[_EDIT["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        for n, up in enumerate((refs or [])[:2], start=2):
            wf[f"ref{n}"] = {"class_type": "LoadImage", "inputs": {"image": up}}
            for enc in _EDIT["encoders"]:
                wf[enc]["inputs"][f"image{n}"] = [f"ref{n}", 0]
        return wf

    def _i2v_wf(self, uploaded: str, prompt: str, w: int, h: int, secs: int) -> dict:
        wf = self._template("wan22_i2v")
        wf[_I2V["image"]]["inputs"]["image"] = uploaded
        wf[_I2V["prompt"]]["inputs"]["text"] = prompt
        wf[_I2V["latent"]]["inputs"]["width"] = w
        wf[_I2V["latent"]]["inputs"]["height"] = h
        wf[_I2V["latent"]]["inputs"]["length"] = 4 * max(1, round(secs * 16 / 4)) + 1  # Wan wants 4k+1 frames @16fps
        wf[_I2V["lora"]]["inputs"]["value"] = True
        wf[_I2V["sampler"]]["inputs"]["noise_seed"] = random.randint(0, 2**32 - 1)
        return wf

    async def _assemble(self, clips: list, mode: str, audio, music_style: str, lyrics: str, label: str, emitter,
                        crossfade: float = 0.0) -> tuple:
        """Concatenate clip bytes; soundtrack mode clips/song/new/none. Returns (mp4 bytes, seconds, soundtrack bytes or None)."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for k, data in enumerate(clips):
                p = os.path.join(tmp, f"in{k}.mp4"); open(p, "wb").write(data); paths.append(p)
            w, h = await self._probe_size(paths[0])
            infos = [await self._stream_info(c) for c in paths]
            uniform = len({(i["w"], i["h"], i["fps"], i["codec"], i["audio"]) for i in infos}) == 1
            parts = []
            if uniform:  # clips from the same pipeline: join without re-encoding (fast, a few MB of memory)
                parts = paths
            for k, c in enumerate([] if uniform else paths):  # mixed clips: same size/fps, every clip gets an audio track
                out = os.path.join(tmp, f"norm{k}.mp4")
                has_audio = await self._has_audio(c)
                cmd = ["ffmpeg", "-y", "-v", "error", "-i", c]
                if not has_audio:
                    cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
                cmd += ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps=16,format=yuv420p",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-threads", "2",
                        "-c:a", "aac", "-ar", "44100", "-ac", "2"]
                if not has_audio:
                    cmd += ["-shortest"]
                await self._ffmpeg(cmd + [out])
                parts.append(out)
            listing = os.path.join(tmp, "list.txt")
            open(listing, "w").write("".join(f"file '{p}'\n" for p in parts))
            joined = os.path.join(tmp, "joined.mp4")
            if crossfade > 0 and len(parts) > 1:  # dissolve between shots (re-encode, video only; music is added below)
                durs = [await self._duration(p) for p in parts]
                ins, chain, prev, acc = [], [], "[0:v]", 0.0
                for k, p in enumerate(parts):
                    ins += ["-i", p]
                for k in range(1, len(parts)):
                    acc += durs[k - 1] - crossfade
                    out = f"[x{k}]" if k < len(parts) - 1 else "[vout]"
                    chain.append(f"{prev}[{k}:v]xfade=transition=fade:duration={crossfade}:offset={acc:.3f}{out}")
                    prev = out
                await self._ffmpeg(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(chain), "-map", "[vout]",
                                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-threads", "2",
                                    "-pix_fmt", "yuv420p", "-an", joined])
                if mode == "clips":
                    mode = "none"  # per-clip audio can't follow a dissolve; use song/new for sound
            else:
                await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", joined])
            total = await self._duration(joined)
            final = joined
            if mode == "none":
                final = os.path.join(tmp, "final.mp4")
                await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-i", joined, "-an", "-c:v", "copy", final])
            elif mode in ("song", "new"):
                if mode == "new":
                    await self._status(emitter, f"{label}: composing a {round(total)}s soundtrack")
                    awf = self._template("ace_step_t2a")
                    awf[_T2A["encode"]]["inputs"]["tags"] = music_style
                    awf[_T2A["encode"]]["inputs"]["lyrics"] = (lyrics or "").strip() or "[inst]"
                    awf[_T2A["latent"]]["inputs"]["seconds"] = max(5, int(total + 1))
                    awf[_T2A["sampler"]]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
                    audio = await self._comfy(awf, _T2A["save"], self.valves.AUDIO_TIMEOUT, f"{label}: soundtrack", emitter)
                apath = os.path.join(tmp, "music.mp3"); open(apath, "wb").write(audio)
                final = os.path.join(tmp, "final.mp4")
                await self._ffmpeg(["ffmpeg", "-y", "-v", "error", "-i", joined, "-i", apath, "-map", "0:v", "-map", "1:a",
                                    "-c:v", "copy", "-af", f"afade=t=out:st={max(0.0, total - 1.5):.2f}:d=1.5", "-c:a", "aac",
                                    "-t", f"{total:.3f}", final])
            return open(final, "rb").read(), total, audio

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

    async def _stream_info(self, path: str) -> dict:
        out = await self._ffmpeg(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height,r_frame_rate,codec_name", "-of", "json", path])
        v = (json.loads(out).get("streams") or [{}])[0]
        return {"w": v.get("width"), "h": v.get("height"), "fps": v.get("r_frame_rate"),
                "codec": v.get("codec_name"), "audio": await self._has_audio(path)}

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
        ext = {"image/png": ".png", "video/mp4": ".mp4", "audio/mpeg": ".mp3", "application/json": ".json"}.get(content_type, "")
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
