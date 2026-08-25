"""
darkcoal-imagen-v2 — RunPod Serverless
Uncensored anime + general NSFW image generation — cheapest self-hosted at ~$0.0005/img @ 1080p.

Models: illustrious (default, natural language + Danbooru), pony, noobai, realistic
Pipeline: SDXL txt2img + img2img (character lock via image_urls[0] + denoising_strength)
API:    POST {"input": {style, prompt, negative_prompt, width, height, steps, guidance, seed, image_urls, denoising_strength, lora_urls, lora_scales, num_images}}
Output: {"images": [{"b64": "data:image/jpeg;base64,..."}], "seed": int, "timings": {...}, "style": ..., "model_repo": ...}

Uncensored: no safety checker (SDXL has none; we don't add one).

RunPod bootstrap is at top-level (NOT inside if __name__) so scanner finds it.
Heavy deps (torch/diffusers) are lazy — imported only inside handler, so import never crashes cold container.
"""
import os
import io
import base64
import time
import traceback
from typing import Optional

import requests
from PIL import Image

# ---------------- Config ----------------
# Persist HF cache on RunPod Network Volume when attached (HF_HOME=/runpod-volume).
# If no volume is attached /runpod-volume is just a local dir — still works, just re-downloads each cold start.
HF_HOME = os.environ.get("HF_HOME", "/runpod-volume")
os.environ.setdefault("HF_HOME", HF_HOME)
os.environ.setdefault("HF_HUB_CACHE", HF_HOME)
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("DIFFUSERS_VERBOSITY", "error")

REGISTRY = {
    "illustrious": "OnomaAIResearch/Illustrious-XL-v2.0",   # 6.9 GB — natural language + Danbooru (default)
    "pony":        "AstraliteHeart/pony-diffusion-v6-xl",   # tag-heavy anime
    "noobai":      "Laxhar/NoobAI-XL-Vpred-1.0",            # v-prediction, strong anime
    "realistic":   "stabilityai/stable-diffusion-xl-base-1.0",  # photoreal / general
}

_PIPE_CACHE: dict = {}
_LORA_CACHE: dict = {}  # url -> adapter_name


def _get_pipe(style: str):
    """Lazy-load and cache SDXL pipeline per style. Called inside handler so import failures don't kill container."""
    if style in _PIPE_CACHE:
        return _PIPE_CACHE[style]

    # Lazy imports — container stays healthy even if these fail to import at module load
    import torch
    from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler, EulerAncestralDiscreteScheduler

    repo = REGISTRY[style]
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None

    # Prefer fp16 variant (half disk/bandwidth), fall back to full
    base_kwargs = dict(torch_dtype=torch.float16, use_safetensors=True)
    if hf_token:
        base_kwargs["token"] = hf_token

    last_err = None
    pipe = None
    for variant in ("fp16", None):
        try:
            kw = dict(base_kwargs)
            if variant:
                kw["variant"] = variant
            # from_pretrained downloads to HF_HOME on first cold start; cached on volume afterward
            if style == "noobai":
                # NoobAI is v-prediction — must override scheduler
                p = StableDiffusionXLPipeline.from_pretrained(repo, **kw)
                p.scheduler = EulerDiscreteScheduler.from_config(
                    p.scheduler.config, prediction_type="v_prediction", rescale_betas_zero_snr=True
                )
            else:
                p = StableDiffusionXLPipeline.from_pretrained(repo, **kw)
                p.scheduler = EulerAncestralDiscreteScheduler.from_config(p.scheduler.config)
            pipe = p
            print(f"[load] {style} <- {repo} variant={variant or 'full'}", flush=True)
            break
        except Exception as e:
            last_err = e
            print(f"[load] {style} variant={variant or 'full'} failed: {e}", flush=True)
            continue

    if pipe is None:
        raise RuntimeError(f"Failed to load {repo}: {last_err}")

    # Move to GPU — RunPod serverless always has CUDA; if not, we return error instead of crashing container
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available on this worker — need GPU (Flex 24GB)")

    pipe = pipe.to("cuda")

    # VRAM optimizations — all optional, best-effort
    # xformers not in requirements (avoids build hell); if installed elsewhere it will be used
    try:
        pipe.enable_xformers_memory_efficient_attention()
        print("[opt] xformers enabled", flush=True)
    except Exception as e:
        print(f"[opt] xformers not available: {e}", flush=True)
    try:
        # Tiling keeps 1088x1920 VAE decode from OOMing on 24GB (peak ~14GB with tiling vs ~18GB without)
        pipe.enable_vae_tiling()
        print("[opt] vae_tiling enabled", flush=True)
    except Exception:
        pass
    try:
        pipe.enable_vae_slicing()
    except Exception:
        pass

    _PIPE_CACHE[style] = pipe
    return pipe


