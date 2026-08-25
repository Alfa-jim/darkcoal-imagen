# Fix: permission_denied: write_package

This is NOT a code error. It's a GitHub setting.

## Fix in 30 seconds:

1. Go to https://github.com/Alfa-jim/darkcoal-imagen
2. Click **Settings** (top tab, far right)
3. Left sidebar -> **Actions** -> **General**
4. Scroll to very bottom -> **Workflow permissions**
5. Change from "Read" to:
   **(o) Read and write permissions**
6. Check "Allow GitHub Actions to create and approve pull requests"
7. Click **Save**

Then:

8. Go to **Actions** tab -> click the red failed run -> **Re-run all jobs**

It will turn green ✓.

---
If you still get denied after saving, do this extra step:

GitHub.com -> Your Profile picture -> **Settings** -> **Packages** -> make sure nothing is set to private.

