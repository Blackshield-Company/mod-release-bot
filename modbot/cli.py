"""CLI. Every command only reads GitHub (or a local `git log`) and writes local files. There is deliberately no send/post/upload path."""
import argparse
import json
import os
import sys

from . import commits, config, drafts, github
from .state import Seen


def _emit(args, mod, rel, d=None):
    d = d or drafts.build(mod, rel)
    if args.dry_run:
        for name, text in d.items():
            print(f"===== {mod.slug}/{rel['tag']}/{name} =====\n{text}")
        return None
    path = drafts.write(args.out, mod, rel, d)
    print(f"drafts written: {path}")
    if args.print:
        for name, text in d.items():
            print(f"----- {name} -----\n{text}")
    return path


def cmd_draft(args):
    mods = config.load(args.config)
    mod = config.find(mods, args.repo)
    if args.from_commits:
        return _draft_from_commits(args, mod)
    if args.release_json:
        with open(args.release_json, encoding="utf-8") as f:
            rel = github.normalize(json.load(f))
    else:
        rel = github.release(mod.repo, args.tag)
    _emit(args, mod, rel)
    return 0


def _draft_from_commits(args, mod):
    repo_dir = args.repo_dir or mod.checkout or "."
    try:
        log = commits.git_log(args.from_ref, args.to_ref, repo_dir)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"{repo_dir}: {e}", file=sys.stderr)
        return 1
    groups = commits.group(log, mod.skip_commit_types)
    notes = commits.to_markdown(groups)
    if not notes:
        print(f"no notable commits in {args.from_ref}..{args.to_ref} (all skipped or none)", file=sys.stderr)
        notes = "Maintenance release: no user-facing changes."
    # The release may not exist yet, so link to where it will be rather than asking GitHub.
    rel = {"id": None, "tag": args.tag, "name": "", "body": notes, "assets": [],
           "url": f"https://github.com/{mod.repo}/releases/tag/{args.tag}"}
    d = {"release-notes.md": notes + "\n", **drafts.build(mod, rel, x_text=commits.x_summary(groups) or None)}
    _emit(args, mod, rel, d)
    return 0


def cmd_poll(args, fetch=github.releases):
    mods = config.load(args.config)
    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    seen = Seen(args.db)
    made = 0
    for mod in mods.values():
        try:
            rels = fetch(mod.repo)
        except Exception as e:  # one broken repo shouldn't stop the rest
            print(f"{mod.repo}: {e}", file=sys.stderr)
            continue
        first = not seen.is_seeded(mod.repo)
        for rel in rels:
            key = f"rel:{rel['id']}"
            if seen.has(key):
                continue
            if not first:
                _emit(args, mod, rel)
                made += 1
            if not args.dry_run:
                seen.add(key)
        if first and not args.dry_run:
            seen.mark_seeded(mod.repo)
            print(f"seeded {mod.repo} silently ({len(rels)} releases)")
    print(f"new drafts: {made}")
    return 0


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="mods.toml")
    common.add_argument("--out", default="drafts")
    common.add_argument("--dry-run", action="store_true", help="print drafts instead of writing files (and don't touch seen.db)")
    common.add_argument("--print", action="store_true", help="also print drafts after writing them")
    p = argparse.ArgumentParser(prog="mod-release-bot", description="Turn GitHub mod releases into Nexus/X/Reddit drafts. Never posts.")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", parents=[common], help="draft one release")
    d.add_argument("repo", help="owner/name or just name from mods.toml")
    d.add_argument("tag", nargs="?", help="release tag, e.g. v0.2.0")
    d.add_argument("--release-json", help="use a saved release JSON (REST or `gh release view --json` shape) instead of GitHub")
    d.add_argument("--from-commits", action="store_true", help="build the notes from conventional commits in a local clone")
    d.add_argument("--from", dest="from_ref", help="with --from-commits: start ref, exclusive (e.g. the previous tag)")
    d.add_argument("--to", dest="to_ref", default="HEAD", help="with --from-commits: end ref, inclusive (default HEAD)")
    d.add_argument("--repo-dir", help="with --from-commits: local clone to read (default: checkout in mods.toml, else .)")
    pl = sub.add_parser("poll", parents=[common], help="draft every release not seen before; first run per repo seeds silently")
    pl.add_argument("--db", default="data/seen.db")
    args = p.parse_args(argv)
    if args.cmd == "draft" and not (args.tag or args.release_json):
        p.error("draft needs a tag or --release-json")
    if args.cmd == "draft" and args.from_commits:
        if args.release_json:
            p.error("--from-commits and --release-json can't be combined")
        if not args.tag or not args.from_ref:
            p.error("--from-commits needs a tag and --from")
    elif args.cmd == "draft" and (args.from_ref or args.repo_dir):
        p.error("--from/--repo-dir only apply with --from-commits")
    return cmd_draft(args) if args.cmd == "draft" else cmd_poll(args)


if __name__ == "__main__":
    sys.exit(main())
