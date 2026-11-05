import re

OPT = re.compile(r"^\s*\(?([A-Fa-f])[.)]\s+(\S.*)$")
MARK = re.compile(r"(?:(?<=\s)|^)\(?([A-Fa-f])[.)]\s+")
QSTART = re.compile(r"^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,3})\s*[.):\-]\s+(\S.*)$", re.I)
ANS = re.compile(r"^\s*(?:correct\s+)?(?:answer|ans|correct)\s*(?:option|is)?\s*[:\-=]?\s*\(?([A-Fa-f])(?![A-Za-z])", re.I)
EXPL = re.compile(r"^\s*(explanation|solution|rationale|note|hint)\b", re.I)
KEYHEAD = re.compile(r"^\s*(?:answer\s*key|answers|answer\s*sheet)\s*:?\s*$", re.I)
KEYITEM = re.compile(r"(\d{1,3})\s*[.):\-]?\s*\(?([A-Fa-f])\)?(?![A-Za-z0-9])")
PAGE = re.compile(r"^(?:page\s*)?\d+\s*(?:of\s*\d+)?$", re.I)


def _split_inline(line):
    ms = list(MARK.finditer(line))
    if len(ms) < 2 or not OPT.match(line):
        return [line]
    parts = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(line)
        parts.append(f"{m.group(1)}) {line[m.end():end].strip()}")
    return parts


def parse_questions(text):
    text = text.replace("\r", "\n").replace("\u00a0", " ")
    lines = text.split("\n")
    key = {}
    body = lines
    for i, ln in enumerate(lines):
        if KEYHEAD.match(ln):
            body = lines[:i]
            key_text = " ".join(lines[i + 1:])
            key = {int(n): ord(l.upper()) - 65 for n, l in KEYITEM.findall(key_text)}
            break

    blocks, cur = [], None
    for ln in body:
        s = ln.strip()
        if not s or PAGE.match(s):
            continue
        m = QSTART.match(ln)
        if m:
            cur = {"num": int(m.group(1)), "q": [m.group(2).strip()], "opts": [], "ans": None, "skip": False}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        a = ANS.match(ln)
        if a:
            cur["ans"] = ord(a.group(1).upper()) - 65
            continue
        if cur["skip"]:
            continue
        if EXPL.match(ln):
            cur["skip"] = True
            continue
        if OPT.match(ln):
            for part in _split_inline(ln):
                cur["opts"].append(OPT.match(part).group(2).strip())
            continue
        if cur["opts"]:
            cur["opts"][-1] += " " + s
        else:
            cur["q"].append(s)

    # "1. B" lines with no heading look like tiny questions: treat them as answer-key entries
    real = []
    for b in blocks:
        t = " ".join(b["q"]).strip()
        if not b["opts"] and re.fullmatch(r"[A-Fa-f]", t):
            key.setdefault(b["num"], ord(t.upper()) - 65)
        else:
            real.append(b)

    out, errors = [], []
    for b in real:
        n = b["num"]
        text_q = " ".join(b["q"]).strip()
        correct = b["ans"] if b["ans"] is not None else key.get(n)
        if len(b["opts"]) < 2:
            errors.append(f"Q{n}: found fewer than 2 options (options must start with A) B) C) D) on their own lines)")
        elif correct is None:
            errors.append(f"Q{n}: no answer found (add 'Answer: B' under the question, or an Answer Key at the end)")
        elif correct >= len(b["opts"]):
            errors.append(f"Q{n}: the answer letter does not match any option")
        else:
            out.append({"text": text_q, "options": b["opts"], "correct": correct})
    return out, errors