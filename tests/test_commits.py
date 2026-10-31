import os, subprocess
import pytest
from modbot import cli, commits, config, drafts
from modbot.commits import parse
from modbot.drafts import x_len, X_LIMIT
from conftest import ROOT

# --- parsing ---

def test_type_and_description():
    c = parse("feat: add wear hints")
    assert (c.type, c.scope, c.description, c.breaking) == ("feat", None, "add wear hints", False)

def test_scope():
    c = parse("fix(mcm): toggle no longer resets on load")
    assert c.type == "fix" and c.scope == "mcm" and c.description == "toggle no longer resets on load"

def test_type_is_case_insensitive():
    assert parse("Feat(UI): thing").type == "feat" and parse("FIX: x").type == "fix"

def test_bang_marks_breaking():
    for msg in ("feat!: drop SE 1.5.97 support", "refactor(esp)!: renumber form IDs"):
        c = parse(msg)
        assert c.breaking and c.breaking_note == ""

def test_breaking_change_footer():
    c = parse("feat(save): new save format\n\nLonger body.\n\nBREAKING CHANGE: old saves need a clean reload\nRefs: #12")
    assert c.breaking and c.breaking_note == "old saves need a clean reload" and c.description == "new save format"

def test_breaking_change_hyphen_footer_and_wrapping():
    c = parse("fix: x\n\nBREAKING-CHANGE: the global SCS_Wear\n  is now SCS_WearRate\nReviewed-by: A")
    assert c.breaking and c.breaking_note == "the global SCS_Wear is now SCS_WearRate"

def test_lowercase_breaking_footer_is_not_breaking():
    assert not parse("fix: x\n\nbreaking change: nope").breaking

def test_crlf_and_whitespace():
    c = parse("  feat(a): b  \r\n\r\nBREAKING CHANGE: c\r\n")
    assert c.description == "b" and c.breaking_note == "c"

@pytest.mark.parametrize("msg", ["Add issue templates", "feat:missing space", "feat(): empty scope", ": nothing",
                                 "Merge branch 'x'", "feat(a)(b): two scopes", ""])
def test_non_conventional(msg):
    c = parse(msg)
    assert c.type is None and not c.breaking and c.description == msg.strip()

def test_non_conventional_footer_does_not_count():
    # Only conventional commits carry footers we trust.
    assert not parse("Update readme\n\nBREAKING CHANGE: x").breaking

# --- grouping and rendering ---

LOG = [parse(m, sha=f"{i:040x}") for i, m in enumerate([
    "feat(mcm): add wear-hint toggle",
    "fix: grindstone repairs the right item",
    "perf: cache tier lookups",
    "chore: bump version",
    "docs: readme",
    "ci: cache pip",
    "test: more cases",
    "style: format",
    "build: pack script",
    "refactor: split wear script",
    "Tweak meshes",
    "chore!: drop the legacy plugin",
    "feat(save): new save format\n\nBREAKING CHANGE: old saves need a clean reload",
])]

def test_group_default_skip_and_order():
    g = commits.group(LOG)
    assert list(g) == ["breaking", "features", "fixes", "perf", "other"]
    assert [c.description for c in g["features"]] == ["add wear-hint toggle"]
    assert [c.description for c in g["other"]] == ["split wear script", "Tweak meshes"]
    every = [c.type for v in g.values() for c in v if not c.breaking]
    assert not set(every) & set(commits.DEFAULT_SKIP)

def test_breaking_always_kept_and_not_duplicated():
    g = commits.group(LOG, skip=["chore", "feat"])
    assert [c.description for c in g["breaking"]] == ["drop the legacy plugin", "new save format"]
    assert "features" not in g

def test_custom_skip():
    g = commits.group(LOG, skip=[])
    assert {"bump version", "readme"} <= {c.description for c in g["other"]}
    g = commits.group(LOG, skip=[*commits.DEFAULT_SKIP, "REFACTOR", "perf"])  # a custom list replaces the default
    assert "perf" not in g and [c.description for c in g["other"]] == ["Tweak meshes"]

def test_group_empty():
    assert commits.group([]) == {} and commits.to_markdown({}) == "" and commits.x_summary({}) == ""

def test_markdown():
    md = commits.to_markdown(commits.group(LOG))
    assert md.startswith("### Breaking changes\n\n- drop the legacy plugin\n- **save:** new save format\n"
                         "  - old saves need a clean reload\n\n### Features\n\n- **mcm:** add wear-hint toggle")
    assert md.index("### Fixes") < md.index("### Performance") < md.index("### Other changes")
    assert "bump version" not in md

