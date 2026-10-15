import json, os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from modbot import config, github

@pytest.fixture
def mods():
    return config.load(os.path.join(ROOT, "mods.toml"))

def fixture(name):
    with open(os.path.join(ROOT, "tests", "fixtures", name), encoding="utf-8") as f:
        return github.normalize(json.load(f))

@pytest.fixture
def ss_rel():
    return fixture("scarred-steel-v0.2.0.json")

@pytest.fixture
def cqm_rel():
    return fixture("company-quartermaster-v0.2.1.json")
