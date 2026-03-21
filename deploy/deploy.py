#!/usr/bin/env python3
"""
deploy.py - Automates web-app configuration on PythonAnywhere via their API.

What this script does automatically:
  1. Creates (or verifies) your web app on PythonAnywhere
  2. Writes the correct WSGI configuration file
  3. Sets the path to your virtual environment
  4. Reloads the web app so your changes go live

What you must do ONCE in the PythonAnywhere bash console first:
  Run:  bash ~/mathquest/deploy/setup.sh
  (See README.md for full instructions)

Usage:
  python deploy.py --username YOUR_PA_USERNAME --token YOUR_API_TOKEN

Optional flags:
  --region eu        Use EU region (eu.pythonanywhere.com). Default: US (www)
    --python 3.12      Python version for the web app. Default: 3.12

Get your API token from: https://www.pythonanywhere.com/user/YOUR_USERNAME/account/#api_token
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' is not installed.\nRun:  pip install requests")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(region: str) -> str:
    host = (
        "eu.pythonanywhere.com" if region == "eu" else "www.pythonanywhere.com"
    )
    return f"https://{host}/api/v0"


def _headers(token: str) -> dict:
    return {"Authorization": f"Token {token}"}


def _normalize_python_version(version: str) -> str:
    """Normalize user input into the PythonAnywhere API version format (e.g. 3.12)."""
    value = version.strip().lower()

    # Accept common variants: "3.12", "python3.12", "python312"
    if value.startswith("python"):
        value = value[len("python") :]

    if "." not in value and value.isdigit() and len(value) >= 2:
        value = f"{value[0]}.{value[1:]}"

    return value


def _check(resp, label: str) -> dict:
    if resp.status_code not in (200, 201):
        print(f"\n[ERROR] {label}")
        print(f"  HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    return resp.json()


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def get_or_create_webapp(
    base: str, headers: dict, username: str, domain: str, python_version: str
) -> dict:
    """Create the web app if it doesn't exist yet; return its config."""
    list_resp = requests.get(
        f"{base}/user/{username}/webapps/", headers=headers
    )
    webapps = _check(list_resp, "listing web apps")
    normalized_python = _normalize_python_version(python_version)

    existing = next((w for w in webapps if w["domain_name"] == domain), None)
    if existing:
        existing_python = existing.get("python_version", "")
        if existing_python != normalized_python:
            print(
                f"  Web app '{domain}' exists with Python {existing_python}"
                f" but {normalized_python} was requested — recreating..."
            )
            del_resp = requests.delete(
                f"{base}/user/{username}/webapps/{domain}/",
                headers=headers,
            )
            if del_resp.status_code not in (200, 204):
                print("\n[ERROR] deleting old web app")
                print(f"  HTTP {del_resp.status_code}: {del_resp.text}")
                sys.exit(1)
        else:
            print(f"  Web app '{domain}' already exists — skipping creation.")
            return existing

    print(f"  Creating web app '{domain}' with Python {normalized_python}...")
    create_resp = requests.post(
        f"{base}/user/{username}/webapps/",
        headers=headers,
        data={"domain_name": domain, "python_version": normalized_python},
    )
    return _check(create_resp, "creating web app")


def upload_wsgi(base: str, headers: dict, username: str, domain: str) -> None:
    """Write the correct WSGI file to PythonAnywhere."""
    wsgi_template = Path(__file__).parent / "wsgi.py"
    wsgi_content = wsgi_template.read_text().replace("YOUR_USERNAME", username)

    pa_wsgi_path = f"var/www/{domain.replace('.', '_')}_wsgi.py"
    print(f"  Uploading WSGI config → /{pa_wsgi_path} ...")

    resp = requests.post(
        f"{base}/user/{username}/files/path/{pa_wsgi_path}",
        headers=headers,
        files={"content": ("wsgi.py", wsgi_content.encode())},
    )
    if resp.status_code not in (200, 201):
        print("\n[ERROR] Uploading WSGI file")
        print(f"  HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    print("  WSGI file uploaded.")


def set_virtualenv(
    base: str, headers: dict, username: str, domain: str
) -> None:
    """Point the web app at the virtualenv created by setup.sh."""
    venv_path = f"/home/{username}/mathquest/venv"
    print(f"  Setting virtualenv path → {venv_path} ...")

    resp = requests.patch(
        f"{base}/user/{username}/webapps/{domain}/",
        headers=headers,
        data={"virtualenv_path": venv_path},
    )
    _check(resp, "setting virtualenv path")
    print("  Virtualenv configured.")


def reload_webapp(
    base: str, headers: dict, username: str, domain: str
) -> None:
    """Send the reload signal so the new config goes live."""
    print("  Reloading web app...")
    resp = requests.post(
        f"{base}/user/{username}/webapps/{domain}/reload/",
        headers=headers,
    )
    if resp.status_code not in (200, 201):
        print("\n[ERROR] Reloading web app")
        print(f"  HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    print("  Reloaded successfully.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy MathQuest to PythonAnywhere.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Example:
              python deploy.py --username andy --token abc123xyz

            Get your API token from:
              https://www.pythonanywhere.com/user/<YOUR_USERNAME>/account/#api_token
        """),
    )
    parser.add_argument(
        "--username", required=True, help="Your PythonAnywhere username"
    )
    parser.add_argument(
        "--token", required=True, help="Your PythonAnywhere API token"
    )
    parser.add_argument(
        "--region",
        choices=["us", "eu"],
        default="us",
        help="Server region: 'us' (default) or 'eu'",
    )
    parser.add_argument(
        "--python",
        default="3.12",
        metavar="VERSION",
        help="Python version for the web app (default: 3.12)",
    )
    args = parser.parse_args()

    username = args.username
    domain = f"{username}.pythonanywhere.com"
    base = _api(args.region)
    headers = _headers(args.token)

    print(f"\nDeploying MathQuest → https://{domain}")
    print("=" * 50)

    print("\n[1/4] Web app setup")
    get_or_create_webapp(base, headers, username, domain, args.python)

    print("\n[2/4] WSGI configuration")
    upload_wsgi(base, headers, username, domain)

    print("\n[3/4] Virtual environment")
    set_virtualenv(base, headers, username, domain)

    print("\n[4/4] Reload")
    reload_webapp(base, headers, username, domain)

    print(f"\nDone!  Your app is live at https://{domain}\n")


if __name__ == "__main__":
    main()
