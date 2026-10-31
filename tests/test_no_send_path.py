"""Guard rail: the package must never gain a way to post, upload or send."""
import pathlib, re
PKG = pathlib.Path(__file__).resolve().parent.parent / "modbot"
BANNED = [r"\bimport requests\b", r"\bfrom requests\b", r"\burllib\b", r"\bhttp\.client\b", r"\bhttpx\b", r"\baiohttp\b",
          r"\bsocket\b", r"\bsmtplib\b", r"--method\",\s*\"(POST|PUT|PATCH|DELETE)", r"discord\.com", r"api\.(x|twitter)\.com",
          r"oauth\.reddit|reddit\.com/api", r"api\.nexusmods\.com", r"\"-X\"|\"--field\"|\"-f\"|\"-F\""]

def test_no_network_write_code():
    for f in PKG.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".j2"):
            src = f.read_text()
            for pat in BANNED:
                assert not re.search(pat, src), f"{f.name} matches banned pattern {pat}"

def test_gh_only_used_with_get():
    src = (PKG / "github.py").read_text()
    assert src.count('"gh", "api"') == 1 and '"--method", "GET"' in src

def test_git_only_used_with_log():
    # Commit mode reads a local clone; it must never commit, tag, push or otherwise change it.
    users = [f.name for f in PKG.rglob("*.py") if '"git"' in f.read_text()]
    assert users == ["commits.py"]
    src = (PKG / "commits.py").read_text()
    assert src.count('"git", "-C"') == 1 and '"git", "-C", repo_dir, "log"' in src
    assert not re.search(r"\b(push|fetch|commit|tag|reset|checkout|remote)\b\"", src)

def test_subprocess_only_in_readers():
    assert sorted(f.name for f in PKG.rglob("*.py") if "subprocess" in f.read_text()) == ["commits.py", "github.py"]
