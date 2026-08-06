# Complete GitHub Profile Setup Guide for Ayush Singh (`Ayush-840`)

Follow these simple instructions to push this complete handcrafted profile to your personal GitHub repository so it displays live on your profile page: **https://github.com/Ayush-840**.

---

## 📁 Repository Structure Created

```text
Ayush-840/
├── README.md                           ← Handcrafted 14-section flagship profile README
├── VERCEL_SETUP.md                     ← Walkthrough for self-hosting rate-limit-free stats
├── SETUP.md                            ← This deployment guide
├── assets/
│   ├── banner.svg                      ← Terminal hero banner with dithered portrait & HUD
│   ├── portrait_pixel.png              ← Floyd-Steinberg dithered PNG portrait
│   ├── portrait_pixel.svg              ← Floyd-Steinberg dithered SVG portrait grid
│   ├── github-contribution-grid-snake-dark.svg  ← Dark theme snake SVG
│   └── github-contribution-grid-snake.svg       ← Light theme snake SVG
├── scripts/
│   ├── pixel_portrait.py               ← Python Floyd-Steinberg dither generator
│   ├── build_hero_banner.py            ← Python banner SVG builder
│   └── build_snake_svg.py             ← Python initial snake SVG builder
└── .github/
    └── workflows/
        └── snake.yml                   ← GitHub Actions workflow for contribution snake
```

---

## 🚀 How to Publish to GitHub (3 Easy Steps)

### Step 1: Create the Special Profile Repository
If you haven't already:
1. Go to [GitHub New Repository](https://github.com/new).
2. Repository Name: `Ayush-840` *(Must match your GitHub username exactly!)*.
3. Description: `Ayush Singh — Special GitHub Profile Repository`.
4. Visibility: **Public**.
5. Do NOT check "Initialize this repository with a README" (we already have a handcrafted `README.md`).
6. Click **Create repository**.

---

### Step 2: Push Files from Terminal
Open your terminal in this repository folder and run:

```bash
# 1. Initialize git if not already initialized
git init

# 2. Add all profile assets and README
git add .

# 3. Commit changes
git commit -m "feat: publish ultra-premium dark terminal profile README & hero banner"

# 4. Set main branch and remote URL
git branch -M main
git remote add origin https://github.com/Ayush-840/Ayush-840.git

# 5. Push to GitHub
git push -u origin main --force
```

---

### Step 3: Enable GitHub Actions (For Contribution Snake)
1. Go to your repository: `https://github.com/Ayush-840/Ayush-840`.
2. Click on the **Actions** tab.
3. Click **"I understand my workflows, go ahead and enable them"**.
4. Select **Generate Contribution Snake** from the left sidebar.
5. Click **Run workflow** → **Run workflow**.

That's it! Your profile page `https://github.com/Ayush-840` will immediately show your new header banner, animated typing header, tech badges, project cards, and stats!
