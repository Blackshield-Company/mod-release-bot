"""Markdown -> Nexus Mods BBCode, via markdown-it-py tokens and a small hand-written renderer."""
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark").enable("strikethrough").enable("table")
HEADING_SIZE = {"h1": 5, "h2": 4, "h3": 4, "h4": 3, "h5": 3, "h6": 3}


def _inline(tokens):
    out = []
    for t in tokens:
        ty = t.type
        if ty == "text":
            out.append(t.content)
        elif ty == "code_inline":
            out.append(f"[font=Courier New]{t.content}[/font]")
        elif ty in ("softbreak",):
            out.append(" ")
        elif ty == "hardbreak":
            out.append("\n")
        elif ty == "strong_open":
            out.append("[b]")
        elif ty == "strong_close":
            out.append("[/b]")
        elif ty == "em_open":
            out.append("[i]")
        elif ty == "em_close":
            out.append("[/i]")
        elif ty == "s_open":
            out.append("[s]")
        elif ty == "s_close":
            out.append("[/s]")
        elif ty == "link_open":
            out.append(f"[url={t.attrGet('href')}]")
        elif ty == "link_close":
            out.append("[/url]")
        elif ty == "image":
            out.append(f"[img]{t.attrGet('src')}[/img]")
        elif ty in ("html_inline",):
            out.append(t.content)
    return "".join(out)


def md_to_bbcode(md: str) -> str:
    tokens = _md.parse(md or "")
    out = []
    list_depth = 0
    in_table = False
    row = []
    for t in tokens:
        ty = t.type
        if ty == "heading_open":
            out.append(f"[size={HEADING_SIZE[t.tag]}][b]")
        elif ty == "heading_close":
            out.append("[/b][/size]\n")
        elif ty == "paragraph_open":
            pass
        elif ty == "paragraph_close":
            if not t.hidden:
                out.append("\n" if list_depth else "\n\n")
        elif ty == "inline":
            if in_table:
                row.append(_inline(t.children or []).strip())
            else:
                out.append(_inline(t.children or []))
        elif ty == "bullet_list_open":
            if list_depth and out and not out[-1].endswith("\n"):
                out.append("\n")
            out.append("[list]\n")
            list_depth += 1
        elif ty == "ordered_list_open":
            if list_depth and out and not out[-1].endswith("\n"):
                out.append("\n")
            out.append("[list=1]\n")
            list_depth += 1
        elif ty in ("bullet_list_close", "ordered_list_close"):
            list_depth -= 1
            out.append("[/list]\n" + ("" if list_depth else "\n"))
        elif ty == "list_item_open":
            out.append("[*]")
        elif ty == "list_item_close":
            if out and not out[-1].endswith("\n"):
                out.append("\n")
        elif ty in ("fence", "code_block"):
            out.append(f"[code]\n{t.content.rstrip()}\n[/code]\n\n")
        elif ty == "blockquote_open":
            out.append("[quote]")
        elif ty == "blockquote_close":
            out[-1] = out[-1].rstrip("\n")
            out.append("[/quote]\n\n")
        elif ty == "hr":
            out.append("[line]\n\n")
        elif ty == "html_block":
            out.append(t.content)
        # Nexus BBCode has no reliable table tag: render rows as " | "-joined lines in a [code] block.
        elif ty == "table_open":
            in_table = True
            out.append("[code]\n")
        elif ty == "tr_close":
            out.append(" | ".join(row) + "\n")
            row = []
        elif ty == "table_close":
            in_table = False
            out.append("[/code]\n\n")
    return "".join(out).strip() + "\n"
