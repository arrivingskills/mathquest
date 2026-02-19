# Deploying MathQuest on PythonAnywhere

## Overview

Deployment is split into two stages:

| Stage | What | Where | Frequency |
|-------|------|--------|-----------|
| **Setup** | Clone repo, create virtualenv, install dependencies | PythonAnywhere bash console | **Once** |
| **Deploy** | Configure web app, upload WSGI, reload | Your local machine | Every release |

---

## Prerequisites

- A [PythonAnywhere](https://www.pythonanywhere.com) account (free tier works)
- Your API token (get it from **Account → API token** on PythonAnywhere)
- `requests` installed locally: `pip install requests`

---

## Step 1 — One-time server setup (PythonAnywhere bash console)

1. Log in to PythonAnywhere.
2. Go to **Consoles → Bash** and open a new bash console.
3. Paste and run:

```bash
git clone https://github.com/arrivingskills/mathquest.git
bash ~/mathquest/deploy/setup.sh
```

That's it. The script will:

- Pull the latest code from GitHub
- Create a virtual environment at `~/mathquest/venv`
- Install all dependencies

---

## Step 2 — Deploy from your local machine

From the `mathquest/deploy/` folder on your machine:

```bash
python deploy.py --username YOUR_PA_USERNAME --token YOUR_API_TOKEN
```

Replace `YOUR_PA_USERNAME` and `YOUR_API_TOKEN` with your actual values.

**EU region?** Add `--region eu`:

```bash
python deploy.py --username YOUR_PA_USERNAME --token YOUR_API_TOKEN --region eu
```

The script will automatically:

1. Create the web app at `https://YOUR_PA_USERNAME.pythonanywhere.com`
2. Write the correct WSGI configuration
3. Configure the virtual environment path
4. Reload the app so it goes live

---

## Redeploying after code changes

1. Push your changes to GitHub as normal (`git push`).
2. In the PythonAnywhere bash console, run:

   ```bash
   bash ~/mathquest/deploy/update.sh
   ```

3. Then on your local machine:

   ```bash
   python deploy/deploy.py --username YOUR_PA_USERNAME --token YOUR_API_TOKEN
   ```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: requests` | Run `pip install requests` locally |
| HTTP 401 on deploy | Check your API token is correct |
| App loads but shows an error | In PythonAnywhere, check **Web → Error log** |
| Changes not showing | Make sure you ran `update.sh` AND reloaded |

---

## Files in this folder

| File | Purpose |
|------|---------|
| `deploy.py` | Automated web app configuration via PythonAnywhere API |
| `setup.sh` | One-time server setup (run in PA bash console) |
| `update.sh` | Pull new code + reinstall (run in PA bash console) |
| `wsgi.py` | WSGI entry point template (uploaded automatically by deploy.py) |
