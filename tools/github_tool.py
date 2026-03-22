import os
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO", "")
BASE_URL     = "https://api.github.com"
HEADERS      = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def _repo_url(path=""):
    return f"{BASE_URL}/repos/{GITHUB_REPO}/contents/{path.lstrip('/')}"


def list_repo_files(path: str = "") -> str:
    """List files and folders in the website repo at a given path."""
    try:
        res = requests.get(_repo_url(path), headers=HEADERS, timeout=10)
        if res.status_code == 404:
            return f"Path '{path}' not found in repo {GITHUB_REPO}"
        res.raise_for_status()
        items = res.json()
        if isinstance(items, dict):
            # Single file returned
            return f"File: {items['path']} ({items['size']} bytes)"
        lines = []
        for item in items:
            prefix = "📁" if item["type"] == "dir" else "📄"
            lines.append(f"{prefix} {item['path']}")
        return "\n".join(lines) if lines else "Empty directory."
    except Exception as e:
        return f"GitHub list error: {e}"


def read_repo_file(filepath: str) -> str:
    """Read the contents of a file from the website GitHub repo."""
    try:
        res = requests.get(_repo_url(filepath), headers=HEADERS, timeout=10)
        if res.status_code == 404:
            return f"File '{filepath}' not found in repo {GITHUB_REPO}"
        res.raise_for_status()
        data    = res.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content[:6000]
    except Exception as e:
        return f"GitHub read error: {e}"


def write_repo_file(filepath: str, content: str, commit_message: str = "") -> str:
    """
    Write or update a file in the website GitHub repo.
    Creates a commit directly on the default branch.
    """
    try:
        if not commit_message:
            commit_message = f"Update {filepath} via Agent Office"

        # Check if file already exists (need its SHA to update)
        existing = requests.get(_repo_url(filepath), headers=HEADERS, timeout=10)
        sha = existing.json().get("sha") if existing.status_code == 200 else None

        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_message,
            "content": encoded,
        }
        if sha:
            payload["sha"] = sha

        res = requests.put(
            _repo_url(filepath),
            headers=HEADERS,
            data=json.dumps(payload),
            timeout=15,
        )
        res.raise_for_status()
        action = "Updated" if sha else "Created"
        commit = res.json().get("commit", {}).get("sha", "")[:7]
        return f"{action} {filepath} · Commit: {commit}"
    except Exception as e:
        return f"GitHub write error: {e}"


def delete_repo_file(filepath: str, commit_message: str = "") -> str:
    """Delete a file from the website GitHub repo."""
    try:
        if not commit_message:
            commit_message = f"Delete {filepath} via Agent Office"

        existing = requests.get(_repo_url(filepath), headers=HEADERS, timeout=10)
        if existing.status_code == 404:
            return f"File '{filepath}' does not exist."
        sha = existing.json().get("sha")

        payload = {"message": commit_message, "sha": sha}
        res = requests.delete(
            _repo_url(filepath),
            headers=HEADERS,
            data=json.dumps(payload),
            timeout=15,
        )
        res.raise_for_status()
        return f"Deleted {filepath}"
    except Exception as e:
        return f"GitHub delete error: {e}"


def get_repo_info() -> str:
    """Get basic info about the website repo."""
    try:
        res = requests.get(f"{BASE_URL}/repos/{GITHUB_REPO}", headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        return (
            f"Repo: {data['full_name']}\n"
            f"Default branch: {data['default_branch']}\n"
            f"Description: {data.get('description','none')}\n"
            f"Last updated: {data['updated_at']}\n"
            f"URL: {data['html_url']}"
        )
    except Exception as e:
        return f"GitHub info error: {e}"