def _fetch_image(url: str) -> Image.Image:
    """Fetch reference image for img2img character lock. Supports http(s) and data: URIs."""
    if not url or not url.strip():
        raise ValueError("empty image URL")
    url = url.strip()
    if url.startswith("data:"):
        # data:image/jpeg;base64,...
        try:
            _, b64 = url.split(",", 1)
        except ValueError:
            raise ValueError("invalid data URI")
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _pil_to_b64(img: Image.Image, quality: int = 90) -> str:
    buf = io.BytesIO()
    # JPEG is ~3x smaller than PNG for photos/anime, fits RunPod 10MB output limit easily
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"


# ---------------- Handler ----------------

def handler(job: dict):
    """
    RunPod job: {"id": "...", "input": {...}}
    Returns dict serialized as `output` in RunPod response.
    Never raises — always returns dict (RunPod marks uncaught raises as FAILED).
    """
    t0 = time.time()
    try:
        inp = job.get("input", {}) if isinstance(job, dict) else {}
        style = (inp.get("style") or "illustrious").strip().lower()
        if style not in REGISTRY:
            style = "illustrious"

        prompt: str = (inp.get("prompt") or "").strip()
        if not prompt:
            return {"error": "prompt is required (non-empty string)"}

        negative_prompt: str = inp.get("negative_prompt") or ""
        width: int = int(inp.get("width") or inp.get("w") or 1088)
        height: int = int(inp.get("height") or inp.get("h") or 1920)
        steps: int = int(inp.get("steps") or 20)
        guidance: float = float(inp.get("guidance") or inp.get("guidance_scale") or 6.0)
        seed = inp.get("seed")
        num_images: int = int(inp.get("num_images") or inp.get("n") or 1)
        image_urls = inp.get("image_urls") or (inp.get("image_url") and [inp.get("image_url")]) or None
        denoising_strength: float = float(inp.get("denoising_strength") or inp.get("strength") or 0.62)
        lora_urls = inp.get("lora_urls")
        lora_scales = inp.get("lora_scales")

        # Clamp & align to 8 (SDXL latent is 8x)
        width = max(512, min(2048, (width // 8) * 8))
        height = max(512, min(2048, (height // 8) * 8))
        steps = max(1, min(60, steps))
        guidance = max(0.0, min(20.0, guidance))
        denoising_strength = max(0.05, min(1.0, denoising_strength))
        num_images = max(1, min(4, num_images))

        # Lazy torch import — also validates CUDA before pipe load
        import torch

        pipe = _get_pipe(style)

        # ---- Ephemeral LoRAs (optional) ----
        loaded_adapters = []
        if lora_urls:
            if isinstance(lora_urls, str):
                lora_urls = [lora_urls]
            if isinstance(lora_scales, (int, float, str)):
                lora_scales = [float(lora_scales)]
            scales = lora_scales if isinstance(lora_scales, list) and lora_scales else [0.85] * len(lora_urls)
            # pad scales to urls length
            if len(scales) < len(lora_urls):
                scales = (scales * len(lora_urls))[:len(lora_urls)]
            for url, sc in zip(lora_urls, scales):
                url = url.strip()
                if not url:
                    continue
                adapter = _LORA_CACHE.get(url)
                if adapter is None:
                    adapter = f"lora_{len(_LORA_CACHE)}"
                    print(f"[lora] loading {url} as {adapter} scale={sc}", flush=True)
                    loaded_ok = False
                    # Try direct HF/Lora URL load first (diffusers supports HF repo + weight_name + URL)
                    try:
                        # diffusers can load from HF model id or URL if it's a direct .safetensors
                        pipe.load_lora_weights(url, adapter_name=adapter)
                        loaded_ok = True
                    except Exception as e:
                        print(f"[lora] direct load failed: {e} — downloading", flush=True)
                        try:
                            r = requests.get(url, timeout=80, headers={"User-Agent": "Mozilla/5.0"})
                            r.raise_for_status()
                            import tempfile
                            suffix = ".safetensors" if url.endswith(".safetensors") else ".bin"
                            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
                                tf.write(r.content)
                                tmp = tf.name
                            pipe.load_lora_weights(os.path.dirname(tmp), weight_name=os.path.basename(tmp), adapter_name=adapter)
                            try:
                                os.remove(tmp)
                            except Exception:
                                pass
                            loaded_ok = True
                        except Exception as e2:
                            print(f"[lora] download load failed: {e2}", flush=True)
                            continue
                    if loaded_ok:
                        _LORA_CACHE[url] = adapter
                    else:
                        continue
                try:
                    # set_adapters is diffusers>=0.27 API; fallback to set_lora_scale or do nothing
                    if hasattr(pipe, "set_adapters"):
                        pipe.set_adapters([adapter], adapter_weights=[float(sc)])
                    elif hasattr(pipe, "set_lora_scale"):
                        pipe.set_lora_scale(float(sc))
                except Exception as e:
                    print(f"[lora] set_adapters failed: {e}", flush=True)
                loaded_adapters.append(adapter)

        seed_val = int(seed) if seed is not None and str(seed).strip() != "" else int(torch.randint(0, 2**31 - 1, (1,)).item())
        generator = torch.Generator(device="cuda").manual_seed(seed_val)

        # ---- Reference image (img2img) for character lock ----
        is_img2img = bool(image_urls)
        ref_image: Optional[Image.Image] = None
        if is_img2img:
            if isinstance(image_urls, str):
                image_urls = [image_urls]
            # Only first ref is used (keeps VRAM predictable); extra refs ignored
            try:
                ref_image = _fetch_image(str(image_urls[0])).resize((width, height), Image.LANCZOS)
                print(f"[img2img] ref fetched {ref_image.size} strength={denoising_strength}", flush=True)
            except Exception as e:
                traceback.print_exc()
                return {"error": f"failed to fetch image_urls[0]: {e}"}

        # ---- Inference ----
        try:
            if is_img2img and ref_image is not None:
                # Reuse txt2img weights as img2img to avoid double VRAM (two pipelines would need 12GB+12GB)
                from diffusers import StableDiffusionXLImg2ImgPipeline
                try:
                    img_pipe = StableDiffusionXLImg2ImgPipeline.from_pipe(pipe)
                    # from_pipe copies scheduler etc.; keep xformers/tiling settings
                    try:
                        img_pipe.enable_vae_tiling()
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[img2img] from_pipe failed, falling back to txt2img pipe: {e}", flush=True)
                    img_pipe = pipe  # some diffusers versions accept image kwarg on txt2img

                # Strength: 0.0 = identical to ref, 1.0 = ignore ref. 0.55-0.70 is character-lock sweet spot.
                images = img_pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt or None,
                    image=ref_image,
                    strength=float(denoising_strength),
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
                    num_images_per_prompt=num_images,
                ).images
            else:
                images = pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt or None,
                    width=width,
                    height=height,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
                    num_images_per_prompt=num_images,
                ).images
        except Exception as e:
            traceback.print_exc()
            return {"error": f"inference failed: {e}", "style": style, "model_repo": REGISTRY[style]}

        finally:
            # Unload ephemeral LoRAs so next request without loras is clean
            if loaded_adapters:
                try:
                    pipe.unload_lora_weights()
                    print("[lora] unloaded", flush=True)
                except Exception:
                    pass
                # Clear lora cache entries for adapters we just unloaded? Keep mapping so re-use is faster.
            # Free CUDA cache between jobs — helps when switching styles (different pipe stays cached)
            try:
                import torch as _t
                if _t.cuda.is_available():
                    _t.cuda.empty_cache()
            except Exception:
                pass

        out_images = []
        for im in images:
            b64 = _pil_to_b64(im, quality=90)
            out_images.append({"b64": b64, "width": width, "height": height, "content_type": "image/jpeg"})

        dt = time.time() - t0
        print(f"[done] style={style} {width}x{height} steps={steps} n={num_images} seed={seed_val} t={dt:.2f}s", flush=True)
        return {
            "images": out_images,
            "seed": seed_val,
            "timings": {"inference": round(dt, 3), "steps": steps, "width": width, "height": height},
            "style": style,
            "model_repo": REGISTRY[style],
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": f"handler error: {e}"}


# ---------------- RunPod bootstrap ----------------
# MUST be at top-level (not inside `if __name__ == "__main__":`) — RunPod's scanner
# greps for `runpod.serverless.start` at import time. Guarding it breaks health checks
# and the worker stays "Unhealthy" forever (the #1 fix in this v2).
import runpod  # noqa: E402  (import after handler def is intentional)

print("[boot] handler module loaded — starting runpod.serverless", flush=True)
runpod.serverless.start({"handler": handler})
