from modbot.bbcode import md_to_bbcode as b

def test_headings():
    assert b("## Fixed") == "[size=4][b]Fixed[/b][/size]\n"
    assert b("# Big").startswith("[size=5][b]Big")

def test_bullets():
    assert b("- a\n- b") == "[list]\n[*]a\n[*]b\n[/list]\n"

def test_ordered():
    assert b("1. one\n2. two") == "[list=1]\n[*]one\n[*]two\n[/list]\n"

def test_nested_list():
    out = b("- a\n  - a1\n  - a2\n- b")
    assert out == "[list]\n[*]a\n[list]\n[*]a1\n[*]a2\n[/list]\n[*]b\n[/list]\n"

def test_links_and_inline():
    out = b("See [GitHub](https://x.test/r) and **bold**, *it*, ~~old~~ `code`")
    assert "[url=https://x.test/r]GitHub[/url]" in out
    assert "[b]bold[/b]" in out and "[i]it[/i]" in out and "[s]old[/s]" in out
    assert "[font=Courier New]code[/font]" in out

def test_code_block():
    assert b("```\nset X to 1\n```") == "[code]\nset X to 1\n[/code]\n"

def test_quote_and_hr():
    out = b("> note\n\n---\n\nafter")
    assert "[quote]note[/quote]" in out and "[line]" in out and out.endswith("after\n")

def test_table_becomes_code():
    out = b("| a | b |\n|---|---|\n| 1 | 2 |")
    assert out == "[code]\na | b\n1 | 2\n[/code]\n"

def test_image():
    assert "[img]https://i.test/p.png[/img]" in b("![alt](https://i.test/p.png)")

def test_empty():
    assert b("") == "\n"

def test_matches_existing_nexus_style():
    # same tags the hand-written scarred_steel_bbcode.txt uses for sections and lists
    out = b("## Requirements\n- Skyrim SE")
    assert out.startswith("[size=4][b]Requirements[/b][/size]") and "[list]\n[*]Skyrim SE" in out
