"""
================================================================================
HPS Security Policy Migration Builder
================================================================================
Usage:
    1. Fill in the POLICY_DATA dictionary at the bottom of this file with
       content extracted from your source policy document.
    2. Run:  python hps_policy_migration_builder.py
    3. A completed .docx file will be saved to the current directory.

Notes:
    - All text values accept \\n for line breaks within a cell.
    - Semicolons in procedure text will auto-insert a line break after them.
    - Checkboxes: set True = ☑  /  False = ☐
    - Revision history rows are tuples: (date, version, updated_by, description)
================================================================================
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy
import os

# ── Color constants ────────────────────────────────────────────────────────────
GRAY_LOGO    = "BFBFBF"   # Wipro logo banner
GRAY_LABEL   = "D9D9D9"   # Metadata label cells
GRAY_SUBHDR  = "BFBFBF"   # Policy Owner/Approver bar, Policy Types/LOB headers
GRAY_SECTION = "D9D9D9"   # Section heading rows
WHITE        = "FFFFFF"
BLACK        = "000000"
WIPRO_RED    = "C00000"    # "wipro:" brand red
WIPRO_TEAL   = "17375E"   # "healthplan services" dark teal

# ── Low-level XML helpers ──────────────────────────────────────────────────────
def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def set_cell_shading(cell, fill_hex):
    """Apply background shading to a table cell."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  fill_hex.upper())
    # Remove any existing shd
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    tcPr.append(shd)

def set_cell_borders(cell, color="000000", size=4):
    """Apply uniform thin borders to a cell."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:tcBorders")):
        tcPr.remove(old)
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"),   "single")
        el.set(qn("w:sz"),    str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tcPr.append(borders)

def set_cell_margins(cell, top=60, bottom=60, left=80, right=80):
    """Set internal cell padding (in twentieths of a point)."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:tcMar")):
        tcPr.remove(old)
    mar = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"),    str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)

def set_row_height(row, height_twips, exact=False):
    """Set a fixed or minimum row height."""
    trPr = row._tr.get_or_add_trPr()
    for old in trPr.findall(qn("w:trHeight")):
        trPr.remove(old)
    trH = OxmlElement("w:trHeight")
    trH.set(qn("w:val"),      str(int(height_twips)))
    trH.set(qn("w:hRule"),    "exact" if exact else "atLeast")
    trPr.append(trH)

def merge_cells_horizontally(row, start_col, end_col):
    """Merge cells from start_col to end_col (inclusive) in a row."""
    cells = row.cells
    cells[start_col].merge(cells[end_col])
    return cells[start_col]

def set_cell_valign(cell, align=WD_ALIGN_VERTICAL.CENTER):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center" if align == WD_ALIGN_VERTICAL.CENTER else "top")
    for old in tcPr.findall(qn("w:vAlign")):
        tcPr.remove(old)
    tcPr.append(vAlign)

def set_paragraph_spacing(para, before=40, after=40):
    pPr  = para._p.get_or_add_pPr()
    spc  = OxmlElement("w:spacing")
    spc.set(qn("w:before"), str(before))
    spc.set(qn("w:after"),  str(after))
    for old in pPr.findall(qn("w:spacing")):
        pPr.remove(old)
    pPr.append(spc)

# ── Run helpers ────────────────────────────────────────────────────────────────
def styled_run(para, text, bold=False, italic=False, color_hex=BLACK,
               size_pt=9.5, font="Arial", underline=False):
    run = para.add_run(text)
    run.bold      = bold
    run.italic    = italic
    run.underline = underline
    run.font.name = font
    run.font.size = Pt(size_pt)
    r, g, b = hex_to_rgb(color_hex)
    run.font.color.rgb = RGBColor(r, g, b)
    return run

def label_paragraph(cell, text, size_pt=9.0):
    """Right-aligned bold paragraph in a label cell."""
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_paragraph_spacing(para, 40, 40)
    # Handle multi-line labels
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            para.add_run("\n")
        styled_run(para, line, bold=True, size_pt=size_pt)
    return para

def value_paragraph(cell, text, size_pt=9.5):
    """Left-aligned regular paragraph in a value cell."""
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_paragraph_spacing(para, 40, 40)
    styled_run(para, text or "", size_pt=size_pt)
    return para

def section_heading_paragraph(cell, text, size_pt=10.0):
    """Bold left-aligned section heading paragraph."""
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_paragraph_spacing(para, 60, 60)
    styled_run(para, text, bold=True, size_pt=size_pt)
    return para

def center_bold_paragraph(cell, text, size_pt=9.5, color_hex=BLACK):
    """Centered bold paragraph — used for Policy Owner/Approver bar."""
    cell.text = ""
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(para, 50, 50)
    styled_run(para, text, bold=True, size_pt=size_pt, color_hex=color_hex)
    return para

