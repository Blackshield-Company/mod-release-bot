import json, os, pytest
from modbot import config, cli, github
from conftest import ROOT

def test_load(mods):
    m = config.find(mods, "scarred-steel")
    assert m.repo == "synthalorian/scarred-steel" and m.nexus_url is None
    assert config.find(mods, "synthalorian/steel-oath").nexus_id == 194208

def test_unknown(mods):
    with pytest.raises(KeyError):
        config.find(mods, "nope")

def test_normalize_both_shapes():
    rest = github.normalize({"id": 1, "tag_name": "v1", "html_url": "u", "body": None, "assets": [{"name": "a.zip", "size": 3}]})
    ghv = github.normalize({"tagName": "v1", "url": "u", "isDraft": False})
    assert rest["tag"] == ghv["tag"] == "v1" and rest["body"] == "" and rest["assets"][0]["name"] == "a.zip"

def test_gh_get_is_read_only(monkeypatch):
    calls = []
    class P: returncode = 0; stdout = "[]"; stderr = ""
    monkeypatch.setattr(github.subprocess, "run", lambda a, **k: calls.append(a) or P())
    github.gh_get("repos/o/r/releases")
    assert calls[0][:4] == ["gh", "api", "--method", "GET"]

def test_cli_draft_from_json(tmp_path, capsys):
    rc = cli.main(["draft", "scarred-steel", "--config", os.path.join(ROOT, "mods.toml"), "--out", str(tmp_path),
                   "--release-json", os.path.join(ROOT, "tests/fixtures/scarred-steel-v0.2.0.json")])
    assert rc == 0 and (tmp_path / "scarred-steel/v0.2.0/changelog.bbcode").exists()

def test_cli_dry_run_writes_nothing(tmp_path, capsys):
    cli.main(["draft", "scarred-steel", "--dry-run", "--config", os.path.join(ROOT, "mods.toml"), "--out", str(tmp_path),
              "--release-json", os.path.join(ROOT, "tests/fixtures/scarred-steel-v0.2.0.json")])
    assert "===== scarred-steel/v0.2.0/post-x.txt" in capsys.readouterr().out and not list(tmp_path.iterdir())

def _poll(tmp_path, rels, dry=False):
    cfg = tmp_path / "mods.toml"; cfg.write_text('[mods.m]\nname = "M"\n')
    a = cli.main.__globals__["argparse"].Namespace(config=str(cfg), out=str(tmp_path / "d"), dry_run=dry, print=False, db=str(tmp_path / "s.db"))
    return cli.cmd_poll(a, fetch=lambda repo: rels)

def rel(i): return {"id": i, "tag": f"v{i}", "name": "", "body": "- fix", "url": f"https://g/{i}", "assets": []}

def test_poll_seeds_then_drafts_new(tmp_path):
    _poll(tmp_path, [rel(1)])
    assert not (tmp_path / "d").exists()  # first run: silent seed
    _poll(tmp_path, [rel(2), rel(1)])
    assert (tmp_path / "d/m/v2").exists() and not (tmp_path / "d/m/v1").exists()
    _poll(tmp_path, [rel(2), rel(1)])  # nothing new, nothing re-drafted
    assert len(list((tmp_path / "d/m").iterdir())) == 1

def test_poll_fetch_error_continues(tmp_path, capsys):
    cfg = tmp_path / "mods.toml"; cfg.write_text('[mods.m]\nname = "M"\n')
    import argparse
    a = argparse.Namespace(config=str(cfg), out=str(tmp_path / "d"), dry_run=False, print=False, db=str(tmp_path / "s.db"))
    def boom(repo): raise RuntimeError("down")
    assert cli.cmd_poll(a, fetch=boom) == 0 and "down" in capsys.readouterr().err

def test_cli_requires_tag():
    with pytest.raises(SystemExit):
        cli.main(["draft", "scarred-steel"])
