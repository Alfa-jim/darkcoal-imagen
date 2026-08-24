# darkcoal-imagen — RunPod Serverless (uncensored, anime+general+refs, ~$0.0009/img)

> For your scale (100 DAU, ~5 people generating): ~50 imgs/day → ~$1.35/month. Idle = **$0**.

## Quick start (GitHub free build, no Docker on laptop)

**1. Create GitHub repo:** https://github.com/new → name `darkcoal-imagen` → **Public** → Create (don't add README).

**2. Upload:** On the new repo page click "uploading an existing file" → drag EVERYTHING from `C:\Users\dutap\OneDrive\Desktop\DSH workspace\darkcoal-imagen` (handler.py, Dockerfile, requirements.txt, .dockerignore, and the `.github` folder) → Commit.

**3. Wait for build:** Go to **Actions** tab → "Build and Push to GHCR" → yellow → wait 8-12 min → green ✓. That's GitHub building the Docker image for free on their server — your laptop can be closed.

**4. Make package public:** After green, GitHub → your profile → Packages → `darkcoal-imagen` → Package settings → Change visibility → Public. (If you skip, RunPod says Image not found.)

**5. RunPod endpoint:** https://console.runpod.io/serverless → New Endpoint
   * Container Image: `ghcr.io/YOUR_GITHUB_USERNAME/darkcoal-imagen:latest` (lowercase username!)
   * Disk: 20 GB, Volume: None
   * GPU: Flex → RTX 4090 first, L4 second (cheapest per image — $0.00088 @1080p)
   * Workers: Min 0 (you pay $0 when idle), Max 5, Idle 5s, Timeout 60s
   * Copy ENDPOINT_ID from the URL

## Test (PowerShell)

Get API key: https://console.runpod.io/user/settings → API Keys → `rpa_...`

```powershell
$ENDPOINT="YOUR_ENDPOINT_ID"
$KEY="rpa_XXXXXXXXXXXXXXXX"
$body=@{ input=@{ style="illustrious"; prompt="a 25-year-old consenting adult woman, nude, standing in softly lit bedroom, masterpiece"; width=1088; height=1920; steps=20; guidance=6 } } | ConvertTo-Json -Depth 6
$job = Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT/run" -Method Post -Headers @{Authorization="Bearer $KEY"; "Content-Type"="application/json"} -Body $body
$id = $job.id; do { Start-Sleep 2; $st = Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT/status/$id" -Headers @{Authorization="Bearer $KEY"}; Write-Host $st.status; if($st.status -eq "COMPLETED"){ $b64=$st.output.images[0].b64; $bytes=[Convert]::FromBase64String($b64.Split(",")[1]); Set-Content -Path ".\test_out.jpg" -Value $bytes -AsByteStream; Invoke-Item ".\test_out.jpg"; break } if($st.status -eq "FAILED"){ $st|ConvertTo-Json -Depth 5; break } } while($true)
```

With ref: `{"input":{"style":"illustrious","prompt":"same woman as reference, nude...","image_urls":["https://..."],"denoising_strength":0.62}}`

## Model & GPU

* **Model:** OnomaAIResearch/Illustrious-XL-v2.0 (default, handles casual language + Danbooru tags). Switch with `style`: `pony` (tag-heavy), `noobai`, `realistic`.
* **GPU:** RTX 4090 = $0.00044/s, ~2.0s @1088×1920 → $0.00088/image. L4 is fallback. A100/H100 are faster but 1.5-2× more expensive per image.

## Updates

Just push to GitHub `main` — Actions rebuilds and RunPod pulls `:latest` on next cold start (or click Update in RunPod).

## Local Docker (optional)

```powershell
cd "C:\Users\dutap\OneDrive\Desktop\DSH workspace\darkcoal-imagen"
docker buildx build --platform linux/amd64 -t ghcr.io/YOUR_USER/darkcoal-imagen:latest . --push
```