# ── Table setup ────────────────────────────────────────────────────────────────
def style_cell(cell, shade=WHITE, borders=True, margins=True,
               border_color="000000", border_size=4):
    set_cell_shading(cell, shade)
    if borders:
        set_cell_borders(cell, color=border_color, size=border_size)
    if margins:
        set_cell_margins(cell)
    return cell

def new_table(doc, rows, cols, col_widths_twips, total_width_twips):
    """Add a table with set column widths and full-page width."""
    tbl = doc.add_table(rows=rows, cols=cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl.style = "Table Grid"
    # Set total table width
    tblPr = tbl._tbl.tblPr
    tblW  = OxmlElement("w:tblW")
    tblW.set(qn("w:w"),    str(total_width_twips))
    tblW.set(qn("w:type"), "dxa")
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblPr.append(tblW)
    # Set column widths
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
    # Apply widths to each cell
    for row in tbl.rows:
        for i, cell in enumerate(row.cells):
            tc   = cell._tc
            tcPr = tc.get_or_add_tcPr()
            for old in tcPr.findall(qn("w:tcW")):
                tcPr.remove(old)
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:w"),    str(col_widths_twips[i] if i < len(col_widths_twips) else col_widths_twips[-1]))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)
    return tbl

def set_col_width(cell, twips):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:tcW")):
        tcPr.remove(old)
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"),    str(twips))
    tcW.set(qn("w:type"), "dxa")
    tcPr.append(tcW)

def add_bullet_paragraph(cell_or_doc, text, level=0, is_sub=False):
    """Add a bullet paragraph to a cell."""
    if hasattr(cell_or_doc, "add_paragraph"):
        para = cell_or_doc.add_paragraph()
    else:
        para = cell_or_doc.paragraphs[-1]._p.addnext(OxmlElement("w:p"))
    # For cells, just add as regular paragraph with a bullet character
    if hasattr(cell_or_doc, "_tc"):
        para = cell_or_doc.add_paragraph()
    set_paragraph_spacing(para, 40, 40)
    pPr  = para._p.get_or_add_pPr()
    ind  = OxmlElement("w:ind")
    indent = 900 if is_sub else 540
    ind.set(qn("w:left"),    str(indent))
    ind.set(qn("w:hanging"), "260")
    pPr.append(ind)
    bullet_char = "\u25E6" if is_sub else "\u2022"
    run = para.add_run(f"{bullet_char}  {text}")
    run.font.name = "Arial"
    run.font.size = Pt(10)
    return para

def add_content_para(cell, text, before=60, after=40, size_pt=10.0,
                     bold_prefix=None, italic_prefix=None):
    """
    Add a content paragraph to a cell.
    bold_prefix:   (prefix_text, rest_text) — prefix is bold
    italic_prefix: (prefix_text, rest_text) — prefix is bold+italic
    """
    para = cell.add_paragraph()
    set_paragraph_spacing(para, before, after)
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
    """Bold + underline heading paragraph inside a content cell."""
    para = cell.add_paragraph()
    set_paragraph_spacing(para, 100, 60)
    styled_run(para, text, bold=True, underline=True, size_pt=size_pt)
    return para

def add_empty_para(cell, before=0, after=0):
    para = cell.add_paragraph()
    set_paragraph_spacing(para, before, after)
    return para

def apply_semicolon_breaks(cell, text, size_pt=10.0):
    """Split text on semicolons, each segment on its own paragraph."""
    segments = text.split(";")
    for i, seg in enumerate(segments):
        seg = seg.strip()
        if not seg:
            continue
        suffix = ";" if i < len(segments) - 1 else ""
        para = cell.add_paragraph()
        set_paragraph_spacing(para, 40, 40)
        styled_run(para, seg + suffix, size_pt=size_pt)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def build_policy_document(data: dict, output_path: str):
    doc = Document()

    # Page setup: US Letter, 0.75" margins
    section = doc.sections[0]
    section.page_width  = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin   = Inches(0.75)
    section.right_margin  = Inches(0.75)
    section.top_margin    = Inches(0.75)
    section.bottom_margin = Inches(0.9)

    # Remove default paragraph spacing
    doc.styles["Normal"].paragraph_format.space_before = Pt(0)
    doc.styles["Normal"].paragraph_format.space_after  = Pt(0)

    PAGE_W = int((8.5 - 0.75 - 0.75) * 1440)   # ~10800 DXA at 0.75" margins
    GAP    = 80  # twips gap between tables

    def gap_para():
        p = doc.add_paragraph()
        set_paragraph_spacing(p, GAP, 0)

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 0 — Wipro Logo Banner
    # ──────────────────────────────────────────────────────────────────────────
    t0 = new_table(doc, 1, 1, [PAGE_W], PAGE_W)
    c  = t0.cell(0, 0)
    style_cell(c, GRAY_LOGO)
    set_cell_margins(c, top=160, bottom=160, left=120, right=120)
    c.text = ""
    banner = c.paragraphs[0]
    banner.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(banner, 0, 0)
    styled_run(banner, "wipro",  bold=True, color_hex=WIPRO_RED,  size_pt=22)
    styled_run(banner, ":",      bold=True, color_hex=WIPRO_RED,  size_pt=22)
    styled_run(banner, "  healthplan services",    color_hex=WIPRO_TEAL, size_pt=20)

    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 1 — Metadata
    # ──────────────────────────────────────────────────────────────────────────
    META_L  = int(PAGE_W * 0.18)   # label col
    META_MID= int(PAGE_W * 0.32)   # value col (left side)
    META_RL = int(PAGE_W * 0.18)   # right label col
    META_RV = PAGE_W - META_L - META_MID - META_RL  # right value col

    t1 = new_table(doc, 11, 4, [META_L, META_MID, META_RL, META_RV], PAGE_W)

    def meta_row(row_idx, left_label, left_val, right_label=None, right_val=None,
                 merge_right=False, shade_left_val=WHITE):
        row = t1.rows[row_idx]
        c0, c1, c2, c3 = row.cells

        # Left label
        style_cell(c0, GRAY_LABEL); set_col_width(c0, META_L)
        label_paragraph(c0, left_label)

        if merge_right:
            # Merge c1 + c2 + c3
            c1.merge(c3)
            style_cell(c1, WHITE); set_col_width(c1, META_MID + META_RL + META_RV)
            value_paragraph(c1, left_val)
        else:
            style_cell(c1, shade_left_val); set_col_width(c1, META_MID)
            value_paragraph(c1, left_val)
            style_cell(c2, GRAY_LABEL); set_col_width(c2, META_RL)
            label_paragraph(c2, right_label or "")
            style_cell(c3, WHITE); set_col_width(c3, META_RV)
            value_paragraph(c3, right_val or "")

    # Row 0: Policy Name (full width value)
    meta_row(0, "Policy Name", data["policy_name"], merge_right=True)
    # Row 1: Policy Number | Version Number
    meta_row(1, "Policy Number", data["policy_number"],
             "Version Number", data["version"])
    # Row 2: (blank label) | GRC ID Number
    row2 = t1.rows[2]
    style_cell(row2.cells[0], GRAY_LABEL); set_col_width(row2.cells[0], META_L)
    row2.cells[0].text = ""
    row2.cells[0].paragraphs[0].add_run("")
    style_cell(row2.cells[1], WHITE); set_col_width(row2.cells[1], META_MID)
    row2.cells[1].text = ""
    style_cell(row2.cells[2], GRAY_LABEL); set_col_width(row2.cells[2], META_RL)
    label_paragraph(row2.cells[2], "GRC ID Number")
    style_cell(row2.cells[3], WHITE); set_col_width(row2.cells[3], META_RV)
    value_paragraph(row2.cells[3], data.get("grc_id", ""))
    # Row 3: Supersedes | Effective Date
    meta_row(3, "Supersedes Policy", data.get("supersedes", ""),
             "Effective Date", data["effective_date"])
    # Row 4: Last Reviewed | Last Revised
    meta_row(4, "Last Reviewed Date", data["last_reviewed"],
             "Last Revised Date",  data["last_revised"])
    # Row 5: Policy Custodian (full width)
    meta_row(5, "Policy Custodian\nName(s)", data.get("custodians", "Chelsea Sanchez, Alexis Taylor"),
             merge_right=True)
    # Row 6: Policy Owner / Policy Approver sub-header bar
    row6 = t1.rows[6]
    row6.cells[0].merge(row6.cells[1])
    row6.cells[2].merge(row6.cells[3])
    style_cell(row6.cells[0], GRAY_SUBHDR)
    center_bold_paragraph(row6.cells[0], "Policy Owner")
    style_cell(row6.cells[2], GRAY_SUBHDR)
    center_bold_paragraph(row6.cells[2], "Policy Approver")
    # Row 7: Names
    meta_row(7, "Name", data["owner_name"], "Name", data["approver_name"])
    # Row 8: Titles
    meta_row(8, "Title", data["owner_title"], "Title", data["approver_title"])
    # Row 9: Signatures (taller row for wet-ink)
    row9 = t1.rows[9]
    for i, (lbl, w) in enumerate(
            [("Signature", META_L), (None, META_MID), ("Signature", META_RL), (None, META_RV)]):
        c = row9.cells[i]
        shade = GRAY_LABEL if lbl else WHITE
        style_cell(c, shade)
        set_col_width(c, w)
        if lbl:
            label_paragraph(c, lbl)
        else:
            c.text = ""
    set_row_height(row9, 500)
    # Row 10: Date Signed | Date Approved
    meta_row(10, "Date Signed", data.get("date_signed", ""),
             "Date Approved", data.get("date_approved", ""))

    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 2 — Applicable To (checkboxes)
    # ──────────────────────────────────────────────────────────────────────────
    APP_L = int(PAGE_W * 0.23)
    APP_R = PAGE_W - APP_L

    applicable = data.get("applicable_to", {})
    policy_types = data.get("policy_types", {})
    lob = data.get("line_of_business", {})

    # Build checkbox rows data
    chk_rows = []  # list of (right_col_text, right_shade, is_subhdr)
    chk_rows.append((f"HealthPlan Services, Inc.  {'☑' if applicable.get('hps_inc', True) else '☐'}", WHITE, False))
    chk_rows.append((f"HealthPlan Services Insurance Agency, LLC  {'☑' if applicable.get('agency', True) else '☐'}", WHITE, False))
    chk_rows.append(("Policy Types", GRAY_SUBHDR, True))
    chk_rows.append((f"Corporate  {'☑' if applicable.get('corporate', True) else '☐'}", WHITE, False))
    chk_rows.append((f"Government Affairs Review Required  {'☑' if applicable.get('govt_affairs', False) else '☐'}", WHITE, False))
    chk_rows.append((f"Legal Review Required  {'☑' if applicable.get('legal_review', False) else '☐'}", WHITE, False))
    chk_rows.append(("Line of Business (LOB)", GRAY_SUBHDR, True))
    chk_rows.append((f"All LOBs  {'☑' if lob.get('all_lobs', True) else '☐'}", WHITE, False))
    chk_rows.append((f"Specific LOB {lob.get('specific_lob', '[INSERT HERE]')}  {'☑' if lob.get('specific_lob_checked', False) else '☐'}", WHITE, False))

    # Policy Types sub-rows (right column, inside the policy types subhdr)
    pt_rows = []
    for pt_key, pt_label in [
        ("carrier_specific",  "Carrier Specific (Facing)"),
        ("cross_carrier",     "Cross-Carrier (Multiple/All)"),
        ("global",            "Global"),
        ("on_off_hix",        "ON/OFF HIX"),
    ]:
        checked = policy_types.get(pt_key, False)
        pt_rows.append(f"{'☑' if checked else '☐'}  {pt_label}")

    # We'll build the applicable to table as a simple 2-column layout
    # Label col spans all rows; right col has items
    total_rows = len(chk_rows)
    t2 = new_table(doc, total_rows, 2, [APP_L, APP_R], PAGE_W)

    # Style and fill the label column (first col, spanning all rows visually)
    first_label_done = False
    for i, (right_text, right_shade, is_subhdr) in enumerate(chk_rows):
        row  = t2.rows[i]
        cl   = row.cells[0]
        cr   = row.cells[1]

        # Left label cell
        style_cell(cl, GRAY_LABEL)
        set_col_width(cl, APP_L)
        if i == 0:
            cl.text = ""
            para = cl.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_paragraph_spacing(para, 60, 60)
            styled_run(para, "Applicable To:\n(select all that apply)",
                       bold=True, size_pt=9.0)
        else:
            cl.text = ""
            para = cl.paragraphs[0]
            set_paragraph_spacing(para, 0, 0)

        # Right content cell
        style_cell(cr, right_shade)
        set_col_width(cr, APP_R)
        cr.text = ""
        para = cr.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT if not is_subhdr else WD_ALIGN_PARAGRAPH.RIGHT
        set_paragraph_spacing(para, 50, 50)
        styled_run(para, right_text, bold=is_subhdr, size_pt=9.0)

    # Add Policy Types checked items inside the sub-header row (append after "Policy Types" label)
    # They go below the Policy Types header, before Corporate — already in chk_rows order above

    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # HELPER: single-column section table (heading row + content row)
    # ──────────────────────────────────────────────────────────────────────────
    def section_table(heading, content_builder):
        """
        content_builder: callable(cell) — fills the content cell.
        Returns the table.
        """
        tbl = new_table(doc, 2, 1, [PAGE_W], PAGE_W)
        hdr_cell = tbl.rows[0].cells[0]
        style_cell(hdr_cell, GRAY_SECTION)
        set_cell_margins(hdr_cell, top=60, bottom=60, left=80, right=80)
        section_heading_paragraph(hdr_cell, heading)

        cnt_cell = tbl.rows[1].cells[0]
        style_cell(cnt_cell, WHITE)
        set_cell_margins(cnt_cell, top=100, bottom=100, left=120, right=120)
        cnt_cell.text = ""
        content_builder(cnt_cell)
        return tbl

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 3 — Purpose and Scope
    # ──────────────────────────────────────────────────────────────────────────
    def fill_purpose(cell):
        for line in data["purpose"].strip().split("\n"):
            line = line.strip()
            if line:
                add_content_para(cell, line)
            else:
                add_empty_para(cell)

    section_table("Purpose and Scope", fill_purpose)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 4 — Definitions
    # ──────────────────────────────────────────────────────────────────────────
    def fill_definitions(cell):
        for term, definition in data.get("definitions", {}).items():
            para = cell.add_paragraph()
            set_paragraph_spacing(para, 50, 50)
            styled_run(para, "\u2013  ", size_pt=10)
            styled_run(para, f"{term}:  ", bold=True, size_pt=10)
            styled_run(para, definition, size_pt=10)

    section_table("Definitions", fill_definitions)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 5 — Policy Statement
    # ──────────────────────────────────────────────────────────────────────────
    def fill_policy_statement(cell):
        stmt = data.get("policy_statement", "")
        # Expects format: "It is the policy of WHPS that..."
        # We bold+italicize up to "that"
        if " that " in stmt:
            idx  = stmt.index(" that ") + 6
            prefix = stmt[:idx]
            rest   = stmt[idx:]
        else:
            prefix, rest = "", stmt
        para = cell.add_paragraph()
        set_paragraph_spacing(para, 60, 60)
        if prefix:
            styled_run(para, prefix, bold=True, italic=True, size_pt=10)
        styled_run(para, rest, size_pt=10)

    section_table("Policy Statement", fill_policy_statement)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 6 — Procedures
    # ──────────────────────────────────────────────────────────────────────────
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
                add_bullet_paragraph(cell, text)
            elif kind == "sub-bullet":
                add_bullet_paragraph(cell, text, is_sub=True)
            elif kind == "bold_intro":
                # bold_prefix tuple: (bold_text, rest_text)
                add_content_para(cell, "", bold_prefix=(item["bold"], item["rest"]))
            elif kind == "bold_intro_semi":
                para = cell.add_paragraph()
                set_paragraph_spacing(para, 60, 40)
                styled_run(para, item["bold"], bold=True, size_pt=10)
                segs = item["rest"].split(";")
                for i, seg in enumerate(segs):
                    seg = seg.strip()
                    if not seg:
                        continue
                    suffix = ";" if i < len(segs) - 1 else ""
                    if i == 0:
                        styled_run(para, seg + suffix, size_pt=10)
                    else:
                        p2 = cell.add_paragraph()
                        set_paragraph_spacing(p2, 0, 40)
                        styled_run(p2, seg + suffix, size_pt=10)
            elif kind == "empty":
                add_empty_para(cell)

    section_table("Procedures", fill_procedures)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 7 — Related Policies
    # ──────────────────────────────────────────────────────────────────────────
    def fill_related(cell):
        for policy in data.get("related_policies", []):
            add_content_para(cell, policy)

    section_table("Related Policies or Standard Operating Procedures", fill_related)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 8 — Citations/References
    # ──────────────────────────────────────────────────────────────────────────
    def fill_citations(cell):
        for citation in data.get("citations", []):
            if ";" in citation:
                apply_semicolon_breaks(cell, citation)
            else:
                add_content_para(cell, citation)

    section_table("Citations/References", fill_citations)
    gap_para()

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE 9 — Revision History
    # ──────────────────────────────────────────────────────────────────────────
    C1 = int(PAGE_W * 0.12)
    C2 = int(PAGE_W * 0.13)
    C3 = int(PAGE_W * 0.20)
    C4 = PAGE_W - C1 - C2 - C3

    rev_entries = data.get("revision_history", [])
    total_rev_rows = 2 + len(rev_entries)   # heading + col headers + data

    t9 = new_table(doc, total_rev_rows, 4, [C1, C2, C3, C4], PAGE_W)

    # Row 0: "Revision History" heading spanning all 4 cols
    t9.rows[0].cells[0].merge(t9.rows[0].cells[3])
    style_cell(t9.rows[0].cells[0], GRAY_SECTION)
    set_cell_margins(t9.rows[0].cells[0], top=60, bottom=60, left=80, right=80)
    section_heading_paragraph(t9.rows[0].cells[0], "Revision History")

    # Row 1: Column headers
    for col_idx, (hdr_text, width) in enumerate(
            [("Date", C1), ("Version Number", C2),
             ("Updated By", C3), ("Description of Update", C4)]):
        hc = t9.rows[1].cells[col_idx]
        style_cell(hc, GRAY_LABEL)
        set_col_width(hc, width)
        hc.text = ""
        para = hc.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_paragraph_spacing(para, 50, 50)
        styled_run(para, hdr_text, bold=True, size_pt=9.0)

    # Data rows
    for ri, entry in enumerate(rev_entries):
        row = t9.rows[ri + 2]
        date_txt, ver_txt, by_txt, desc_txt = entry
        for ci, (txt, width) in enumerate(
                [(date_txt, C1), (ver_txt, C2), (by_txt, C3), (desc_txt, C4)]):
            rc = row.cells[ci]
            style_cell(rc, WHITE)
            set_col_width(rc, width)
            rc.text = ""
            for li, line in enumerate(txt.split("\n")):
                if li == 0:
                    para = rc.paragraphs[0]
                else:
                    para = rc.add_paragraph()
                set_paragraph_spacing(para, 30, 30)
                styled_run(para, line.strip(), size_pt=9.0)

    # ──────────────────────────────────────────────────────────────────────────
    # Footer
    # ──────────────────────────────────────────────────────────────────────────
    footer = doc.sections[0].footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_para.text = ""
    set_paragraph_spacing(footer_para, 0, 0)
    styled_run(footer_para,
               "Confidential & Proprietary \u00a9 HealthPlan Services Inc., "
               "including its subsidiaries and affiliates",
               size_pt=7.5, color_hex="555555")

    footer_para2 = footer.add_paragraph()
    set_paragraph_spacing(footer_para2, 0, 0)
    styled_run(footer_para2,
               f"{data['policy_number']}  |  {data['policy_name']}  |  {data['version']}",
               size_pt=7.5, color_hex="555555")

    # ── Save ────────────────────────────────────────────────────────────────
    doc.save(output_path)
    print(f"\n✅  Saved: {output_path}\n")


# ══════════════════════════════════════════════════════════════════════════════
# POLICY DATA  ←  Fill this dictionary with your migrated policy content
# ══════════════════════════════════════════════════════════════════════════════
POLICY_DATA = {

    # ── Header ──────────────────────────────────────────────────────────────
    "policy_name":    "Mobile Device Management in the Workplace",
    "policy_number":  "SEC-P020",
    "version":        "V10.0",
    "grc_id":         "",
    "supersedes":     "",
    "effective_date": "8/31/2014",
    "last_reviewed":  "09/26/2025",
    "last_revised":   "09/26/2025",
    "custodians":     "Chelsea Sanchez, Alexis Taylor",
    "owner_name":     "Dan Cutler",
    "owner_title":    "Dir., Security Engineering",
    "approver_name":  "Sam Sweilem",
    "approver_title": "CIO",
    "date_signed":    "",
    "date_approved":  "09/30/2025",

    # ── Applicable To ────────────────────────────────────────────────────────
    "applicable_to": {
        "hps_inc":      True,
        "agency":       True,
        "corporate":    True,
        "govt_affairs": False,
        "legal_review": False,
    },
    "policy_types": {
        "carrier_specific": True,
        "cross_carrier":    True,
        "global":           True,
        "on_off_hix":       False,
    },
    "line_of_business": {
        "all_lobs":            True,
        "specific_lob":        "[INSERT HERE]",
        "specific_lob_checked": False,
    },

    # ── Purpose and Scope ────────────────────────────────────────────────────
    "purpose": """
This policy establishes safeguards for mobile devices to protect information from unauthorized disclosure, use, modification, and loss. Mobile devices, while increasingly prolific and useful, represent a significant risk to information and data security if the appropriate controls and procedures are not applied, and can serve as a conduit for unauthorized access to the organization's information resources. This can lead to data leakage and system compromise.

This policy's scope includes securing both WHPS-provided and personally owned mobile devices present on WHPS premises and connected to the WHPS network. A mobile device, for this policy's purpose, refers to any portable wireless device small enough to be used while held in the hand. This covers smartphones, tablets and other mobile devices but does not include laptops and mini terminals, such as iGel, WYSE Clients, etc.
""",

    # ── Definitions ──────────────────────────────────────────────────────────
    "definitions": {
        "iGel":        "a Linux-based operating system optimized for secure, scalable delivery of virtual desktops and cloud workspaces.",
        "WYSE":        "is an application that manages the use of Wyse thin clients. This includes managing users, jobs, and more.",
        "Jail-broken": "modify (a smartphone or other electronic device) to remove restrictions imposed by the manufacturer or operator, e.g. to allow the installation of unauthorized software.",
    },

    # ── Policy Statement ─────────────────────────────────────────────────────
    "policy_statement": (
        "It is the policy of Wipro HealthPlan Holdings (WHPS) "
        "that Phones, tablets, and other mobile devices containing Restricted or Confidential "
        "and Proprietary data must be adequately protected from unauthorized access through "
        "appropriate access controls, encryption, theft deterrents and screen locks."
    ),

    # ── Procedures ───────────────────────────────────────────────────────────
    # Each item is a dict with "type" and "text" (or "bold"/"rest" for bold_intro).
    # Types: "para" | "heading" | "bullet" | "sub-bullet" | "bold_intro" |
    #        "bold_intro_semi" | "empty"
    "procedures": [
        {"type": "para",    "text": "All mobile devices that connect to the corporate network must be registered with IT (Information Technology) and be managed centrally by IT using its mobile device security solution."},
        {"type": "empty"},
        {"type": "para",    "text": "Mobile devices—whether personally-owned or corporate-owned—may not access email, calendar, or any other data resources directly from native device applications, unless these data can be monitored and managed by the IT mobile device security solution. Most commonly, this means that ActiveSync may not be used to access network resources without the use of the mobile device security solution."},
        {"type": "empty"},
        {"type": "heading", "text": "Expectation of Privacy:"},
        {"type": "bold_intro_semi",
         "bold": "Corporate-provided devices – ",
         "rest": "WHPS retains its right to monitor the activities of its workforce members using WHPS computing equipment and electronic networks during normally expected work hours. This includes the right to monitor email, calendars, and other data transmissions to and from Company-provided mobile devices; the right to restrict what applications (or \u201capps\u201d) are downloaded and installed in the devices; and other asset and security management activities not necessarily listed here. WHPS does not track or monitor the physical location of workforce members using the GPS Location features of mobile devices."},
        {"type": "bold_intro",
         "bold": "Personally-owned devices – ",
         "rest": "WHPS shall manage personally-owned devices to the extent required to protect WHPS business data permitted to be stored or processed on personal devices. It does not monitor, restrict, or control full use of the device, its features, any app installation, or any other function that does not impact the security of Company data on the device."},
        {"type": "empty"},
        {"type": "para",    "text": "Mobile devices belonging to employees must also have been authorized by the direct manager as permitted to connect to the network, have a documented job-related need, or they are exempted in writing by the Chief Information Officer."},
        {"type": "empty"},
        {"type": "heading", "text": "Technical Requirements for all mobile devices:"},
        {"type": "bullet",  "text": "Devices must store all user-saved passwords, if any are stored, in an encrypted password store."},
        {"type": "bullet",  "text": "Devices must be password or PIN protected using the features of the device to prevent unauthorized access."},
        {"type": "bullet",  "text": "The device must lock itself if idle for three minutes and require a password or PIN to unlock the device."},
        {"type": "bullet",  "text": "Devices must be configured with a security PIN code. This PIN must not be the same as any other credentials used within the organization."},
        {"type": "bullet",  "text": "Devices must be encrypted in accordance with WHPS compliance standards. Mobile devices that store sensitive information must use a Federal Information Process Standard (FIPS 140-2) encryption method to protect data from unauthorized disclosure."},
        {"type": "empty"},
        {"type": "heading", "text": "User Requirements – All devices:"},
        {"type": "bullet",  "text": "Users must report all lost or stolen WHPS devices or mobile devices that connect to the corporate network to the IT Help Desk immediately."},
        {"type": "bullet",  "text": "If a user suspects that unauthorized access to company data has taken place through a mobile device, the user must report the incident to IT Help Desk immediately."},
        {"type": "para",    "text": "The employee's device is remotely wiped if:"},
        {"type": "sub-bullet", "text": "The device is lost."},
        {"type": "sub-bullet", "text": "The employee terminates his or her employment."},
        {"type": "para",    "text": "IT detects:"},
        {"type": "sub-bullet", "text": "A data or policy breach."},
        {"type": "sub-bullet", "text": "A virus or similar threat to the security of the company's data and technology infrastructure."},
        {"type": "empty"},
        {"type": "bullet",  "text": "Devices must not be \u201cjail-broken\u201d or have any software/firmware installed which is designed to gain access to functionality not intended to be exposed to the user."},
        {"type": "bullet",  "text": "Users must not load pirated software or illegal content onto their devices."},
        {"type": "bullet",  "text": "Devices must be kept up to date with the manufacturer or network provided patches. As a minimum, patches should be checked weekly and applied at least once a month."},
        {"type": "bullet",  "text": "The employee must always use their devices ethically and adhere to the company\u2019s acceptable use policies."},
        {"type": "empty"},
        {"type": "heading", "text": "WHPS Owned Devices:"},
        {"type": "bullet",  "text": "Users must only load data essential to their role onto corporate owned mobile device(s)."},
        {"type": "bullet",  "text": "Users must never download or access cardholder data from WHPS devices."},
        {"type": "empty"},
        {"type": "heading", "text": "Personally Owned Devices:"},
        {"type": "bullet",  "text": "Employees are responsible for notifying their mobile carrier immediately upon loss of a device."},
        {"type": "bullet",  "text": "While WHPS administers every precaution to prevent the employee\u2019s personal data from being lost, in the event it must remote wipe a device, it is the employee\u2019s responsibility to take additional precautions, such as backing up email, contacts, among others."},
        {"type": "bullet",  "text": "Users must be cautious about the merging of personal and work email accounts on their devices. Users must take particular care to ensure company data is only sent through the corporate email system. If a user suspects that company data has been sent from a personal email account, either in body text or as an attachment, they must notify WHPS IT Service Desk immediately."},
        {"type": "bullet",  "text": "The employee is personally liable for all costs associated with his or her device."},
        {"type": "bullet",  "text": "The employee assumes full liability for risks including, but not limited to, the partial or complete loss of company and personal data due to an operating system crash, errors, bugs, viruses, malware, and/or other software or hardware failures, or programming errors that render the device unusable."},
        {"type": "bullet",  "text": "Users must never download or access cardholder data from personally owned devices."},
    ],

    # ── Related Policies ─────────────────────────────────────────────────────
    "related_policies": [
        "SEC-P001 Information Security Governing Policy",
        "SEC-C002 Information Security Charter",
        "SEC-P008 Password Policy",
    ],

    # ── Citations / References ────────────────────────────────────────────────
    "citations": [
        "45 CFR 164.308(a)(5)(ii)(D);",
        "CoBIT 5.0: DSS05.02, 05.04;",
        "HiTrust v9.3: 01.x, 01.y, 10.k;",
        "PCI DSS v3.2: 2.1, 8.5.2, 8.5.3, 8.5.8, 8.5.10-12;",
        "(State of Mass.) 201 CMR 17.04(1)(b).",
        "ISO/IEC 27001:2022 Information Security, Cybersecurity and Privacy Protection: A.6.2.1, A.8.1.3.",
    ],

    # ── Revision History ─────────────────────────────────────────────────────
    # Each entry: (Date, Version, Updated By, Description)
    "revision_history": [
        ("12/4/2013",  "v0.1 s/b 1.0", "Kate Mullin",      "Initial Draft"),
        ("4/18/2014",  "v0.2 s/b 2.0", "Jay Schwitzgebel", "Adapted for mobile devices only (no laptops) and prep for Good Technologies rollout"),
        ("6/13/2014",  "v1.0 s/b 3.0", "Kelly Oliver",     "Updated to include PCI DSS 2.0 requirements"),
        ("7/29/2014",  "v1.0 s/b 3.0", "Ray Johnson",      "Updated grammar and style guidelines."),
        ("8/26/2015",  "v2.0 s/b 4.0", "Jay Schwitzgebel", "Format updates;\nsome updates to enterprise mobile device security solution"),
        ("8/10/2017",  "v3.0 s/b 4.0", "Jay Schwitzgebel", "Updated header info;\nadded SOP;\nadded ISO control citations"),
        ("8/30/2019",  "v4.0 s/b 5.0", "David Folden",     "Updates from HPH to WHPS throughout policy;\nupdated HPH logo to WHPS/Wipro logo;\nannual review"),
        ("9/10/2020",  "V4.0 s/b 6.0", "Andrea Cooper",    "Updated References and citations;\nUpdated version in header and footer"),
        ("9/10/2020",  "V4.0 s/b 6.0", "Kelly Latinka",    "Updated Approver to Dennis Prysner. Minor Maintenance."),
        ("10/18/2021", "V7.0",          "Victor Beary",     "No material changes made to content;\nupdated new CISO name to Sachin Sheth"),
        ("10/20/2021", "V5.0 s/b 7.0", "Alexis Taylor",    "Changed reviewed and revised dates, change version number, updated the new CIO to Sam Sweilem, and updated the name and version number in the footer."),
        ("6/28/2023",  "V8.0",          "Dan Cutler",       "Updated policy with HiTrust language"),
        ("6/28/2023",  "V8.0",          "Alexis Taylor",    "Annual Review 2023: Moved to new template, changed review/revise dates, change approver, update footer;\ngrammar, formatting corrections, added definitions"),
        ("4/24/2024",  "V9.0",          "Brian Word",       "Annual Review. Updated Grammar issues."),
        ("8/7/2025",   "V10.0",         "Dan Cutler",       "Annual review and approval.\nRelated Policy Section changes:\nChanged SEC-P002 to SEC-C002.\nRemoved SEC-S020.1."),
        ("09/26/2025", "V10.0",         "Chelsea Sanchez",  "Annual Compliance Review complete."),
    ],
}

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out_name = (
        f"{POLICY_DATA['policy_number']} "
        f"{POLICY_DATA['policy_name']} "
        f"{POLICY_DATA['version']}-NEW.docx"
    )
    build_policy_document(POLICY_DATA, out_name)
