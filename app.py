import os
from pathlib import Path
from datetime import datetime

import streamlit as st


# --- Embedded builder code ---

import os
from rembg import remove

os.makedirs("uploads", exist_ok=True)
os.makedirs("assets", exist_ok=True)

def make_transparent_logo(uploaded_file):
    original_path = os.path.join("uploads", uploaded_file.name)

    with open(original_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    output_path = os.path.join("assets", f"{uploaded_file.name}_transparent.png")

    with open(original_path, "rb") as f:
        input_bytes = f.read()

    output_bytes = remove(input_bytes)

    with open(output_path, "wb") as f:
        f.write(output_bytes)

    return output_path

"""
================================================================================
HPS Security Policy Migration Builder — Final Version
================================================================================
Purpose:
    Rebuild a migrated policy into the HPS template with stronger template fidelity.

What this version fixes:
    - Gray banner with centered logo image
    - Single integrated top table (banner + metadata) for cleaner border flow
    - Larger, vertically merged "Applicable To" label box
    - Dynamic logo support via logo_path parameter
    - Revision history accepts tuples OR dicts
    - Cleaner footer handling
    - More stable section layout

Usage:
    1. Fill POLICY_DATA at the bottom of this file.
    2. Update DEFAULT_LOGO_PATH if desired.
    3. Run: python hps_policy_migration_builder_final.py
    4. Output .docx is saved to the current directory.
================================================================================
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os


# ── Default assets ─────────────────────────────────────────────────────────────
DEFAULT_LOGO_PATH = r"/mnt/data/a_logo_image_in_a_digital_format_features_wipro_h.png"

# ── Color constants ────────────────────────────────────────────────────────────
GRAY_LOGO = "BFBFBF"
GRAY_LABEL = "D9D9D9"
GRAY_SUBHDR = "BFBFBF"
GRAY_SECTION = "D9D9D9"
WHITE = "FFFFFF"
BLACK = "000000"
WIPRO_RED = "C00000"
WIPRO_TEAL = "17375E"
FOOTER_GRAY = "555555"


# ── Low-level helpers ──────────────────────────────────────────────────────────
def hex_to_rgb(hex_str: str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def styled_run(
    para,
    text,
    bold=False,
    italic=False,
    color_hex=BLACK,
    size_pt=9.5,
    font="Arial",
    underline=False,
):
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.underline = underline
    run.font.name = font
    run.font.size = Pt(size_pt)
    r, g, b = hex_to_rgb(color_hex)
    run.font.color.rgb = RGBColor(r, g, b)
    return run


def remove_children(parent, tag_name: str):
    for old in parent.findall(qn(tag_name)):
        parent.remove(old)


def set_paragraph_spacing(para, before=0, after=0, line=None):
    pPr = para._p.get_or_add_pPr()
    remove_children(pPr, "w:spacing")
    spc = OxmlElement("w:spacing")
    spc.set(qn("w:before"), str(before))
    spc.set(qn("w:after"), str(after))
    if line is not None:
        spc.set(qn("w:line"), str(line))
        spc.set(qn("w:lineRule"), "auto")
    pPr.append(spc)


def set_paragraph_keep_with_next(para, enabled=True):
    pPr = para._p.get_or_add_pPr()
    remove_children(pPr, "w:keepNext")
    if enabled:
        el = OxmlElement("w:keepNext")
        pPr.append(el)


def set_paragraph_keep_lines(para, enabled=True):
    pPr = para._p.get_or_add_pPr()
    remove_children(pPr, "w:keepLines")
    if enabled:
        el = OxmlElement("w:keepLines")
        pPr.append(el)


def set_cell_shading(cell, fill_hex):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    remove_children(tcPr, "w:shd")
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex.upper())
    tcPr.append(shd)


def set_cell_borders(cell, color="000000", size=4):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    remove_children(tcPr, "w:tcBorders")
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tcPr.append(borders)


def set_cell_margins(cell, top=60, bottom=60, left=80, right=80):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    remove_children(tcPr, "w:tcMar")
    mar = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def set_cell_valign(cell, align=WD_ALIGN_VERTICAL.CENTER):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    remove_children(tcPr, "w:vAlign")
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center" if align == WD_ALIGN_VERTICAL.CENTER else "top")
    tcPr.append(vAlign)


def set_row_height(row, height_twips, exact=False):
    trPr = row._tr.get_or_add_trPr()
    remove_children(trPr, "w:trHeight")
    trH = OxmlElement("w:trHeight")
    trH.set(qn("w:val"), str(int(height_twips)))
    trH.set(qn("w:hRule"), "exact" if exact else "atLeast")
    trPr.append(trH)


def prevent_row_break_across_pages(row):
    trPr = row._tr.get_or_add_trPr()
    remove_children(trPr, "w:cantSplit")
    el = OxmlElement("w:cantSplit")
    trPr.append(el)


def style_cell(cell, shade=WHITE, border_color="000000", border_size=4, margins=True):
    set_cell_shading(cell, shade)
    set_cell_borders(cell, color=border_color, size=border_size)
    if margins:
        set_cell_margins(cell)
    return cell


def set_col_width(cell, twips):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    remove_children(tcPr, "w:tcW")
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"), str(twips))
    tcW.set(qn("w:type"), "dxa")
    tcPr.append(tcW)


def new_table(doc, rows, cols, col_widths_twips, total_width_twips):
    tbl = doc.add_table(rows=rows, cols=cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl.style = "Table Grid"

    tblPr = tbl._tbl.tblPr
    remove_children(tblPr, "w:tblW")
    remove_children(tblPr, "w:tblLayout")

    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(total_width_twips))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)

    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    tblGrid = tbl._tbl.find(qn("w:tblGrid"))
    if tblGrid is None:
        tblGrid = OxmlElement("w:tblGrid")
        tbl._tbl.insert(0, tblGrid)

    for old in tblGrid.findall(qn("w:gridCol")):
        tblGrid.remove(old)

    for w in col_widths_twips:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        tblGrid.append(gc)

    for row in tbl.rows:
        for i, cell in enumerate(row.cells):
            set_col_width(cell, col_widths_twips[i if i < len(col_widths_twips) else -1])

    return tbl


def label_paragraph(cell, text, size_pt=9.0):
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_paragraph_spacing(para, 30, 30)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            para.add_run("\n")
        styled_run(para, line, bold=True, size_pt=size_pt)
    return para


def value_paragraph(cell, text, size_pt=9.5, alignment=WD_ALIGN_PARAGRAPH.LEFT, bold=False):
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = alignment
    set_paragraph_spacing(para, 30, 30)
    styled_run(para, text or "", size_pt=size_pt, bold=bold)
    return para


def center_bold_paragraph(cell, text, size_pt=9.5, color_hex=BLACK):
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(para, 40, 40)
    styled_run(para, text, bold=True, size_pt=size_pt, color_hex=color_hex)
    return para


def section_heading_paragraph(cell, text, size_pt=10.0):
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_paragraph_spacing(para, 30, 30)
    set_paragraph_keep_with_next(para, True)
    styled_run(para, text, bold=True, size_pt=size_pt)
    return para


def add_content_para(
    cell,
    text,
    before=40,
    after=30,
    size_pt=10.0,
    bold_prefix=None,
    italic_prefix=None,
):
    para = cell.add_paragraph()
    set_paragraph_spacing(para, before, after)
    set_paragraph_keep_lines(para, True)
    if italic_prefix:
        styled_run(para, italic_prefix[0], bold=True, italic=True, size_pt=size_pt)
        styled_run(para, italic_prefix[1], size_pt=size_pt)
    elif bold_prefix:
        styled_run(para, bold_prefix[0], bold=True, size_pt=size_pt)
        styled_run(para, bold_prefix[1], size_pt=size_pt)
    else:
        styled_run(para, text, size_pt=size_pt)
    return para


def add_heading_para(cell, text, size_pt=10.0):
    para = cell.add_paragraph()
    set_paragraph_spacing(para, 60, 30)
    set_paragraph_keep_with_next(para, True)
    styled_run(para, text, bold=True, underline=True, size_pt=size_pt)
    return para


def add_empty_para(cell, before=0, after=0):
    para = cell.add_paragraph()
    set_paragraph_spacing(para, before, after)
    return para


def add_bullet_paragraph(cell, text, is_sub=False):
    para = cell.add_paragraph()
    set_paragraph_spacing(para, 30, 30)
    pPr = para._p.get_or_add_pPr()
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), str(900 if is_sub else 540))
    ind.set(qn("w:hanging"), "260")
    pPr.append(ind)
    bullet_char = "\u25E6" if is_sub else "\u2022"
    styled_run(para, f"{bullet_char}  {text}", size_pt=10)
    return para


def apply_semicolon_breaks(cell, text, size_pt=10.0):
    segments = [seg.strip() for seg in text.split(";") if seg.strip()]
    for i, seg in enumerate(segments):
        suffix = ";" if i < len(segments) - 1 else ""
        para = cell.add_paragraph()
        set_paragraph_spacing(para, 30, 30)
        styled_run(para, seg + suffix, size_pt=size_pt)


def normalize_revision_entry(entry):
    if isinstance(entry, dict):
        return (
            str(entry.get("date", "")),
            str(entry.get("version", "")),
            str(entry.get("updated_by", "")),
            str(entry.get("description", "")),
        )
    if isinstance(entry, (list, tuple)) and len(entry) >= 4:
        return tuple(str(x) for x in entry[:4])
    raise ValueError(f"Unsupported revision history entry format: {entry!r}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def build_policy_document(data: dict, output_path: str, logo_path: str | None = None):
    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.9)
    section.footer_distance = Inches(0.3)

    doc.styles["Normal"].paragraph_format.space_before = Pt(0)
    doc.styles["Normal"].paragraph_format.space_after = Pt(0)

    PAGE_W = int((8.5 - 0.75 - 0.75) * 1440)
    GAP = 36

    def gap_para(after=0):
        p = doc.add_paragraph()
        set_paragraph_spacing(p, GAP, after)

    logo_path = logo_path or DEFAULT_LOGO_PATH

    # Column widths for top area
    META_L = int(PAGE_W * 0.18)
    META_MID = int(PAGE_W * 0.32)
    META_RL = int(PAGE_W * 0.18)
    META_RV = PAGE_W - META_L - META_MID - META_RL

    # ──────────────────────────────────────────────────────────────────────
    # TOP TABLE — Gray banner + metadata integrated
    # ──────────────────────────────────────────────────────────────────────
    top = new_table(doc, 12, 4, [META_L, META_MID, META_RL, META_RV], PAGE_W)

    # Banner row
    banner_cell = top.rows[0].cells[0]
    banner_cell.merge(top.rows[0].cells[3])
    style_cell(banner_cell, GRAY_LOGO)
    set_cell_margins(banner_cell, top=25, bottom=25, left=20, right=20)
    set_cell_valign(banner_cell, WD_ALIGN_VERTICAL.CENTER)
    set_row_height(top.rows[0], 400, exact=True)
    prevent_row_break_across_pages(top.rows[0])

    banner_cell.text = ""
    banner_para = banner_cell.paragraphs[0]
    banner_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(banner_para, 0, 0)

    if logo_path and os.path.exists(logo_path):
        run = banner_para.add_run()
        run.add_picture(logo_path, width=Inches(2.55))
    else:
        styled_run(banner_para, "wipro", bold=True, color_hex=WIPRO_RED, size_pt=22)
        styled_run(banner_para, ":", bold=True, color_hex=WIPRO_RED, size_pt=22)
        styled_run(banner_para, "  healthplan services", color_hex=WIPRO_TEAL, size_pt=20)

    def meta_row(row_idx, left_label, left_val, right_label=None, right_val=None, merge_right=False):
        row = top.rows[row_idx]
        c0, c1, c2, c3 = row.cells

        style_cell(c0, GRAY_LABEL)
        set_col_width(c0, META_L)
        label_paragraph(c0, left_label)

        if merge_right:
            c1.merge(c3)
            style_cell(c1, WHITE)
            set_col_width(c1, META_MID + META_RL + META_RV)
            value_paragraph(c1, left_val)
        else:
            style_cell(c1, WHITE)
            set_col_width(c1, META_MID)
            value_paragraph(c1, left_val)

            style_cell(c2, GRAY_LABEL)
            set_col_width(c2, META_RL)
            label_paragraph(c2, right_label or "")

            style_cell(c3, WHITE)
            set_col_width(c3, META_RV)
            value_paragraph(c3, right_val or "")

        prevent_row_break_across_pages(row)

    meta_row(1, "Policy Name", data["policy_name"], merge_right=True)
    meta_row(2, "Policy Number", data["policy_number"], "Version Number", data["version"])

    row3 = top.rows[3]
    style_cell(row3.cells[0], GRAY_LABEL)
    set_col_width(row3.cells[0], META_L)
    row3.cells[0].text = ""
    style_cell(row3.cells[1], WHITE)
    set_col_width(row3.cells[1], META_MID)
    row3.cells[1].text = ""
    style_cell(row3.cells[2], GRAY_LABEL)
    set_col_width(row3.cells[2], META_RL)
    label_paragraph(row3.cells[2], "GRC ID Number")
    style_cell(row3.cells[3], WHITE)
    set_col_width(row3.cells[3], META_RV)
    value_paragraph(row3.cells[3], data.get("grc_id", ""))
    prevent_row_break_across_pages(row3)

    meta_row(4, "Supersedes Policy", data.get("supersedes", ""), "Effective Date", data["effective_date"])
    meta_row(5, "Last Reviewed Date", data["last_reviewed"], "Last Revised Date", data["last_revised"])
    meta_row(6, "Policy Custodian\nName(s)", data.get("custodians", ""), merge_right=True)

    row7 = top.rows[7]
    row7.cells[0].merge(row7.cells[1])
    row7.cells[2].merge(row7.cells[3])
    style_cell(row7.cells[0], GRAY_SUBHDR)
    style_cell(row7.cells[2], GRAY_SUBHDR)
    center_bold_paragraph(row7.cells[0], "Policy Owner")
    center_bold_paragraph(row7.cells[2], "Policy Approver")
    prevent_row_break_across_pages(row7)

    meta_row(8, "Name", data["owner_name"], "Name", data["approver_name"])
    meta_row(9, "Title", data["owner_title"], "Title", data["approver_title"])

    row10 = top.rows[10]
    for i, (lbl, w) in enumerate(
        [("Signature", META_L), (None, META_MID), ("Signature", META_RL), (None, META_RV)]
    ):
        c = row10.cells[i]
        style_cell(c, GRAY_LABEL if lbl else WHITE)
        set_col_width(c, w)
        if lbl:
            label_paragraph(c, lbl)
        else:
            c.text = ""
    set_row_height(row10, 480)
    prevent_row_break_across_pages(row10)

    meta_row(11, "Date Signed", data.get("date_signed", ""), "Date Approved", data.get("date_approved", ""))

    gap_para()

    # ──────────────────────────────────────────────────────────────────────
    # TABLE 2 — Applicable To
    # ──────────────────────────────────────────────────────────────────────
    applicable = data.get("applicable_to", {})
    policy_types = data.get("policy_types", {})
    lob = data.get("line_of_business", {})

    app_lines = [
        ("HealthPlan Services, Inc.", applicable.get("hps_inc", True)),
        ("HealthPlan Services Insurance Agency, LLC", applicable.get("agency", True)),
        ("Policy Types", None),
        ("Corporate", applicable.get("corporate", True)),
        ("Government Affairs Review Required", applicable.get("govt_affairs", False)),
        ("Legal Review Required", applicable.get("legal_review", False)),
        ("Line of Business (LOB)", None),
        ("All LOBs", lob.get("all_lobs", True)),
        (f"Specific LOB {lob.get('specific_lob', '[INSERT HERE]')}", lob.get("specific_lob_checked", False)),
    ]

    APP_L = int(PAGE_W * 0.28)
    APP_R = PAGE_W - APP_L
    t2 = new_table(doc, len(app_lines), 2, [APP_L, APP_R], PAGE_W)

    # Merge left label column vertically
    left_anchor = t2.rows[0].cells[0]
    for i in range(1, len(app_lines)):
        left_anchor = left_anchor.merge(t2.rows[i].cells[0])

    style_cell(left_anchor, GRAY_LABEL)
    set_cell_margins(left_anchor, top=160, bottom=160, left=120, right=120)
    set_cell_valign(left_anchor, WD_ALIGN_VERTICAL.CENTER)
    left_anchor.text = ""
    lp = left_anchor.paragraphs[0]
    lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(lp, 0, 0)
    styled_run(lp, "Applicable To:\n(select all that apply)", bold=True, size_pt=10.0)

    for i, (label, checked) in enumerate(app_lines):
        right = t2.rows[i].cells[1]
        is_subhdr = checked is None
        shade = GRAY_SUBHDR if is_subhdr else WHITE
        style_cell(right, shade)
        set_cell_margins(right, top=70, bottom=70, left=90, right=90)
        set_col_width(right, APP_R)
        set_cell_valign(right, WD_ALIGN_VERTICAL.CENTER)
        right.text = ""
        p = right.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        set_paragraph_spacing(p, 20, 20)
        if is_subhdr:
            styled_run(p, label, bold=True, size_pt=9.5)
        else:
            mark = "☑" if checked else "☐"
            styled_run(p, f"{label}  {mark}", size_pt=9.25)
        prevent_row_break_across_pages(t2.rows[i])

    gap_para()

    # ──────────────────────────────────────────────────────────────────────
    # Section table helper
    # ──────────────────────────────────────────────────────────────────────
    def section_table(heading, content_builder):
        tbl = new_table(doc, 2, 1, [PAGE_W], PAGE_W)

        hdr = tbl.rows[0].cells[0]
        style_cell(hdr, GRAY_SECTION)
        set_cell_margins(hdr, top=45, bottom=45, left=80, right=80)
        section_heading_paragraph(hdr, heading)
        prevent_row_break_across_pages(tbl.rows[0])

        cnt = tbl.rows[1].cells[0]
        style_cell(cnt, WHITE)
        set_cell_margins(cnt, top=60, bottom=80, left=120, right=120)
        cnt.text = ""
        content_builder(cnt)
        prevent_row_break_across_pages(tbl.rows[1])

        return tbl

    def fill_purpose(cell):
        for line in data["purpose"].strip().split("\n"):
            line = line.strip()
            if line:
                add_content_para(cell, line)
            else:
                add_empty_para(cell)

    section_table("Purpose and Scope", fill_purpose)
    gap_para()

    def fill_definitions(cell):
        for term, definition in data.get("definitions", {}).items():
            para = cell.add_paragraph()
            set_paragraph_spacing(para, 30, 30)
            styled_run(para, "\u2013  ", size_pt=10)
            styled_run(para, f"{term}:  ", bold=True, size_pt=10)
            styled_run(para, definition, size_pt=10)

    section_table("Definitions", fill_definitions)
    gap_para()

    def fill_policy_statement(cell):
        stmt = data.get("policy_statement", "")
        if " that " in stmt:
            idx = stmt.index(" that ") + 6
            prefix, rest = stmt[:idx], stmt[idx:]
        else:
            prefix, rest = "", stmt
        para = cell.add_paragraph()
        set_paragraph_spacing(para, 40, 40)
        if prefix:
            styled_run(para, prefix, bold=True, italic=True, size_pt=10)
        styled_run(para, rest, size_pt=10)

    section_table("Policy Statement", fill_policy_statement)
    gap_para()

    def fill_procedures(cell):
        for item in data.get("procedures", []):
            kind = item.get("type", "para")
            text = item.get("text", "")

            if kind == "para":
                if ";" in text:
                    apply_semicolon_breaks(cell, text)
                else:
                    add_content_para(cell, text)
            elif kind == "heading":
                add_heading_para(cell, text)
            elif kind == "bullet":
                add_bullet_paragraph(cell, text, is_sub=False)
            elif kind == "sub-bullet":
                add_bullet_paragraph(cell, text, is_sub=True)
            elif kind == "bold_intro":
                add_content_para(cell, "", bold_prefix=(item["bold"], item["rest"]))
            elif kind == "bold_intro_semi":
                para = cell.add_paragraph()
                set_paragraph_spacing(para, 40, 30)
                styled_run(para, item["bold"], bold=True, size_pt=10)
                segs = [seg.strip() for seg in item["rest"].split(";") if seg.strip()]
                for i, seg in enumerate(segs):
                    suffix = ";" if i < len(segs) - 1 else ""
                    if i == 0:
                        styled_run(para, seg + suffix, size_pt=10)
                    else:
                        p2 = cell.add_paragraph()
                        set_paragraph_spacing(p2, 0, 30)
                        styled_run(p2, seg + suffix, size_pt=10)
            elif kind == "empty":
                add_empty_para(cell)

    section_table("Procedures", fill_procedures)
    gap_para()

    def fill_related(cell):
        for policy in data.get("related_policies", []):
            add_content_para(cell, policy)

    section_table("Related Policies or Standard Operating Procedures", fill_related)
    gap_para()

    def fill_citations(cell):
        for citation in data.get("citations", []):
            if ";" in citation:
                apply_semicolon_breaks(cell, citation)
            else:
                add_content_para(cell, citation)

    section_table("Citations/References", fill_citations)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────
    # Revision History
    # ──────────────────────────────────────────────────────────────────────
    C1 = int(PAGE_W * 0.12)
    C2 = int(PAGE_W * 0.13)
    C3 = int(PAGE_W * 0.20)
    C4 = PAGE_W - C1 - C2 - C3

    rev_entries = [normalize_revision_entry(x) for x in data.get("revision_history", [])]
    total_rows = 2 + len(rev_entries)
    t9 = new_table(doc, total_rows, 4, [C1, C2, C3, C4], PAGE_W)

    heading_cell = t9.rows[0].cells[0]
    heading_cell.merge(t9.rows[0].cells[3])
    style_cell(heading_cell, GRAY_SECTION)
    set_cell_margins(heading_cell, top=45, bottom=45, left=80, right=80)
    section_heading_paragraph(heading_cell, "Revision History")
    prevent_row_break_across_pages(t9.rows[0])

    for col_idx, (hdr_text, width) in enumerate(
        [("Date", C1), ("Version Number", C2), ("Updated By", C3), ("Description of Update", C4)]
    ):
        hc = t9.rows[1].cells[col_idx]
        style_cell(hc, GRAY_LABEL)
        set_col_width(hc, width)
        value_paragraph(hc, hdr_text, size_pt=9.0, alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    prevent_row_break_across_pages(t9.rows[1])

    for ri, entry in enumerate(rev_entries, start=2):
        row = t9.rows[ri]
        for ci, (txt, width) in enumerate(zip(entry, [C1, C2, C3, C4])):
            rc = row.cells[ci]
            style_cell(rc, WHITE)
            set_col_width(rc, width)
            rc.text = ""
            lines = str(txt).split("\n")
            for li, line in enumerate(lines):
                para = rc.paragraphs[0] if li == 0 else rc.add_paragraph()
                set_paragraph_spacing(para, 20, 20)
                styled_run(para, line.strip(), size_pt=9.0)
        prevent_row_break_across_pages(row)

    # ──────────────────────────────────────────────────────────────────────
    # Footer
    # ──────────────────────────────────────────────────────────────────────
    footer = section.footer
    footer_tbl = footer.add_table(rows=2, cols=1, width=Inches(7.0))
    footer_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r in footer_tbl.rows:
        prevent_row_break_across_pages(r)
        c = r.cells[0]
        c.text = ""
        set_cell_borders(c, color=WHITE, size=0)
        set_cell_shading(c, WHITE)
        set_cell_margins(c, top=0, bottom=0, left=0, right=0)
        set_cell_valign(c, WD_ALIGN_VERTICAL.CENTER)

    fp1 = footer_tbl.rows[0].cells[0].paragraphs[0]
    fp1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(fp1, 0, 0)
    styled_run(
        fp1,
        "Confidential & Proprietary \u00A9 HealthPlan Services Inc., including its subsidiaries and affiliates",
        size_pt=7.5,
        color_hex=FOOTER_GRAY,
    )

    fp2 = footer_tbl.rows[1].cells[0].paragraphs[0]
    fp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(fp2, 0, 0)
    styled_run(
        fp2,
        f"{data['policy_number']}  |  {data['policy_name']}  |  {data['version']}",
        size_pt=7.5,
        color_hex=FOOTER_GRAY,
    )

    doc.save(output_path)
    print(f"\n✅ Saved: {output_path}\n")


# ══════════════════════════════════════════════════════════════════════════════
# POLICY DATA — Sample content
# ══════════════════════════════════════════════════════════════════════════════
POLICY_DATA = {
    "policy_name": "Mobile Device Management in the Workplace",
    "policy_number": "SEC-P020",
    "version": "V10.0",
    "grc_id": "",
    "supersedes": "",
    "effective_date": "8/31/2014",
    "last_reviewed": "09/26/2025",
    "last_revised": "09/26/2025",
    "custodians": "Chelsea Sanchez, Alexis Taylor",
    "owner_name": "Dan Cutler",
    "owner_title": "Dir., Security Engineering",
    "approver_name": "Sam Sweilem",
    "approver_title": "CIO",
    "date_signed": "",
    "date_approved": "09/30/2025",
    "applicable_to": {
        "hps_inc": True,
        "agency": True,
        "corporate": True,
        "govt_affairs": False,
        "legal_review": False,
    },
    "policy_types": {
        "carrier_specific": True,
        "cross_carrier": True,
        "global": True,
        "on_off_hix": False,
    },
    "line_of_business": {
        "all_lobs": True,
        "specific_lob": "[INSERT HERE]",
        "specific_lob_checked": False,
    },
    "purpose": """
This policy establishes safeguards for mobile devices to protect information from unauthorized disclosure, use, modification, and loss. Mobile devices, while increasingly prolific and useful, represent a significant risk to information and data security if the appropriate controls and procedures are not applied, and can serve as a conduit for unauthorized access to the organization's information resources. This can lead to data leakage and system compromise.

This policy's scope includes securing both WHPS-provided and personally owned mobile devices present on WHPS premises and connected to the WHPS network. A mobile device, for this policy's purpose, refers to any portable wireless device small enough to be used while held in the hand. This covers smartphones, tablets and other mobile devices but does not include laptops and mini terminals, such as iGel, WYSE Clients, etc.
""",
    "definitions": {
        "iGel": "a Linux-based operating system optimized for secure, scalable delivery of virtual desktops and cloud workspaces.",
        "WYSE": "is an application that manages the use of Wyse thin clients. This includes managing users, jobs, and more.",
        "Jail-broken": "modify (a smartphone or other electronic device) to remove restrictions imposed by the manufacturer or operator, e.g. to allow the installation of unauthorized software.",
    },
    "policy_statement": (
        "It is the policy of Wipro HealthPlan Holdings (WHPS) "
        "that Phones, tablets, and other mobile devices containing Restricted or Confidential "
        "and Proprietary data must be adequately protected from unauthorized access through "
        "appropriate access controls, encryption, theft deterrents and screen locks."
    ),
    "procedures": [
        {"type": "para", "text": "All mobile devices that connect to the corporate network must be registered with IT (Information Technology) and be managed centrally by IT using its mobile device security solution."},
        {"type": "empty"},
        {"type": "para", "text": "Mobile devices—whether personally-owned or corporate-owned—may not access email, calendar, or any other data resources directly from native device applications, unless these data can be monitored and managed by the IT mobile device security solution. Most commonly, this means that ActiveSync may not be used to access network resources without the use of the mobile device security solution."},
        {"type": "empty"},
        {"type": "heading", "text": "Expectation of Privacy:"},
        {"type": "bold_intro_semi", "bold": "Corporate-provided devices – ", "rest": "WHPS retains its right to monitor the activities of its workforce members using WHPS computing equipment and electronic networks during normally expected work hours. This includes the right to monitor email, calendars, and other data transmissions to and from Company-provided mobile devices; the right to restrict what applications (or “apps”) are downloaded and installed in the devices; and other asset and security management activities not necessarily listed here. WHPS does not track or monitor the physical location of workforce members using the GPS Location features of mobile devices."},
        {"type": "bold_intro", "bold": "Personally-owned devices – ", "rest": "WHPS shall manage personally-owned devices to the extent required to protect WHPS business data permitted to be stored or processed on personal devices. It does not monitor, restrict, or control full use of the device, its features, any app installation, or any other function that does not impact the security of Company data on the device."},
        {"type": "empty"},
        {"type": "para", "text": "Mobile devices belonging to employees must also have been authorized by the direct manager as permitted to connect to the network, have a documented job-related need, or they are exempted in writing by the Chief Information Officer."},
        {"type": "empty"},
        {"type": "heading", "text": "Technical Requirements for all mobile devices:"},
        {"type": "bullet", "text": "Devices must store all user-saved passwords, if any are stored, in an encrypted password store."},
        {"type": "bullet", "text": "Devices must be password or PIN protected using the features of the device to prevent unauthorized access."},
        {"type": "bullet", "text": "The device must lock itself if idle for three minutes and require a password or PIN to unlock the device."},
        {"type": "bullet", "text": "Devices must be configured with a security PIN code. This PIN must not be the same as any other credentials used within the organization."},
        {"type": "bullet", "text": "Devices must be encrypted in accordance with WHPS compliance standards. Mobile devices that store sensitive information must use a Federal Information Process Standard (FIPS 140-2) encryption method to protect data from unauthorized disclosure."},
        {"type": "empty"},
        {"type": "heading", "text": "User Requirements – All devices:"},
        {"type": "bullet", "text": "Users must report all lost or stolen WHPS devices or mobile devices that connect to the corporate network to the IT Help Desk immediately."},
        {"type": "bullet", "text": "If a user suspects that unauthorized access to company data has taken place through a mobile device, the user must report the incident to IT Help Desk immediately."},
        {"type": "para", "text": "The employee's device is remotely wiped if:"},
        {"type": "sub-bullet", "text": "The device is lost."},
        {"type": "sub-bullet", "text": "The employee terminates his or her employment."},
        {"type": "para", "text": "IT detects:"},
        {"type": "sub-bullet", "text": "A data or policy breach."},
        {"type": "sub-bullet", "text": "A virus or similar threat to the security of the company's data and technology infrastructure."},
        {"type": "empty"},
        {"type": "bullet", "text": "Devices must not be “jail-broken” or have any software/firmware installed which is designed to gain access to functionality not intended to be exposed to the user."},
        {"type": "bullet", "text": "Users must not load pirated software or illegal content onto their devices."},
        {"type": "bullet", "text": "Devices must be kept up to date with the manufacturer or network provided patches. As a minimum, patches should be checked weekly and applied at least once a month."},
        {"type": "bullet", "text": "The employee must always use their devices ethically and adhere to the company’s acceptable use policies."},
        {"type": "empty"},
        {"type": "heading", "text": "WHPS Owned Devices:"},
        {"type": "bullet", "text": "Users must only load data essential to their role onto corporate owned mobile device(s)."},
        {"type": "bullet", "text": "Users must never download or access cardholder data from WHPS devices."},
        {"type": "empty"},
        {"type": "heading", "text": "Personally Owned Devices:"},
        {"type": "bullet", "text": "Employees are responsible for notifying their mobile carrier immediately upon loss of a device."},
        {"type": "bullet", "text": "While WHPS administers every precaution to prevent the employee’s personal data from being lost, in the event it must remote wipe a device, it is the employee’s responsibility to take additional precautions, such as backing up email, contacts, among others."},
        {"type": "bullet", "text": "Users must be cautious about the merging of personal and work email accounts on their devices. Users must take particular care to ensure company data is only sent through the corporate email system. If a user suspects that company data has been sent from a personal email account, either in body text or as an attachment, they must notify WHPS IT Service Desk immediately."},
        {"type": "bullet", "text": "The employee is personally liable for all costs associated with his or her device."},
        {"type": "bullet", "text": "The employee assumes full liability for risks including, but not limited to, the partial or complete loss of company and personal data due to an operating system crash, errors, bugs, viruses, malware, and/or other software or hardware failures, or programming errors that render the device unusable."},
        {"type": "bullet", "text": "Users must never download or access cardholder data from personally owned devices."},
    ],
    "related_policies": [
        "SEC-P001 Information Security Governing Policy",
        "SEC-C002 Information Security Charter",
        "SEC-P008 Password Policy",
    ],
    "citations": [
        "45 CFR 164.308(a)(5)(ii)(D);",
        "CoBIT 5.0: DSS05.02, 05.04;",
        "HiTrust v9.3: 01.x, 01.y, 10.k;",
        "PCI DSS v3.2: 2.1, 8.5.2, 8.5.3, 8.5.8, 8.5.10-12;",
        "(State of Mass.) 201 CMR 17.04(1)(b).",
        "ISO/IEC 27001:2022 Information Security, Cybersecurity and Privacy Protection: A.6.2.1, A.8.1.3.",
    ],
    "revision_history": [
        ("12/4/2013", "v0.1 s/b 1.0", "Kate Mullin", "Initial Draft"),
        ("4/18/2014", "v0.2 s/b 2.0", "Jay Schwitzgebel", "Adapted for mobile devices only (no laptops) and prep for Good Technologies rollout"),
        ("6/13/2014", "v1.0 s/b 3.0", "Kelly Oliver", "Updated to include PCI DSS 2.0 requirements"),
        ("7/29/2014", "v1.0 s/b 3.0", "Ray Johnson", "Updated grammar and style guidelines."),
        ("8/26/2015", "v2.0 s/b 4.0", "Jay Schwitzgebel", "Format updates;\nsome updates to enterprise mobile device security solution"),
        ("8/10/2017", "v3.0 s/b 4.0", "Jay Schwitzgebel", "Updated header info;\nadded SOP;\nadded ISO control citations"),
        ("8/30/2019", "v4.0 s/b 5.0", "David Folden", "Updates from HPH to WHPS throughout policy;\nupdated HPH logo to WHPS/Wipro logo;\nannual review"),
        ("9/10/2020", "V4.0 s/b 6.0", "Andrea Cooper", "Updated References and citations;\nUpdated version in header and footer"),
        ("9/10/2020", "V4.0 s/b 6.0", "Kelly Latinka", "Updated Approver to Dennis Prysner. Minor Maintenance."),
        ("10/18/2021", "V7.0", "Victor Beary", "No material changes made to content;\nupdated new CISO name to Sachin Sheth"),
        ("10/20/2021", "V5.0 s/b 7.0", "Alexis Taylor", "Changed reviewed and revised dates, change version number, updated the new CIO to Sam Sweilem, and updated the name and version number in the footer."),
        ("6/28/2023", "V8.0", "Dan Cutler", "Updated policy with HiTrust language"),
        ("6/28/2023", "V8.0", "Alexis Taylor", "Annual Review 2023: Moved to new template, changed review/revise dates, change approver, update footer;\ngrammar, formatting corrections, added definitions"),
        ("4/24/2024", "V9.0", "Brian Word", "Annual Review. Updated Grammar issues."),
        ("8/7/2025", "V10.0", "Dan Cutler", "Annual review and approval.\nRelated Policy Section changes:\nChanged SEC-P002 to SEC-C002.\nRemoved SEC-S020.1."),
        {"date": "09/26/2025", "version": "V10.0", "updated_by": "Chelsea Sanchez", "description": "Annual Compliance Review complete."},
    ],
}


if __name__ == "__main__":
    out_name = (
        f"{POLICY_DATA['policy_number']} "
        f"{POLICY_DATA['policy_name']} "
        f"{POLICY_DATA['version']}-FINAL.docx"
    )
    build_policy_document(POLICY_DATA, out_name, logo_path=DEFAULT_LOGO_PATH)


# --- End embedded builder code ---

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
ASSETS_DIR = BASE_DIR / "assets"

for d in (UPLOADS_DIR, OUTPUTS_DIR, ASSETS_DIR):
    d.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Midnight Policy Migration", layout="wide")


def save_uploaded_file(uploaded_file, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    file_path = destination_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


@st.cache_data(show_spinner=False)
def process_logo_bytes(file_bytes: bytes) -> bytes:
    if not REMBG_AVAILABLE:
        raise RuntimeError(
            "Background removal requires rembg. Install it with: pip install rembg"
        )
    return remove(file_bytes)


def create_processed_logo(uploaded_file) -> Path:
    original_path = save_uploaded_file(uploaded_file, UPLOADS_DIR)
    base_name = Path(uploaded_file.name).stem
    processed_path = ASSETS_DIR / f"{base_name}_transparent.png"

    input_bytes = original_path.read_bytes()
    output_bytes = process_logo_bytes(input_bytes)
    processed_path.write_bytes(output_bytes)
    return processed_path


st.title("Midnight Policy Migration")
st.caption("Upload policy files, process a logo, and generate the final Word document.")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Migration Inputs")
    source_file = st.file_uploader(
        "Upload Source Policy",
        type=["docx", "doc", "pdf", "txt"],
        key="source_policy",
    )
    template_file = st.file_uploader(
        "Upload Target Template",
        type=["docx"],
        key="target_template",
    )

    st.subheader("Branding")
    logo_file = st.file_uploader(
        "Upload Logo",
        type=["png", "jpg", "jpeg", "webp"],
        key="logo_upload",
        help="PNG works best. JPG/JPEG/WEBP can be converted to a transparent PNG.",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        process_clicked = st.button("Process Logo", use_container_width=True)
    with col2:
        clear_clicked = st.button("Clear Logo", use_container_width=True)

    if clear_clicked:
        st.session_state.pop("processed_logo_path", None)
        st.session_state.pop("processed_logo_name", None)
        st.session_state.pop("original_logo_path", None)
        st.success("Logo selection cleared.")

    if process_clicked:
        if logo_file is None:
            st.warning("Upload a logo first.")
        else:
            try:
                original_path = save_uploaded_file(logo_file, UPLOADS_DIR)
                st.session_state["original_logo_path"] = str(original_path)

                if logo_file.type == "image/png":
                    processed_path = ASSETS_DIR / f"{Path(logo_file.name).stem}_transparent.png"
                    processed_path.write_bytes(original_path.read_bytes())
                else:
                    processed_path = create_processed_logo(logo_file)

                st.session_state["processed_logo_path"] = str(processed_path)
                st.session_state["processed_logo_name"] = processed_path.name
                st.success("Logo processed and ready for the template header.")
            except Exception as exc:
                st.error(f"Logo processing failed: {exc}")

with right:
    st.subheader("Logo Preview")
    processed_logo_path = st.session_state.get("processed_logo_path")
    if processed_logo_path and Path(processed_logo_path).exists():
        st.image(processed_logo_path, caption=Path(processed_logo_path).name, use_container_width=True)
    elif Path(DEFAULT_LOGO_PATH).exists():
        st.info("No processed logo yet. Default logo is currently active.")
        st.image(DEFAULT_LOGO_PATH, caption="Default Logo", use_container_width=True)
    else:
        st.info("Upload a logo to preview it here.")

    st.subheader("Current Files")
    st.write(f"Source policy: {source_file.name if source_file else 'Not uploaded'}")
    st.write(f"Template: {template_file.name if template_file else 'Not uploaded'}")
    st.write(
        f"Active logo: {st.session_state.get('processed_logo_name', Path(DEFAULT_LOGO_PATH).name)}"
    )

st.divider()

st.subheader("Generate Document")
output_default_name = (
    f"{POLICY_DATA['policy_number']} {POLICY_DATA['policy_name']} {POLICY_DATA['version']}-NEW.docx"
)
output_name = st.text_input("Output filename", value=output_default_name)

if st.button("Run Migration", type="primary", use_container_width=True):
    try:
        active_logo_path = st.session_state.get("processed_logo_path", DEFAULT_LOGO_PATH)
        output_path = OUTPUTS_DIR / output_name

        # Keep uploaded files on disk for downstream logic even if this builder does not use them yet.
        if source_file is not None:
            save_uploaded_file(source_file, UPLOADS_DIR)
        if template_file is not None:
            save_uploaded_file(template_file, UPLOADS_DIR)

        build_policy_document(
            data=POLICY_DATA,
            output_path=str(output_path),
            logo_path=str(active_logo_path) if active_logo_path else None,
        )

        st.success(f"Document generated: {output_path.name}")
        with open(output_path, "rb") as f:
            st.download_button(
                "Download Final Document",
                data=f,
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    except Exception as exc:
        st.error(f"Document generation failed: {exc}")

with st.expander("Notes"):
    st.markdown(
        """
- Put `app.py` in the same folder as `hps_policy_migration_builder_final.py`.
- If JPG/JPEG/WEBP background removal does not work yet, install `rembg` first.
- The builder uses the processed logo in the top gray banner.
- Source policy and template uploads are saved and ready for future extraction/template logic.
        """
    )
