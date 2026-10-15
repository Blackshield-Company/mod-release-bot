# mod-release-bot

Turns a GitHub release of a Blackshield Company Skyrim mod into review-ready **drafts**:

| File | What it is |
|---|---|
| `changelog.bbcode` | Nexus Mods changelog entry (release notes converted from Markdown to BBCode) |
| `nexus-description.bbcode` | "Latest version" block to paste into the Nexus description |
| `post-x.txt` | Short X post, kept within 280 characters (links counted as 23) |
| `post-reddit.md` | Reddit title, subreddit and Markdown body |

**Drafts only.** The bot reads GitHub (read-only `gh api --method GET`) and writes local files. It has no code
path that posts, uploads or sends anything: no Nexus writes, no X/Reddit/Discord calls. A test
(`tests/test_no_send_path.py`) fails the build if HTTP clients, write methods or posting endpoints show up in the package.

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

## mods.toml

Maps each GitHub repo to a display name and an optional Nexus mod ID:

```toml
owner = "Blackshield-Company"

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
