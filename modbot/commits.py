"""Conventional Commits -> grouped release notes. Reads a local checkout with `git log` only; never writes to it."""
import re
import subprocess
from dataclasses import dataclass

DEFAULT_SKIP = ["chore", "ci", "test", "docs", "style", "build"]
GROUPS = [  # (key, Markdown heading), in render order
    ("breaking", "Breaking changes"),
    ("features", "Features"),
    ("fixes", "Fixes"),
    ("perf", "Performance"),
    ("other", "Other changes"),
]
_TYPE_GROUP = {"feat": "features", "fix": "fixes", "perf": "perf"}
_X_LABEL = {"breaking": "Breaking", "features": "New", "fixes": "Fixed", "perf": "Faster", "other": "Also"}

_HEADER = re.compile(r"^(?P<type>[A-Za-z]+)(?:\((?P<scope>[^()\r\n]+)\))?(?P<bang>!)?:\s+(?P<desc>\S.*)$")
_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:\s*(?P<text>.*)$")
_FOOTER = re.compile(r"^(?:[\w-]+: |[\w-]+ #|BREAKING[ -]CHANGE:)")
_SEP_FIELD, _SEP_RECORD = "\x1f", "\x1e"


@dataclass
class Commit:
    sha: str
    subject: str
    type: str | None = None  # None: subject doesn't follow Conventional Commits
    scope: str | None = None
    description: str = ""
    breaking: bool = False
    breaking_note: str = ""  # text of the BREAKING CHANGE footer, if any


def parse(message: str, sha: str = "") -> Commit:
    """Parses one commit message. Non-conventional subjects come back with type=None and the subject as description."""
    lines = (message or "").replace("\r\n", "\n").strip().split("\n")
    subject = lines[0].strip()
    m = _HEADER.match(subject)
    if not m:
        return Commit(sha=sha, subject=subject, description=subject)
    notes, current = [], None
    for ln in lines[1:]:
        fm = _BREAKING_FOOTER.match(ln)
        if fm:
            current = [fm["text"].strip()]
            notes.append(current)
        elif current is not None and ln.strip() and not _FOOTER.match(ln):
            current.append(ln.strip())  # footer values may wrap onto following lines
        else:
            current = None
    note = " ".join(" ".join(p for p in n if p) for n in notes).strip()
    return Commit(sha=sha, subject=subject, type=m["type"].lower(), scope=(m["scope"] or "").strip() or None,
                  description=m["desc"].strip(), breaking=bool(m["bang"] or notes), breaking_note=note)


def _check_ref(ref: str) -> str:
    if not ref or ref.startswith("-") or any(c.isspace() for c in ref) or ".." in ref:
        raise ValueError(f"not a usable git ref: {ref!r}")
    return ref


def git_log(from_ref: str, to_ref: str = "HEAD", repo_dir: str = ".") -> list[Commit]:
    """Commits in from_ref..to_ref, oldest first, merges left out. Read-only: runs `git log` and nothing else."""
    rng = f"{_check_ref(from_ref)}..{_check_ref(to_ref)}"
    p = subprocess.run(["git", "-C", repo_dir, "log", "--no-merges", "--reverse", f"--format=%H{_SEP_FIELD}%B{_SEP_RECORD}",
                        rng, "--"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[:300] or f"git log {rng} failed")
    out = []
    for rec in p.stdout.split(_SEP_RECORD):
        sha, _, msg = rec.strip("\n").partition(_SEP_FIELD)
        if sha.strip():
            out.append(parse(msg, sha.strip()))
    return out


def group(commits: list[Commit], skip=DEFAULT_SKIP) -> dict[str, list[Commit]]:
    """Buckets commits into GROUPS order. Skipped types are dropped, except breaking changes, which always show."""
    skip = {s.lower() for s in skip}
    out = {key: [] for key, _ in GROUPS}
    for c in commits:
        if c.breaking:
            out["breaking"].append(c)
        elif c.type not in skip:
            out[_TYPE_GROUP.get(c.type, "other")].append(c)
    return {k: v for k, v in out.items() if v}


def _item(c: Commit) -> str:
    return (f"**{c.scope}:** " if c.scope else "") + c.description


def to_markdown(groups: dict[str, list[Commit]]) -> str:
    """GitHub release-notes Markdown; the same text feeds the BBCode changelog, Nexus description and posts."""
    parts = []
    for key, heading in GROUPS:
        if key not in groups:
            continue
        lines = [f"### {heading}", ""]
        for c in groups[key]:
            lines.append(f"- {_item(c)}")
            if key == "breaking" and c.breaking_note and c.breaking_note != c.description:
                lines.append(f"  - {c.breaking_note}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def x_summary(groups: dict[str, list[Commit]]) -> str:
    """One short sentence per group ("New: a; b."), most important first, so drafts.summary() can keep whole ones."""
    out = []
    for key, _ in GROUPS:
        if key in groups:
            items = "; ".join(c.description.rstrip(".") for c in groups[key])
            out.append(f"{_X_LABEL[key]}: {items}.")
    return " ".join(out)
