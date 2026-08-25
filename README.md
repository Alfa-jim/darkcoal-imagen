# darkcoal-imagen-v2 — Your cheap picture maker (works with RunPod)

> **In one sentence:** This lets your app create anime and realistic pictures (including adult/NSFW, no filter) for about **$1.35 per month** instead of $50+. When no one is making pictures, you pay **$0**.

**Who is this for?** You, even if you have never coded before. You just drag files.

---

## The big picture (like ordering food)

*   **You (your app)** = the customer who says "I want a picture of a girl in a bedroom"
*   **RunPod** = the kitchen you rent. You only pay for the time the chef is cooking. If no one orders, you pay nothing. This is called "Taxi mode".
*   **This folder (darkcoal-imagen-v2)** = the recipe. It tells the chef how to draw.

**Cost example:** Making one tall phone picture takes about 2 seconds. That costs less than 1/10 of a cent ($0.0005). If 5 people make 50 pictures a day, that's about $1.35 for a whole month. Your $10 lasts 6-7 months.

---

## Why the old version always showed "Unhealthy" or "Failed"

Think of it like moving:

1.  **It was way too heavy (12 GB).** Imagine trying to send a whole house through email. It took 40 minutes to download and RunPod gave up. **Fix:** The new version is small (2-3 GB), downloads in 1 minute.
2.  **The "ON" button was hidden.** RunPod looks for a big green ON button to start. The old code hid it inside a closed box. So RunPod thought it was broken. **Fix:** The new ON button is right on top where RunPod can easily find it.
3.  **It forgot everything.** Every time it woke up, it had to re-download the brain (6.9 GB). **Fix:** Now it can save the brain on a USB stick (called a Network Volume) so the next time it's instant.

The new version fixes all 3. It also handles anime + realistic photos + keeping the same character if you give it a reference photo.

---

## Setup — Just 5 steps, drag and drop (no coding needed)

Do this once. You don't need to install Docker or anything.

### Step 1 - Create a box on GitHub (free)
1. Go to https://github.com/new
2. Name it: `darkcoal-imagen`
3. Make sure it says **Public** (important!)
4. Click **Create repository**

### Step 2 - Put the files in the box
1. On the new page click the blue text **"uploading an existing file"**
2. Open this folder on your computer: `darkcoal-imagen-v2`
3. Select **EVERYTHING** inside it (handler.py, Dockerfile, requirements.txt, .dockerignore, and the .github folder) and DRAG it into the GitHub website
4. Click **Commit changes** (green button)

### Step 3 - Wait for GitHub to build it (like baking)
1. Click the **Actions** tab at the top
2. You'll see a yellow dot spinning. Wait 8-12 minutes. You can close your laptop.
3. When it turns to a **green checkmark ✓**, it's ready.

### Step 4 - Make it visible (if you skip this, RunPod will say "Image not found")
1. Click your profile picture (top right) -> **Your profile** -> tab **Packages**
2. Click `darkcoal-imagen` -> on the right click **Package settings**
3. Scroll down -> **Change visibility** -> **Make public**

### Step 5 - Tell RunPod to use it
1. Go to https://console.runpod.io/serverless -> **New Endpoint**
2. Fill in:
   *   **Container Image:** `ghcr.io/YOUR_GITHUB_NAME/darkcoal-imagen:latest` (your GitHub name must be small letters!)
   *   **Container Disk:** 20 GB
   *   **Volume:** Click **Create Volume** -> 20 GB -> path is `/runpod-volume` . This is the "USB stick" that makes it fast next time. Costs about $2/month. You can skip it, but then every first picture after sleep will be 30 seconds slower. Recommended to add it.
   *   **GPU:** Choose **Flex** -> drag **RTX 4090** to the top, **L4** second. These are the cheapest. Don't pick A100 or H100, they are expensive.
   *   **Workers:** Min **0** (so you pay $0 when sleeping), Max **5**, Idle Timeout **5s**, Execution Timeout **60s**
3. Click Create. Copy the long ID from the browser address bar — that's your Endpoint ID.

**Done!**

---

## How to test if it works

The very first picture after it slept will take 30-40 seconds (it has to download the brain the first time). The next ones take only 2-3 seconds. This is normal!