def test_markdown_to_bbcode():
    m = config.Mod(repo="o/r", name="R")
    rel = {"tag": "v1.0.0", "body": commits.to_markdown(commits.group(LOG)), "url": "https://github.com/o/r/releases/tag/v1.0.0"}
    d = drafts.build(m, rel)
    assert "[size=4][b]Breaking changes[/b][/size]" in d["changelog.bbcode"]
    assert "[*][b]mcm:[/b] add wear-hint toggle" in d["changelog.bbcode"]
    assert "[list]\n[*]old saves need a clean reload\n[/list]" in d["changelog.bbcode"]
    assert d["nexus-description.bbcode"].startswith("[size=4][b]Latest version: 1.0.0[/b][/size]\n[size=4][b]Breaking")

def test_x_summary():
    s = commits.x_summary(commits.group(LOG))
    assert s.startswith("Breaking: drop the legacy plugin; new save format. New: add wear-hint toggle. Fixed:")

def test_x_draft_within_limit():
    m = config.Mod(repo="o/r", name="R")
    many = [parse(f"feat: a fairly long feature description number {i}") for i in range(40)]
    for log in (LOG, many, [parse("fix: " + "x" * 400)]):
        g = commits.group(log)
        rel = {"tag": "v1", "body": commits.to_markdown(g), "url": "https://github.com/o/r/releases/tag/v1"}
        x = drafts.build(m, rel, x_text=commits.x_summary(g))["post-x.txt"]
        assert x_len(x) <= X_LIMIT, x
        assert "https://github.com/o/r/releases/tag/v1" in x

def test_x_keeps_whole_sentences():
    g = commits.group(LOG)
    rel = {"tag": "v1", "body": commits.to_markdown(g), "url": "https://github.com/o/r/releases/tag/v1"}
    x = drafts.build(config.Mod(repo="o/r", name="R"), rel, x_text=commits.x_summary(g))["post-x.txt"]
    assert "Breaking: drop the legacy plugin; new save format." in x and "…" not in x

# --- git (read-only) ---

def test_bad_refs_rejected():
    for ref in ("--output=/tmp/x", "-p", "a b", "", "v1..v2"):
        with pytest.raises(ValueError):
            commits.git_log(ref)

def test_git_log_is_read_only(monkeypatch):
    calls = []
    class P: returncode = 0; stdout = "abc\x1ffeat: x\n\x1e\ndef\x1fhello\x1e\n"; stderr = ""
    monkeypatch.setattr(commits.subprocess, "run", lambda a, **k: calls.append(a) or P())
    out = commits.git_log("v1", "v2", "/r")
    assert calls[0][:4] == ["git", "-C", "/r", "log"] and calls[0][-2:] == ["v1..v2", "--"]
    assert [(c.sha, c.type, c.description) for c in out] == [("abc", "feat", "x"), ("def", None, "hello")]

def test_git_log_error(monkeypatch):
    class P: returncode = 128; stdout = ""; stderr = "fatal: bad revision 'nope..HEAD'"
    monkeypatch.setattr(commits.subprocess, "run", lambda a, **k: P())
    with pytest.raises(RuntimeError, match="bad revision"):
        commits.git_log("nope")

def _git(repo, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)

@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "mod"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "commit", "-q", "--allow-empty", "-m", "feat: first release")
    _git(r, "tag", "v0.1.0")
    for msg in ("feat(mcm): add wear-hint toggle", "chore: bump version",
                "fix: grindstone repairs the right item\n\nCloses #4",
                "feat!: new save format\n\nBREAKING CHANGE: old saves need a clean reload",
                "Tweak meshes"):
        _git(r, "commit", "-q", "--allow-empty", "-m", msg)
    _git(r, "tag", "v0.2.0")
    _git(r, "commit", "-q", "--allow-empty", "-m", "feat: after the tag")
    return r

def test_git_log_real_repo(repo):
    log = commits.git_log("v0.1.0", "v0.2.0", str(repo))
    assert [c.subject for c in log] == ["feat(mcm): add wear-hint toggle", "chore: bump version",
                                        "fix: grindstone repairs the right item", "feat!: new save format", "Tweak meshes"]
    assert len(log[0].sha) == 40 and log[3].breaking_note == "old saves need a clean reload"
    assert commits.git_log("v0.1.0", repo_dir=str(repo))[-1].description == "after the tag"

def test_git_log_leaves_repo_untouched(repo):
    def state():
        p = subprocess.run(["git", "-C", str(repo), "for-each-ref"], capture_output=True, text=True)
        s = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
        return p.stdout + s.stdout
    before = state()
    commits.git_log("v0.1.0", "v0.2.0", str(repo))
    assert state() == before

# --- config ---

def test_config_skip_defaults_and_override(tmp_path):
    cfg = tmp_path / "mods.toml"
    cfg.write_text('[defaults]\nskip_commit_types = ["chore"]\n[mods.a]\nname = "A"\n'
                   '[mods.b]\nname = "B"\nskip_commit_types = []\ncheckout = "../b"\n[mods.c]\nname = "C"\n')
    mods = config.load(cfg)
    assert config.find(mods, "a").skip_commit_types == ["chore"] and config.find(mods, "b").skip_commit_types == []
    assert config.find(mods, "b").checkout == "../b" and config.find(mods, "a").checkout is None

