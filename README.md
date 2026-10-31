![mod-release-bot](.github/preview.png)

# mod-release-bot

Turns a GitHub release of a Blackshield Company Skyrim mod into review-ready **drafts**:

| File | What it is |
|---|---|
| `changelog.bbcode` | Nexus Mods changelog entry (release notes converted from Markdown to BBCode) |
| `nexus-description.bbcode` | "Latest version" block to paste into the Nexus description |
| `post-x.txt` | Short X post, kept within 280 characters (links counted as 23) |
| `post-reddit.md` | Reddit title, subreddit and Markdown body |
| `release-notes.md` | GitHub release notes in Markdown (only with `--from-commits`, see below) |

**Drafts only.** The bot reads GitHub (read-only `gh api --method GET`) or a local clone (`git log` only) and writes
local files. It has no code
path that posts, uploads or sends anything: no Nexus writes, no X/Reddit/Discord calls. A test
(`tests/test_no_send_path.py`) fails the build if HTTP clients, write methods or posting endpoints show up in the package,
or if git is used for anything but `git log`.

## Setup

Needs Python 3.12+ and an authenticated [`gh`](https://cli.github.com/) CLI.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

```sh
# Draft one release -> drafts/scarred-steel/v0.2.0/
.venv/bin/python -m modbot draft scarred-steel v0.2.0

# Print drafts instead of writing files
.venv/bin/python -m modbot draft company-quartermaster v0.2.1 --dry-run

# Write and print
.venv/bin/python -m modbot draft scarred-steel v0.2.0 --print

# Offline, from a saved release JSON (REST or `gh release view --json` shape)
.venv/bin/python -m modbot draft scarred-steel --release-json tests/fixtures/scarred-steel-v0.2.0.json

# Draft every release not seen before, for every mod in mods.toml.
# The first run per repo seeds data/seen.db silently, so old releases don't flood the drafts folder.
.venv/bin/python -m modbot poll
```

Options (any subcommand): `--config mods.toml`, `--out drafts`, `--dry-run`, `--print`; `poll` also takes `--db data/seen.db`.

`poll` can run from a systemd timer or cron. It never sends anything, so check `drafts/` after it runs.

## Drafting from commits

If a mod's history follows [Conventional Commits](https://www.conventionalcommits.org/), `--from-commits` builds the
notes from `git log` of a local clone instead of an existing GitHub release, so you can draft before the release exists:

```sh
# Commits after v0.2.0 up to HEAD in ../scarred-steel -> drafts/scarred-steel/v0.3.0/
.venv/bin/python -m modbot draft scarred-steel v0.3.0 --from-commits --from v0.2.0 --repo-dir ../scarred-steel

# Explicit range, printed instead of written
.venv/bin/python -m modbot draft scarred-steel v0.3.0 --from-commits --from v0.2.0 --to v0.3.0 \
    --repo-dir ../scarred-steel --dry-run
```

- `--from` (required) is exclusive, `--to` (default `HEAD`) inclusive: the same range as `git log FROM..TO`. Merge
  commits are left out; the rest are listed oldest first.
- `--repo-dir` picks the clone; without it the mod's `checkout` from `mods.toml` is used, else the current directory.
- Only `git log` runs. Nothing is fetched, committed, tagged or pushed, and GitHub isn't contacted: links point at
  `https://github.com/<repo>/releases/tag/<tag>`, where the release will be.

Each commit header is parsed as `type(scope)!: description`. A `!` or a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer
marks it breaking. Commits are grouped into:

| Group | Commits |
|---|---|
| Breaking changes | anything marked breaking, whatever its type (never skipped); the footer text is shown under it |
| Features | `feat` |
| Fixes | `fix` |
| Performance | `perf` |
| Other changes | every other type that isn't skipped, plus subjects that aren't Conventional Commits |

`chore`, `ci`, `test`, `docs`, `style` and `build` are skipped by default. The groups become `release-notes.md`
(`### Features` and so on, `**scope:**` before the description), and that Markdown goes through the same pipeline as a
GitHub release body: Nexus changelog, Nexus description and Reddit post. The X post summarizes one sentence per group,
most important first (`Breaking: ... New: ... Fixed: ...`), keeping only whole sentences that fit in 280 characters. If
every commit in the range is skipped, the bot warns and drafts a "Maintenance release" note.

Change the skipped types for all mods in `[defaults]` or per mod. The list replaces the default; `[]` keeps everything:

```toml
[defaults]
skip_commit_types = ["chore", "ci", "test", "docs", "style", "build", "refactor"]

[mods.scarred-steel]
name = "Scarred Steel"
checkout = "../scarred-steel"  # local clone for --from-commits
skip_commit_types = []
```

## mods.toml

Maps each GitHub repo to a display name and an optional Nexus mod ID:

```toml
owner = "synthalorian"

[defaults]
hashtags = ["Skyrim", "SkyrimMods"]
subreddit = "skyrimmods"

[mods.steel-oath]
name = "Steel Oath"
nexus_id = 194208          # posts link to Nexus when set, else to the GitHub release
blurb = "One-line pitch."  # optional; used in the Reddit title
```

## What gets converted

Headings, bullet and numbered lists (nested too), bold/italic/strikethrough, links, images, inline code, code blocks,
quotes and rules. Nexus has no reliable table tag, so tables become `a | b` rows in a `[code]` block. Checksum lines and
donation boilerplate are left out of the changelog and posts (they stay on GitHub). Changelogs over 5,000 characters are
trimmed and end with a link to the full notes.

Templates live in `modbot/templates/` (Jinja2).

## Example

`examples/` holds drafts generated from real releases:

- `examples/scarred-steel/v0.2.0/`
- `examples/company-quartermaster/v0.2.1/`

## Tests

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```