### Easy test on Windows (copy/paste)

You need your Endpoint ID and an API key from https://console.runpod.io/user/settings -> API Keys (starts with `rpa_...`)

Open PowerShell and paste this (replace the two lines at the top):

```powershell
$ENDPOINT="your-endpoint-id-here"
$KEY="rpa_your_key_here"

$body=@{ input=@{ style="illustrious"; prompt="a 25 year old adult woman, smiling in a softly lit bedroom, masterpiece"; width=1088; height=1920; steps=20; guidance=6 } } | ConvertTo-Json -Depth 6
$job = Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT/run" -Method Post -Headers @{Authorization="Bearer $KEY"; "Content-Type"="application/json"} -Body $body
$id = $job.id; do { Start-Sleep 2; $st = Invoke-RestMethod -Uri "https://api.runpod.ai/v2/$ENDPOINT/status/$id" -Headers @{Authorization="Bearer $KEY"}; Write-Host $st.status; if($st.status -eq "COMPLETED"){ $b64=$st.output.images[0].b64; $bytes=[Convert]::FromBase64String($b64.Split(",")[1]); Set-Content -Path ".\test_out.jpg" -Value $bytes -AsByteStream; Invoke-Item ".\test_out.jpg"; break } if($st.status -eq "FAILED"){ $st|ConvertTo-Json -Depth 6; break } } while($true)
```

If you get a `test_out.jpg` file opening, it works!

### If it says "Unhealthy" or "Failed" — Don't worry, check this:

Go to your RunPod endpoint -> **Logs** -> **Container logs** (NOT System logs) and look at the last lines.

*   Says `Image not found` -> You forgot Step 4 (Make public).
*   Says `CUDA not available` -> You picked the wrong GPU, pick 4090/L4 Flex.
*   Says `401 or 403` -> Add an env variable `HF_TOKEN` on RunPod (but Illustrious is public so you usually don't need it).
*   First run times out -> Use the `/run` + `/status` way above instead of `/runsync`, or make Execution Timeout 120s just for the first test.

Copy the last 20 lines of Container logs to me if you get stuck and I will tell you the fix.

---

## How to use it in your app

Your app sends a message like this:

**To make a new picture:**
Send: `{"style":"illustrious", "prompt":"your description here", "width":1088, "height":1920, "steps":20, "guidance":6}`
*   `style`: `illustrious` (best for anime, understands normal English + tags), `pony`, `noobai`, `realistic` (for real photos)
*   `prompt`: What you want to see, e.g. `"a cute anime girl with long pink hair in a bedroom, soft light"` or `"1girl, blush, long hair"`
*   `width`/`height`: Size. 1088x1920 is a tall phone screen. Keep between 512 and 2048.

**To keep the same character (like same face, new clothes):**
Add: `"image_urls":["https://link-to-your-reference-photo.jpg"], "denoising_strength": 0.62`
Think of `denoising_strength` as "how much to change": 0.55 = keep face very same, 0.70 = change more.

**Answer you get back:**
`{"images":[{"b64":"data:image/jpeg;base64,..."}], "seed":12345, "timings":{...}}` — the `b64` is the picture. You can show it directly in a browser.

---

## Simple cost table

| What you do | Cost |
|---|---|
| No pictures for a whole month | **$0** |
| 1 picture (tall phone, good quality) | **~$0.0005** (less than a penny) |
| 50 pictures per day for 30 days | **~$1.35** |
| $10 in your RunPod balance | Lasts **6-7 months** at that rate |

---

## Important rules

This system has no filter on purpose so you have creative freedom. But **you are responsible**:
*   Only make pictures of consenting adults (18+). Never use it for minors.
*   Never use real people's faces without their permission.
*   Follow your country's laws.

---

## Files in this folder

*   `handler.py` — The recipe (you don't need to touch it)
*   `Dockerfile` — Tells GitHub how to pack the recipe into a small box
*   `requirements.txt` — List of ingredients
*   `.github/workflows/build.yml` — Tells GitHub to build automatically when you upload
*   `START_HERE_EASY.md` — Another super simple copy of this guide
*   `README.md` — This file you are reading

Need help? Just send me the Container logs.