def test_config_skip_builtin_default(mods):
    assert config.find(mods, "scarred-steel").skip_commit_types == commits.DEFAULT_SKIP

def test_config_skip_must_be_list(tmp_path):
    cfg = tmp_path / "mods.toml"
    cfg.write_text('[mods.a]\nname = "A"\nskip_commit_types = "chore"\n')
    with pytest.raises(ValueError):
        config.load(cfg)

# --- CLI ---

def _cfg(tmp_path, extra=""):
    cfg = tmp_path / "mods.toml"
    cfg.write_text(f'owner = "o"\n[mods.mod]\nname = "My Mod"\n{extra}')
    return str(cfg)

def test_cli_from_commits(tmp_path, repo, capsys):
    out = tmp_path / "drafts"
    rc = cli.main(["draft", "mod", "v0.2.0", "--from-commits", "--from", "v0.1.0", "--to", "v0.2.0",
                   "--repo-dir", str(repo), "--config", _cfg(tmp_path), "--out", str(out)])
    assert rc == 0
    d = out / "mod" / "v0.2.0"
    assert sorted(p.name for p in d.iterdir()) == ["changelog.bbcode", "nexus-description.bbcode", "post-reddit.md",
                                                   "post-x.txt", "release-notes.md"]
    notes = (d / "release-notes.md").read_text()
    assert notes == ("### Breaking changes\n\n- new save format\n  - old saves need a clean reload\n\n"
                     "### Features\n\n- **mcm:** add wear-hint toggle\n\n"
                     "### Fixes\n\n- grindstone repairs the right item\n\n"
                     "### Other changes\n\n- Tweak meshes\n")
    assert "bump version" not in (d / "changelog.bbcode").read_text()
    assert "[b]mcm:[/b] add wear-hint toggle" in (d / "nexus-description.bbcode").read_text()
    x = (d / "post-x.txt").read_text()
    assert x_len(x) <= X_LIMIT and x.startswith("My Mod 0.2.0 is out") and "Breaking: new save format." in x
    assert "https://github.com/o/mod/releases/tag/v0.2.0" in x
    assert "### Features" in (d / "post-reddit.md").read_text()

def test_cli_from_commits_to_defaults_head_and_checkout(tmp_path, repo, capsys):
    cfg = _cfg(tmp_path, f'checkout = "{repo}"\n')
    cli.main(["draft", "mod", "v0.3.0", "--from-commits", "--from", "v0.2.0", "--config", cfg, "--dry-run"])
    out = capsys.readouterr().out
    assert "===== mod/v0.3.0/release-notes.md =====\n### Features\n\n- after the tag\n" in out

def test_cli_from_commits_uses_config_skip(tmp_path, repo, capsys):
    cfg = _cfg(tmp_path, 'skip_commit_types = []\n')
    cli.main(["draft", "mod", "v0.2.0", "--from-commits", "--from", "v0.1.0", "--to", "v0.2.0",
              "--repo-dir", str(repo), "--config", cfg, "--dry-run"])
    assert "- bump version" in capsys.readouterr().out

def test_cli_from_commits_dry_run_writes_nothing(tmp_path, repo, capsys):
    out = tmp_path / "drafts"
    cli.main(["draft", "mod", "v0.2.0", "--from-commits", "--from", "v0.1.0", "--repo-dir", str(repo),
              "--config", _cfg(tmp_path), "--out", str(out), "--dry-run"])
    assert "===== mod/v0.2.0/post-x.txt" in capsys.readouterr().out and not out.exists()

def test_cli_from_commits_nothing_notable(tmp_path, repo, capsys):
    _git(repo, "commit", "-q", "--allow-empty", "-m", "docs: typo")
    cli.main(["draft", "mod", "v0.2.1", "--from-commits", "--from", "HEAD~1", "--repo-dir", str(repo),
              "--config", _cfg(tmp_path), "--dry-run"])
    cap = capsys.readouterr()
    assert "no notable commits" in cap.err and "Maintenance release" in cap.out

def test_cli_from_commits_bad_ref(tmp_path, repo, capsys):
    rc = cli.main(["draft", "mod", "v0.2.0", "--from-commits", "--from", "nope", "--repo-dir", str(repo),
                   "--config", _cfg(tmp_path), "--dry-run"])
    assert rc == 1 and "nope" in capsys.readouterr().err

@pytest.mark.parametrize("argv", [
    ["draft", "mod", "v1", "--from-commits"],                                    # no --from
    ["draft", "mod", "--from-commits", "--from", "v0"],                          # no tag
    ["draft", "mod", "v1", "--from-commits", "--from", "v0", "--release-json", "x.json"],
    ["draft", "mod", "v1", "--from", "v0"],                                      # --from without --from-commits
])
def test_cli_from_commits_arg_errors(argv):
    with pytest.raises(SystemExit):
        cli.main(argv)
