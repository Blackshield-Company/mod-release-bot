# Mod Release Bot (drafts only)

## Goal
When a Skyrim mod gets a GitHub release, turn it into (1) a Nexus-ready BBCode changelog and description update and (2) a short announcement post draft for X/Reddit/Discord. It only writes drafts, to files and a review queue. It never uploads to Nexus or posts anywhere on its own.

## Stack
- Python 3.12, `requests` 2.32, the `gh` CLI for GitHub (the same as `release-notifier`), `jinja2` 3.1 templates, `markdown-it-py` 3 → BBCode converter (hand-written renderer)
- State: SQLite (`seen.db`, the same pattern as release-notifier)
- Output: `drafts/<mod>/<tag>/{changelog.bbcode, nexus-description.bbcode, post-x.txt, post-reddit.md}`
- Trigger: systemd timer polling, or a hook inside `release-notifier`

## First-weekend MVP
- [ ] Map GitHub repo → Nexus mod ID + template in `mods.toml`
- [ ] Fetch the new release (tag, notes, assets); seed silently on first run
- [ ] Markdown release notes → Nexus BBCode changelog (headings, lists, links, code)
- [ ] Post drafts within each platform's character limits, with link + version
- [ ] `--dry-run` prints drafts; a Discord DM "draft ready" note reuses the notifier's DM path

## Risks and unknowns
- Nexus has no public upload/changelog-write API for regular authors, so drafts-only is also the only option there. Fine
- Markdown→BBCode edge cases (nested lists, tables) and Nexus's BBCode quirks; test against existing `scarred_steel_bbcode.txt`
- Keep secrets in `.env` only (as release-notifier does), and never add a send path, so the bot can't post by accident

## Box weight (about 5 GB free RAM on paper, ~2 GB actually available at scope time, no swap)
Negligible. A few MB on disk, under 80 MB RAM per run.

## Reuse
`release-notifier/notifier.py` (gh polling, seen-ID SQLite, Discord DM, first-run seeding). This could be a module of it. `skyrim/nexus`, `skyrim/dist`, `scarred_steel_bbcode.txt`, `post_text_v110.txt` and `/workspace/posts` for templates and tone; `marketing/` for post images.
