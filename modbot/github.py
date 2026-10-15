"""Read-only GitHub access through the gh CLI (same approach as release-notifier). Only GET requests."""
import json
import subprocess


def gh_get(path: str):
    p = subprocess.run(["gh", "api", "--method", "GET", path], capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[:300])
    return json.loads(p.stdout or "null")


def normalize(r: dict) -> dict:
    """Keep only the fields the drafts need, from either the REST API or `gh release view --json` shape."""
    return {
        "id": r.get("id"),
        "tag": r.get("tag_name") or r.get("tagName"),
        "name": r.get("name") or "",
        "body": r.get("body") or "",
        "url": r.get("html_url") or r.get("url"),
        "published_at": r.get("published_at") or r.get("publishedAt"),
        "draft": bool(r.get("draft") or r.get("isDraft")),
        "prerelease": bool(r.get("prerelease") or r.get("isPrerelease")),
        "assets": [{"name": a["name"], "size": a.get("size", 0)} for a in r.get("assets", [])],
    }


def release(repo: str, tag: str) -> dict:
    return normalize(gh_get(f"repos/{repo}/releases/tags/{tag}"))


def releases(repo: str, n: int = 10) -> list[dict]:
    return [normalize(r) for r in gh_get(f"repos/{repo}/releases?per_page={n}") if not r.get("draft")]
