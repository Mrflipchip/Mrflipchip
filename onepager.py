from __future__ import annotations
import os
import re
import sys
import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "assets", "aflathrive_banks_onepager_template.pdf")
OUT_DIR = os.path.join(HERE, "onepagers")
SEP = "×"


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "bank"


def _find_title_span(page):
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line.get("spans", []):
                if "AFLATHRIVE" in s["text"] and SEP in s["text"]:
                    return s
    raise RuntimeError("Could not find the 'AFLATHRIVE ×' title in the template PDF.")


def _bold_font(doc, page):
    for f in page.get_fonts(full=True):
        if "IBMPlexSans-Bold" in f[3]:
            return fitz.Font(fontbuffer=doc.extract_font(f[0])[3])
    raise RuntimeError("Embedded title font (IBM Plex Sans Bold) not found in template.")


def make_onepager(bank_name, out_dir=None):
    bank_name = (bank_name or "").strip()
    if not bank_name:
        raise ValueError("bank_name is required")
    if not os.path.exists(TEMPLATE):
        raise FileNotFoundError(f"Template PDF not found: {TEMPLATE}")

    out_dir = out_dir or OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{_slug(bank_name)}.pdf")

    doc = fitz.open(TEMPLATE)
    page = doc[0]
    span = _find_title_span(page)
    font = _bold_font(doc, page)

    prefix = span["text"].split(SEP, 1)[0] + SEP + " "
    new_text = prefix + bank_name

    missing = [c for c in new_text if c != " " and font.has_glyph(ord(c)) == 0]
    if missing:
        raise ValueError(f"Title font has no glyph for: {missing!r}")

    size = span["size"]
    color_int = span["color"]
    color = ((color_int >> 16 & 255) / 255, (color_int >> 8 & 255) / 255, (color_int & 255) / 255)
    x0, y0, x1, y1 = span["bbox"]
    right_edge = x1
    baseline_y = span["origin"][1]

    natural = font.text_length(span["text"], size)
    actual = x1 - x0
    tc = (actual - natural) / max(len(span["text"]), 1)

    page.add_redact_annot(fitz.Rect(x0 - 2, y0 - 3, x1 + 2, y1 + 3), fill=(1, 1, 1))
    page.apply_redactions()

    width = font.text_length(new_text, size) + tc * len(new_text)
    x = right_edge - width
    tw = fitz.TextWriter(page.rect, color=color)
    for ch in new_text:
        tw.append((x, baseline_y), ch, font=font, fontsize=size)
        x += font.glyph_advance(ord(ch)) * size + tc
    tw.write_text(page)

    doc.save(out_path, garbage=4, deflate=True)
    doc.close()
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python3 onepager.py "<Bank Name>"', file=sys.stderr)
        sys.exit(1)
    print(make_onepager(sys.argv[1]))
