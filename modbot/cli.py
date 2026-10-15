"""CLI. Every command only reads GitHub and writes local files. There is deliberately no send/post/upload path."""
import argparse
import json
import os
import sys

from . import config, drafts, github
from .state import Seen


def _emit(args, mod, rel):
    d = drafts.build(mod, rel)
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
    if args.release_json:
        with open(args.release_json, encoding="utf-8") as f:
            rel = github.normalize(json.load(f))
    else:
        rel = github.release(mod.repo, args.tag)
    _emit(args, mod, rel)
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
    pl = sub.add_parser("poll", parents=[common], help="draft every release not seen before; first run per repo seeds silently")
    pl.add_argument("--db", default="data/seen.db")
    args = p.parse_args(argv)
    if args.cmd == "draft" and not (args.tag or args.release_json):
        p.error("draft needs a tag or --release-json")
    return cmd_draft(args) if args.cmd == "draft" else cmd_poll(args)


if __name__ == "__main__":
    sys.exit(main())
