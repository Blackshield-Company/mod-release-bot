"""mods.toml: maps a GitHub repo to its Nexus mod ID, display name and tags."""
import tomllib
from dataclasses import dataclass, field

from .commits import DEFAULT_SKIP

NEXUS_GAME = "skyrimspecialedition"


@dataclass
class Mod:
    repo: str  # owner/name
    name: str
    nexus_id: int | None = None
    hashtags: list[str] = field(default_factory=lambda: ["Skyrim", "SkyrimMods"])
    subreddit: str = "skyrimmods"
    blurb: str = ""
    # Conventional-commit types left out of commit-based notes (breaking changes always stay in).
    skip_commit_types: list[str] = field(default_factory=lambda: list(DEFAULT_SKIP))
    checkout: str | None = None  # local clone used by `draft --from-commits`; --repo-dir overrides it

    @property
    def slug(self) -> str:
        return self.repo.split("/")[-1]

    @property
    def nexus_url(self) -> str | None:
        return f"https://www.nexusmods.com/{NEXUS_GAME}/mods/{self.nexus_id}" if self.nexus_id else None


def load(path) -> dict[str, Mod]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    owner = data.get("owner", "synthalorian")
    defaults = data.get("defaults", {})
    mods = {}
    for slug, m in data.get("mods", {}).items():
        merged = {**defaults, **m}
        repo = merged.pop("repo", f"{owner}/{slug}")
        skip = merged.get("skip_commit_types", DEFAULT_SKIP)
        if not isinstance(skip, list) or not all(isinstance(t, str) for t in skip):
            raise ValueError(f"mods.{slug}.skip_commit_types must be a list of strings")
        mods[repo.lower()] = Mod(repo=repo, **merged)
    return mods


def find(mods: dict[str, Mod], repo: str) -> Mod:
    key = repo.lower() if "/" in repo else None
    if key and key in mods:
        return mods[key]
    for m in mods.values():
        if m.slug.lower() == repo.lower():
            return m
    raise KeyError(f"{repo} is not in mods.toml")
