"""
RunPod Serverless — darkcoal-imagen
"""
import os, io, base64, time, requests, traceback
from PIL import Image

_PIPE_CACHE: dict = {}
REGISTRY = {
    "illustrious": "OnomaAIResearch/Illustrious-XL-v2.0",
    "pony": "AstraliteHeart/pony-diffusion-v6-xl",
    "noobai": "Laxhar/NoobAI-XL-Vpred-1.0",
    "realistic": "stabilityai/stable-diffusion-xl-base-1.0",
}

def _load_pipe(style: str):
    if style in _PIPE_CACHE:
        return _PIPE_CACHE[style]
    import torch
    from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler, EulerAncestralDiscreteScheduler
    repo = REGISTRY[style]
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    kwargs = dict(torch_dtype=torch.float16, use_safetensors=True)
    if hf_token:
        kwargs["token"] = hf_token
    tried = []
    pipe = None
    for variant in ("fp16", None):
        try:
            kw = dict(kwargs)
            if variant:
                kw["variant"] = variant
            if style == "noobai":
                p = StableDiffusionXLPipeline.from_pretrained(repo, **kw)
                p.scheduler = EulerDiscreteScheduler.from_config(p.scheduler.config, prediction_type="v_prediction", rescale_betas_zero_snr=True)
            else:
                p = StableDiffusionXLPipeline.from_pretrained(repo, **kw)
                p.scheduler = EulerAncestralDiscreteScheduler.from_config(p.scheduler.config)
            pipe = p
            break
        except Exception as e:
            tried.append(f"{variant}: {e}")
            continue
    if pipe is None:
        raise RuntimeError(f"Failed to load {repo}: {tried}")
    pipe = pipe.to("cuda")
    try: pipe.enable_xformers_memory_efficient_attention()
    except Exception: pass
    try: pipe.enable_vae_tiling()
    except Exception: pass
    _PIPE_CACHE[style] = pipe
    print(f"[load] {style} <- {repo}", flush=True)
    return pipe

def _fetch_image(url: str) -> Image.Image:
    if url.startswith("data:"):
        _, b64 = url.split(",", 1)
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    r = requests.get(url, timeout=40, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def _pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

def handler(job):
    t0 = time.time()
    inp = job.get("input", {}) if isinstance(job, dict) else {}
    style = inp.get("style") or "illustrious"
    if style not in REGISTRY:
        style = "illustrious"
    prompt = inp.get("prompt") or ""
    if not prompt:
        return {"error": "prompt is required"}
    negative_prompt = inp.get("negative_prompt") or ""
    width = int(inp.get("width") or inp.get("w") or 1088)
    height = int(inp.get("height") or inp.get("h") or 1920)
    steps = int(inp.get("steps") or 20)
    guidance = float(inp.get("guidance") or 6.0)
    seed = inp.get("seed")
    num_images = max(1, min(4, int(inp.get("num_images") or inp.get("n") or 1)))
    image_urls = inp.get("image_urls") or (inp.get("image_url") and [inp.get("image_url")]) or None
    denoising_strength = float(inp.get("denoising_strength") or 0.62)
    width = (width // 8) * 8; height = (height // 8) * 8
    lora_urls = inp.get("lora_urls")
    lora_scales = inp.get("lora_scales")
    import torch
    pipe = _load_pipe(style)
    loaded = []
    _LORA_CACHE = {}
    if lora_urls:
        if isinstance(lora_urls, str): lora_urls = [lora_urls]
        scales = lora_scales or [0.9]*len(lora_urls)
        for url, sc in zip(lora_urls, scales):
            print(f"[lora] {url}", flush=True)
            try:
                pipe.load_lora_weights(url, adapter_name=url[:40])
                _LORA_CACHE[url] = url[:40]
            except Exception as e:
                r = requests.get(url, timeout=80); r.raise_for_status()
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".safetensors", delete=False) as tf:
                    tf.write(r.content); tmp=tf.name
                pipe.load_lora_weights(os.path.dirname(tmp), weight_name=os.path.basename(tmp), adapter_name=url[:40])
                try: os.remove(tmp)
                except: pass
                _LORA_CACHE[url] = url[:40]
            try: pipe.set_adapters([_LORA_CACHE[url]], adapter_weights=[float(sc)])
            except: pass
            loaded.append(url)
    seed_val = int(seed) if seed is not None else int(torch.randint(0, 2**31-1, (1,)).item())
    gen = torch.Generator("cuda").manual_seed(seed_val)
    is_img2img = bool(image_urls)
    ref = None
    if is_img2img:
        if isinstance(image_urls, str): image_urls = [image_urls]
        ref = _fetch_image(image_urls[0]).resize((width, height), Image.LANCZOS)
    try:
        if is_img2img:
            from diffusers import StableDiffusionXLImg2ImgPipeline
            try: img_pipe = StableDiffusionXLImg2ImgPipeline.from_pipe(pipe)
            except: img_pipe = pipe
            images = img_pipe(prompt=prompt, negative_prompt=negative_prompt or None, image=ref, strength=float(denoising_strength), num_inference_steps=steps, guidance_scale=guidance, generator=gen, num_images_per_prompt=num_images).images
        else:
            images = pipe(prompt=prompt, negative_prompt=negative_prompt or None, width=width, height=height, num_inference_steps=steps, guidance_scale=guidance, generator=gen, num_images_per_prompt=num_images).images
    except Exception as e:
        traceback.print_exc()
        return {"error": f"inference failed: {e}"}
    finally:
        if loaded:
            try: pipe.unload_lora_weights()
            except: pass
    out = []
    for im in images:
        out.append({"b64": _pil_to_b64(im), "width": width, "height": height, "content_type": "image/jpeg"})
    dt = time.time() - t0
    return {"images": out, "seed": seed_val, "timings": {"inference": round(dt,3), "steps": steps, "width": width, "height": height}, "style": style, "model_repo": REGISTRY[style]}

# --- RunPod bootstrap (must be at top-level so RunPod's scanner finds it) ---
import runpod
print("[boot] handler ready - starting runpod.serverless", flush=True)
runpod.serverless.start({"handler": handler})
