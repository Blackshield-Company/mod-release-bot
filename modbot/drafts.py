"""Builds the draft files. Pure functions: nothing here touches the network."""
import os
import re
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .bbcode import md_to_bbcode
from .config import Mod

X_LIMIT = 280
X_URL_LEN = 23  # X counts every link as 23 characters (t.co)
REDDIT_TITLE_LIMIT = 300
REDDIT_BODY_LIMIT = 40000
NEXUS_CHANGELOG_LIMIT = 5000  # conservative cap for one changelog version entry

_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
                   undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)

_NOISE = re.compile(r"^\s*(sha256\b|donations? are optional|- (github sponsors|ko-fi):)", re.I)


def version(tag: str) -> str:
    return tag[1:] if tag[:1] in "vV" and tag[1:2].isdigit() else tag


def clean_notes(body: str) -> str:
    """Drops checksum and donation boilerplate; it stays on GitHub, not in the Nexus changelog."""
    lines = [ln for ln in (body or "").replace("\r\n", "\n").split("\n") if not _NOISE.match(ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def plain(md: str) -> str:
    t = re.sub(r"```.*?```", "", md, flags=re.S)
    t = re.sub(r"^#+\s*.*$", "", t, flags=re.M)  # headings are labels, not content
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"(\*\*|__|[`*>])", "", t)
    t = re.sub(r"^\s*[-+]\s+", "", t, flags=re.M)
    return re.sub(r"\s+", " ", t).strip()


def summary(md: str, limit: int) -> str:
    """Whole sentences from the notes that fit in `limit` chars; falls back to a word-trimmed cut."""
    text = plain(md)
    if len(text) <= limit:
        return text
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", text):
        if len(out) + len(s) + (1 if out else 0) > limit:
            break
        out = f"{out} {s}" if out else s
    if out:
        return out
    cut = text[: max(0, limit - 1)].rsplit(" ", 1)[0]
    return cut + "…"


def x_len(text: str) -> int:
    return len(re.sub(r"https?://\S+", "x" * X_URL_LEN, text))


def build(mod: Mod, rel: dict) -> dict[str, str]:
    notes = clean_notes(rel["body"])
    ver = version(rel["tag"])
    link = mod.nexus_url or rel["url"]
    ctx = dict(mod=mod, rel=rel, ver=ver, link=link, notes=notes)
    changelog = md_to_bbcode(notes) if notes else "[list]\n[*]See GitHub release.\n[/list]\n"
    if len(changelog) > NEXUS_CHANGELOG_LIMIT:
        tail = f"\n\nFull notes: {rel['url']}\n"
        head = changelog[: NEXUS_CHANGELOG_LIMIT - len(tail) - 60].rsplit("\n", 1)[0]
        head += "\n[/list]" * max(0, len(re.findall(r"\[list(=1)?\]", head)) - head.count("[/list]"))
        changelog = head + tail
    ctx["changelog"] = changelog

    tags = " ".join(f"#{h}" for h in mod.hashtags)
    fixed = _env.get_template("post-x.txt.j2").render(**ctx, tags=tags, blurb="")
    room = X_LIMIT - x_len(fixed)
    ctx_x = dict(ctx, tags=tags, blurb=summary(notes or mod.blurb, max(0, room)))
    x = _env.get_template("post-x.txt.j2").render(**ctx_x)
    if x_len(x) > X_LIMIT:  # hashtags are the first thing to go
        x = _env.get_template("post-x.txt.j2").render(**dict(ctx_x, tags=""))
    title = f"{mod.name} {ver} released" + (f": {summary(mod.blurb, 120)}" if mod.blurb else "")
    reddit = _env.get_template("post-reddit.md.j2").render(**ctx, title=title[:REDDIT_TITLE_LIMIT])[:REDDIT_BODY_LIMIT]
    return {
        "changelog.bbcode": changelog,
        "nexus-description.bbcode": _env.get_template("nexus-description.bbcode.j2").render(**ctx),
        "post-x.txt": x,
        "post-reddit.md": reddit,
    }


def write(out_root: str, mod: Mod, rel: dict, drafts: dict[str, str]) -> str:
    d = os.path.join(out_root, mod.slug, rel["tag"])
    os.makedirs(d, exist_ok=True)
    for name, text in drafts.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(text)
    return d
