# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Write the blind-grading page for a round from its outputs-blind.md alone; blind-key.json is never read.

  grading_page.py ROUND_DIR OUT_HTML

Publish OUT_HTML as an artifact with the db capability. The page saves each pair to the collection
`grades` as document <pair id> = {A: {rel, waste, form, memo}, B: {...}, better, updatedAt}, which
`blind_round.py record` turns back into user-grades.txt. Fenced blocks give every wide character two
cells, as a terminal does, so answers keep their alignment; diff fences color added and removed lines.
"""

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "grading-page.html"
PAIR_HEAD = re.compile(r"^# (\d\d) · (\S+)\n질문: (.+)$", re.M)
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+|$)(.*)$")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def cellify(text: str) -> str:
    out = []
    for ch in text:
        glyph = html.escape(ch, quote=False)
        if ord(ch) < 128:
            out.append(glyph)
        elif unicodedata.east_asian_width(ch) in ("W", "F"):
            out.append(f'<span class="c2"><i>{glyph}</i></span>')
        else:
            out.append(f'<span class="c1">{glyph}</span>')
    return "".join(out)


def diff_line(line: str) -> str:
    """Color a diff line the way a terminal does: added, removed, or hunk header."""
    if line.startswith("+") and not line.startswith("+++"):
        return " add"
    if line.startswith("-") and not line.startswith("---"):
        return " del"
    return " hunk" if line.startswith("@@") else ""


def inline(text: str) -> str:
    """Render code spans, backslash escapes, links, and emphasis; everything else is escaped text."""
    kept = []

    def keep(rendered: str) -> str:
        kept.append(rendered)
        return f"\x00{len(kept) - 1}\x00"

    text = re.sub(r"(`+)(.+?)(?<!`)\1(?!`)", lambda m: keep(f"<code>{html.escape(m[2].strip(), quote=False)}</code>"), text)
    text = re.sub(r"\\([!-/:-@\[-`{-~])", lambda m: keep(html.escape(m[1], quote=False)), text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: f'<a href="{html.escape(m[2])}">{m[1]}</a>', text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", flanked("strong"), text)
    text = re.sub(r"(?<![\w*])__(?=\S)(.+?)(?<=\S)__(?![\w*])", flanked("strong"), text)
    text = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", flanked("em"), text)
    text = re.sub(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])", flanked("em"), text)
    text = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", flanked("del"), text)
    return re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m[1])], text)


def flanked(tag: str):
    """Wrap a delimiter run only where CommonMark would: punctuation just inside it needs space or punctuation outside."""
    def punct(ch: str) -> bool:
        return not ch.isalnum() and not ch.isspace()

    def wrap(m: re.Match) -> str:
        before = m.string[m.start() - 1] if m.start() else " "
        after = m.string[m.end()] if m.end() < len(m.string) else " "
        opens = not punct(m[1][0]) or before.isspace() or punct(before)
        closes = not punct(m[1][-1]) or after.isspace() or punct(after)
        return f"<{tag}>{m[1]}</{tag}>" if opens and closes else m[0]
    return wrap


def indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def starts_block(lines: list[str], i: int) -> bool:
    line = lines[i]
    return bool(FENCE.match(line) or HEADING.match(line) or RULE.match(line) or LIST_ITEM.match(line)
                or line.lstrip().startswith(">") or is_table(lines, i))


def is_table(lines: list[str], i: int) -> bool:
    return lines[i].lstrip().startswith("|") and i + 1 < len(lines) and bool(TABLE_RULE.match(lines[i + 1]))


def cells(row: str) -> list[str]:
    row = row.strip().removeprefix("|")
    row = row[:-1] if row.endswith("|") and not row.endswith("\\|") else row
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", row)]


def table(lines: list[str], i: int) -> tuple[str, int]:
    aligns = []
    for rule in cells(lines[i + 1]):
        aligns.append("center" if rule.startswith(":") and rule.endswith(":") else
                      "right" if rule.endswith(":") else "left")
    style = lambda n: f' style="text-align:{aligns[n]}"' if n < len(aligns) and aligns[n] != "left" else ""
    head = "".join(f"<th{style(n)}>{inline(c)}</th>" for n, c in enumerate(cells(lines[i])))
    rows, i = [], i + 2
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        rows.append("<tr>" + "".join(f"<td{style(n)}>{inline(c)}</td>" for n, c in enumerate(cells(lines[i]))) + "</tr>")
        i += 1
    return f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>', i


def list_block(lines: list[str], i: int) -> tuple[str, int]:
    first = LIST_ITEM.match(lines[i])
    base, ordered = len(first[1]), first[2][0].isdigit()
    items = []
    while i < len(lines):
        m = LIST_ITEM.match(lines[i])
        if not m or len(m[1]) != base or m[2][0].isdigit() != ordered:
            break
        content = len(m[1]) + len(m[2]) + max(len(m[3]), 1)
        body, i = [m[4]], i + 1
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                j = i
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and indent(lines[j]) >= content:
                    body += [""] * (j - i)
                    i = j
                    continue
                break
            if indent(line) >= content or (LIST_ITEM.match(line) and indent(line) > base):
                body.append(line[min(indent(line), content):])
            elif starts_block(lines, i):
                break
            else:
                body.append(line.strip())
            i += 1
        items.append(blocks(body))
        j = i
        while j < len(lines) and not lines[j].strip():
            j += 1
        sibling = j < len(lines) and (m := LIST_ITEM.match(lines[j])) and len(m[1]) == base
        if not sibling:
            break
        i = j
    rendered = []
    for parts in items:
        if parts and parts[0].startswith("<p>"):
            parts = [parts[0][3:-4], *parts[1:]]
        rendered.append("<li>" + "".join(parts) + "</li>")
    start = int(first[2][:-1]) if ordered else 1
    tag = "ol" if ordered else "ul"
    attr = f' start="{start}"' if ordered and start != 1 else ""
    return f"<{tag}{attr}>{''.join(rendered)}</{tag}>", i


def blocks(lines: list[str]) -> list[str]:
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if m := FENCE.match(line):
            lead, marker, info = m.groups()
            close = re.compile(rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*$")
            body, i = [], i + 1
            while i < len(lines) and not close.match(lines[i]):
                body.append(lines[i][len(lead):] if lines[i].startswith(lead) else lines[i].lstrip())
                i += 1
            i += 1
            lang = html.escape(info.strip().split(" ")[0])
            tag = f'<span class="lang">{lang}</span>' if lang else ""
            if lang.lower() in ("diff", "patch"):
                code = "".join(f'<span class="dl{diff_line(line)}">{cellify(line)}</span>' for line in body)
                out.append(f'<div class="fence diff">{tag}<pre><code>{code}</code></pre></div>')
            else:
                out.append(f'<div class="fence">{tag}<pre><code>{cellify(chr(10).join(body))}</code></pre></div>')
        elif not line.strip():
            i += 1
        elif m := HEADING.match(line):
            level = len(m[1])
            out.append(f"<h{level}>{inline(m[2])}</h{level}>")
            i += 1
        elif RULE.match(line):
            out.append("<hr>")
            i += 1
        elif is_table(lines, i):
            rendered, i = table(lines, i)
            out.append(rendered)
        elif LIST_ITEM.match(line):
            rendered, i = list_block(lines, i)
            out.append(rendered)
        elif line.lstrip().startswith(">"):
            quoted = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quoted.append(re.sub(r"^\s*> ?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + "".join(blocks(quoted)) + "</blockquote>")
        else:
            para = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not starts_block(lines, i):
                para.append(lines[i])
                i += 1
            last = len(para) - 1
            text = "\n".join(inline(p.strip().rstrip("\\").rstrip()) + ("<br>" if n < last and p.endswith(("  ", "\\")) else "")
                             for n, p in enumerate(para))
            out.append(f"<p>{text}</p>")
    return out


def markdown(text: str) -> str:
    return "\n".join(blocks(text.split("\n")))


def read_pack(path: Path) -> tuple[str, list[dict]]:
    sections = re.split(r"^---$", path.read_text(), flags=re.M)
    intro = "\n".join(line for line in sections[0].strip().splitlines() if not line.startswith("# ")).strip()
    pairs = []
    for section in sections[1:]:
        head = PAIR_HEAD.search(section)
        if not head:
            raise SystemExit(f"{path}: a section has no '# NN · case' heading and '질문:' line")
        pid, case, question = head.groups()
        answers = {}
        for side in "AB":
            m = re.search(rf"┏━+ {pid}{side} ━+┓\n(.*?)\n┗━+ {pid}{side} 끝 ━+┛", section, re.S)
            if not m:
                raise SystemExit(f"{path}: answer {pid}{side} is missing")
            answers[side] = m[1].strip()
        pairs.append({"id": pid, "case": case, "question": question, "answers": answers})
    if not pairs:
        raise SystemExit(f"{path}: no pairs")
    return intro, pairs


def chips(name: str, values: list[str], label: str, extra: str = "") -> str:
    items = "".join(
        f'<label class="chip"><input type="radio" name="{name}" value="{html.escape(v)}"><span>{html.escape(v)}</span></label>'
        for v in values
    )
    return (f'<div class="field {extra}" role="radiogroup" aria-label="{label}"><span class="flabel">{label}</span>'
            f'<div class="chips">{items}</div></div>')


def section(pair: dict) -> str:
    pid, cells_html = pair["id"], []
    for side in "AB":
        key = pid + side
        cells_html.append(
            f'<article class="answer" style="grid-area:ans{side}" aria-label="답변 {key}">'
            f'<header class="ahead"><span class="tag">{key}</span></header>'
            f'<div class="md">{markdown(pair["answers"][side])}</div></article>'
        )
        cells_html.append(
            f'<div class="grades" style="grid-area:grd{side}">'
            f'<span class="tag small">{key}</span>'
            + chips(f"{key}-rel", ["O", "△", "X"], "관계")
            + chips(f"{key}-waste", ["0", "1", "2"], "낭비")
            + chips(f"{key}-form", ["O", "X"], "형태")
            + f'<div class="field memo"><label class="flabel" for="{key}-memo">메모</label>'
            f'<input type="text" id="{key}-memo" data-memo="{key}" autocomplete="off" placeholder="한 줄 의견 (선택)"></div>'
            "</div>"
        )
    return (
        f'<section class="pair" id="p{pid}">'
        f'<header class="phead"><span class="pnum">{pid}</span>'
        f'<div class="pmeta"><p class="question">{html.escape(pair["question"])}</p>'
        f'<p class="case">{html.escape(pair["case"])}</p></div>'
        f'<span class="state" data-state-for="{pid}">미채점</span></header>'
        f'<div class="spread">{"".join(cells_html)}</div>'
        f'<div class="verdict">{chips(f"{pid}-better", ["A", "같음", "B"], "더 나은 답변", "verdict-field")}</div>'
        "</section>"
    )


def script_json(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def page(round_name: str, intro: str, pairs: list[dict]) -> str:
    fills = {
        "{{ROUND}}": html.escape(round_name),
        "{{COUNT}}": str(len(pairs)),
        "{{INTRO}}": markdown(intro),
        "{{NAV}}": "".join(f'<a class="navchip" href="#p{p["id"]}" data-nav="{p["id"]}">{p["id"]}</a>' for p in pairs),
        "{{SECTIONS}}": "\n".join(section(p) for p in pairs),
        "{{PAIRS}}": script_json([p["id"] for p in pairs]),
        "{{STORE_KEY}}": script_json(f"blind-grade:{round_name}"),
    }
    return re.sub(r"\{\{[A-Z_]+\}\}", lambda m: fills[m[0]], TEMPLATE.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("round_dir", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    intro, pairs = read_pack(args.round_dir / "outputs-blind.md")
    args.out.write_text(page(args.round_dir.resolve().name, intro, pairs))
    print(f"wrote {len(pairs)} pairs to {args.out}")


if __name__ == "__main__":
    main()
