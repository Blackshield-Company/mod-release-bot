from modbot import drafts, config
from modbot.drafts import x_len, X_LIMIT

def test_version():
    assert drafts.version("v0.2.0") == "0.2.0"
    assert drafts.version("release-1") == "release-1"

def test_clean_notes_strips_boilerplate(cqm_rel):
    n = drafts.clean_notes(cqm_rel["body"])
    assert "sha256" not in n and "ko-fi" not in n.lower() and "Donations" not in n
    assert "Brynja" in n

def test_build_files(mods, ss_rel):
    d = drafts.build(config.find(mods, "scarred-steel"), ss_rel)
    assert set(d) == {"changelog.bbcode", "nexus-description.bbcode", "post-x.txt", "post-reddit.md"}
    assert "SCS_WearHints" in d["post-x.txt"]
    assert "0.2.0" in d["post-x.txt"] and ss_rel["url"] in d["post-x.txt"]
    assert "Latest version: 0.2.0" in d["nexus-description.bbcode"]

def test_x_limit_respected(mods, cqm_rel):
    for rel in (cqm_rel, dict(cqm_rel, body="word " * 2000)):
        x = drafts.build(config.find(mods, "company-quartermaster"), rel)["post-x.txt"]
        assert x_len(x) <= X_LIMIT, x

def test_x_drops_tags_when_name_is_huge(cqm_rel):
    m = config.Mod(repo="o/r", name="N" * 230, hashtags=["Skyrim", "SkyrimMods"])
    x = drafts.build(m, cqm_rel)["post-x.txt"]
    assert x_len(x) <= X_LIMIT and "#Skyrim" not in x

def test_url_counts_23():
    assert x_len("a https://example.com/" + "p" * 100) == 2 + 23

def test_nexus_link_preferred(mods, ss_rel):
    m = config.find(mods, "steel-oath")
    d = drafts.build(m, dict(ss_rel, url="https://github.com/x"))
    assert "nexusmods.com/skyrimspecialedition/mods/194208" in d["post-x.txt"]
    assert "Nexus Mods: https://www.nexusmods.com" in d["post-reddit.md"]

def test_reddit(mods, cqm_rel):
    r = drafts.build(config.find(mods, "company-quartermaster"), cqm_rel)["post-reddit.md"]
    assert r.startswith("Title: Company Quartermaster 0.2.1 released") and "r/skyrimmods" in r
    assert len(r.splitlines()[0]) <= 7 + drafts.REDDIT_TITLE_LIMIT

def test_empty_body(mods, ss_rel):
    d = drafts.build(config.find(mods, "scarred-steel"), dict(ss_rel, body=""))
    assert "See GitHub release" in d["changelog.bbcode"]

def test_long_changelog_capped(mods, ss_rel):
    d = drafts.build(config.find(mods, "scarred-steel"), dict(ss_rel, body="- item line\n" * 2000))
    assert len(d["changelog.bbcode"]) <= drafts.NEXUS_CHANGELOG_LIMIT and "Full notes:" in d["changelog.bbcode"]

def test_write(tmp_path, mods, ss_rel):
    m = config.find(mods, "scarred-steel")
    p = drafts.write(str(tmp_path), m, ss_rel, drafts.build(m, ss_rel))
    assert p.endswith("scarred-steel/v0.2.0")
    assert (tmp_path / "scarred-steel" / "v0.2.0" / "post-x.txt").read_text().startswith("Scarred Steel")

def test_example_is_current(mods, ss_rel):
    import os
    ex = os.path.join(os.path.dirname(__file__), "..", "examples", "scarred-steel", "v0.2.0")
    d = drafts.build(config.find(mods, "scarred-steel"), ss_rel)
    for name, text in d.items():
        assert open(os.path.join(ex, name), encoding="utf-8").read() == text
