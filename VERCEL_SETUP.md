# Self-Hosting `github-readme-stats` on Vercel (No Rate Limits)

To prevent rate-limiting errors (`503 Service Unavailable` or `429 Too Many Requests`) on your GitHub profile stats cards, self-host your own instance of `github-readme-stats` on Vercel in less than 3 minutes.

---

## Step-by-Step Deployment Guide

### Step 1: Fork the Repository
1. Go to the official repository: [anuraghazra/github-readme-stats](https://github.com/anuraghazra/github-readme-stats).
2. Click **Fork** in the top-right corner to create your own copy on your GitHub account (`Ayush-840/github-readme-stats`).

### Step 2: Create a Personal Access Token (PAT)
1. Go to **GitHub Settings** → **Developer Settings** → **Personal Access Tokens** → **Tokens (classic)** (or [click here](https://github.com/settings/tokens)).
2. Click **Generate new token (classic)**.
3. Note: `Vercel Github Stats Token`.
4. Select Scopes:
   - `repo` (Full control of private repositories - optional, needed if you want private stats)
   - `read:user` (Read user profile data)
   - `user:email`
5. Click **Generate token** and copy the token string (starts with `ghp_...`).

### Step 3: Deploy on Vercel
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New** → **Project**.
3. Import your forked `github-readme-stats` repository.
4. Under **Environment Variables**, add the following variable:
   - **Key**: `PAT_1`
   - **Value**: `ghp_YOUR_PERSONAL_ACCESS_TOKEN` (Paste the token copied in Step 2)
5. Click **Deploy**.

---

## Step 4: Update Your Profile README URLs
Once deployed, Vercel will give you a custom URL (e.g., `https://github-readme-stats-ayush-840.vercel.app`).

In your `README.md`, replace the default domain with your Vercel URL:

```markdown
<!-- Before -->
https://github-readme-stats.vercel.app/api?username=Ayush-840...

<!-- After (Your Vercel Deployment) -->
https://github-readme-stats-ayush-840.vercel.app/api?username=Ayush-840...
```

Now your stats cards will load instantly 100% of the time with zero rate-limit interruptions!
