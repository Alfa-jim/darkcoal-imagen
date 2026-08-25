# START HERE - Super Simple Guide (No coding needed!)

Hi! This guide explains everything in plain English.

### What is this thing?

Think of it like renting a powerful computer to make pictures.

*   **Your app** asks for a picture: "a girl in a bedroom"
*   **Our system** draws it for you (anime or realistic, whatever you want)
*   **You only pay when it's drawing.** When no one is asking for pictures, you pay $0. That's why it's so cheap.

Making 50 pictures a day costs about **$1.35 for a whole month.** If you used other companies, it would be $50-$100.

---

### Why did the old version keep failing?

Imagine you tried to move a house with a tiny truck.

1.  **Old version was too big (12GB).** It was like trying to fit an entire house in the truck. RunPod (the company renting the computer) got tired of waiting and said "FAILED".
2.  **It was hidden.** RunPod looks for a "start button" to know how to turn it on. The old code hid that button inside a box, so RunPod could never find it and thought it was broken.

**New version (v2) fixes both:**
*   Now it's small (2-3GB) - fits easily in the truck, starts in 1 minute not 40 minutes.
*   The "start button" is right on top where RunPod can easily see it.
*   It also remembers the drawing model so it doesn't have to download it every single time.

---

### How to set it up (You just need to drag and drop files)

You do NOT need to install anything on your laptop. GitHub will build it for you for free.

**STEP 1: Create a place to store it**

1. Go to https://github.com/new
2. For "Repository name" type: `darkcoal-imagen`
3. Make sure it says **Public** (very important!)
4. Click the big green button **"Create repository"**

**STEP 2: Upload the files**

1. On the new page, you will see a blue link that says **"uploading an existing file"** - click it.
2. Open the folder on your computer: `darkcoal-imagen-v2`
3. Select EVERYTHING in that folder (handler.py, Dockerfile, etc. and the .github folder) and DRAG them into the website.
4. Click **"Commit changes"**

**STEP 3: Wait for it to build (like waiting for bread to bake)**

1. Click the **"Actions"** tab at the top of your GitHub page.
2. You will see a yellow dot spinning. Wait 8-12 minutes. You can close your laptop.
3. When it turns into a **green checkmark ✓**, it's done!

**STEP 4: Make it public so RunPod can see it (If you skip this, RunPod will say "Image not found")**

1. Click your profile picture (top right) -> **Your profile** -> **Packages** tab
2. Find `darkcoal-imagen` and click it
3. On the right side click **"Package settings"**
4. Scroll to the bottom and click **"Change visibility"** -> **"Make public"**

**STEP 5: Tell RunPod to use it**

1. Go to https://console.runpod.io/serverless -> Click **"New Endpoint"**
2. Fill it like this:
    *   **Container Image:** `ghcr.io/YOUR_GITHUB_NAME/darkcoal-imagen:latest` (IMPORTANT: your GitHub name must be all small letters!)
    *   **Container Disk:** 20 GB
    *   **Volume:** Click "Create Volume" -> make it 20 GB -> set the path to `/runpod-volume` (This is like a USB stick so it remembers the model and next pictures are fast. It costs ~$2/month extra but makes it 10x faster. You can skip it, but first picture will always be slow.)
    *   **GPU:** Choose **Flex** -> Put **RTX 4090** at the top, **L4** as second choice. These are the cheapest. Don't pick A100, it's expensive.
    *   **Workers:** Min 0, Max 5, Idle Timeout 5s, Execution Timeout 60s
3. Click Create. Copy the long ID from the website address bar - that's your Endpoint ID.

That's it! You are done.

---

### How to test if it works

The first picture after a long sleep will take 30-40 seconds because it has to download the brain (the 6.9GB Illustrious model). The next pictures will take only 2-3 seconds. This is normal!

If it says "Unhealthy", don't panic:
*   Go to your RunPod endpoint -> Click **"Logs"** -> Click **"Container logs"** (NOT System logs)
*   If it says "Image not found" -> you forgot STEP 4 (make it public)
*   If it says "CUDA not available" -> you picked the wrong GPU, pick 4090/L4

### How much will it cost?

*   When no one is making pictures: **$0**
*   Making one tall phone picture (1088x1920): **less than $0.001** (a tenth of a cent)
*   50 pictures a day for a month: **~$1.35**
*   Your $10 will last 6-7 months easily.

### What kind of pictures can it make?

*   **Anime:** It is amazing at anime. You can talk normally: "a cute girl with pink hair smiling in her bedroom, soft light" or use tags: "1girl, blush, long hair"
*   **Realistic / Photoreal:** Change `style` to `realistic` and it looks like a real photo.
*   **Keep the same character:** Send a reference picture `image_urls` and tell it "same woman as reference, but now wearing a red dress" and it will keep the same face. Use `denoising_strength` around 0.62 (0.55 locks face more, 0.70 changes more).

**Important:** This system has no censorship filter on purpose, but you must only create pictures of consenting adults. Never use it for minors or real people without permission. You are responsible for how you use it.

---

### Need help?

If it fails, just look at the Container Logs on RunPod and copy the last 20 lines to me. I can tell you exactly what went wrong.

You don't need to understand the code. Just follow the 5 steps above!
