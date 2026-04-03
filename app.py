import os
import tempfile
from datetime import datetime, date

import streamlit as st
from groq import Groq
from docx import Document
from hps_policy_migration_builder import build_policy_document


# =========================================================
# CONFIG
# =========================================================
LOCAL_GROQ_API_KEY = ""

TEMPLATE_OPTIONS = [
    "Generic Policy Template",
    "Custom Enterprise Template",
]

PAGE_OPTIONS = ["Overview", "Migrate a Policy", "Create a Policy"]

EXTRACTION_PROMPT = """
You are a policy migration specialist.

Your task is to read the attached legacy policy document and extract ALL content
into the exact Python dictionary structure below.

STRICT RULES:
- Do NOT summarize, rewrite, or remove content
- Preserve the source wording as closely as possible
- Fix only minor spacing / punctuation / obvious grammar defects where needed
- Map all content into the correct field
- If content does not fit perfectly, place it in the most logical field
- For procedure items, classify each entry using exactly one type:
  "para" = standalone paragraph
  "heading" = bold underlined subsection title
  "bullet" = first-level bullet
  "sub-bullet" = second-level bullet
  "bold_intro" = paragraph that starts with a bold label; use keys "bold" and "rest"
  "bold_intro_semi" = same as bold_intro but "rest" contains semicolons
  "empty" = blank spacer line

Return ONLY a valid Python dictionary assignment. No explanation. No markdown.
Start your response with:
POLICY_DATA = {
and end with the closing brace.

POLICY_DATA = {
    "policy_name": "",
    "policy_number": "",
    "version": "",
    "grc_id": "",
    "supersedes": "",
    "effective_date": "",
    "last_reviewed": "",
    "last_revised": "",
    "custodians": "",
    "owner_name": "",
    "owner_title": "",
    "approver_name": "",
    "approver_title": "",
    "date_signed": "",
    "date_approved": "",
    "applicable_to": {
        "hps_inc": False,
        "agency": True,
        "corporate": True,
        "govt_affairs": False,
        "legal_review": False
    },
    "policy_types": {
        "carrier_specific": False,
        "cross_carrier": False,
        "global": False,
        "on_off_hix": False
    },
    "line_of_business": {
        "all_lobs": True,
        "specific_lob": "",
        "specific_lob_checked": False
    },
    "purpose": "",
    "definitions": {},
    "policy_statement": "",
    "procedures": [],
    "related_policies": [],
    "citations": [],
    "revision_history": []
}

HERE IS THE LEGACY POLICY DOCUMENT:
"""

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Midnight",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# STATE
# =========================================================
if "page" not in st.session_state:
    st.session_state["page"] = "Overview"

if "selected_template" not in st.session_state:
    st.session_state["selected_template"] = TEMPLATE_OPTIONS[0]

if "migration_policy_data" not in st.session_state:
    st.session_state["migration_policy_data"] = None

if "created_policy_data" not in st.session_state:
    st.session_state["created_policy_data"] = None

if "logo_path" not in st.session_state:
    st.session_state["logo_path"] = None

if "logo_preview_name" not in st.session_state:
    st.session_state["logo_preview_name"] = ""

# =========================================================
# STYLING
# =========================================================
st.markdown(
    """
    <style>
        :root {
            --bg-1: #05070c;
            --bg-2: #0b1020;
            --bg-3: #111827;
            --surface: rgba(14, 20, 33, 0.78);
            --surface-soft: rgba(255,255,255,0.04);
            --surface-light: rgba(255,255,255,0.06);
            --line: rgba(255,255,255,0.08);
            --line-strong: rgba(255,255,255,0.14);
            --text: #f5f7fa;
            --text-muted: #a6b0be;
            --text-dim: #7d8796;
            --accent: #00b7ff;
            --accent-2: #2563eb;
            --accent-warm: #ff5b2e;
            --success: #1ed760;
        }

        html, body, [class*="css"] {
            background: transparent !important;
        }

        .stApp {
            background:
                radial-gradient(circle at 78% 16%, rgba(255,91,46,0.18), transparent 18%),
                radial-gradient(circle at 62% 18%, rgba(0,183,255,0.16), transparent 16%),
                linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 42%, var(--bg-3) 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 0.9rem;
            padding-bottom: 2rem;
            background: transparent !important;
        }

        header {visibility: hidden;}

        div[data-testid="stVerticalBlock"] > div {
            background: transparent !important;
        }

        .fade-in {
            animation: fadeIn 0.7s ease-out;
        }

        .slide-up {
            animation: slideUp 0.75s ease-out;
        }

        .slide-left {
            animation: slideLeft 0.8s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to   { opacity: 1; }
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(18px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideLeft {
            from { opacity: 0; transform: translateX(22px); }
            to   { opacity: 1; transform: translateX(0); }
        }

        /* ---------- Nav ---------- */
        .topnav-shell {
            animation: fadeIn 0.6s ease-out;
        }

        .topnav {
            background: rgba(10, 14, 24, 0.72);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 28px rgba(0,0,0,0.22);
            backdrop-filter: blur(14px);
        }

        .brand-eyebrow {
            color: rgba(255,255,255,0.55);
            font-size: 0.72rem;
            letter-spacing: 0.24em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .brand-title {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            margin-bottom: 0.08rem;
            color: var(--text);
        }

        .brand-subtitle {
            color: var(--text-muted);
            font-size: 0.94rem;
        }

        div[data-testid="stRadio"] > div {
            gap: 0.45rem;
        }

        div[data-testid="stRadio"] label {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 14px !important;
            padding: 0.62rem 0.92rem !important;
            transition: all .18s ease;
        }

        div[data-testid="stRadio"] label:hover {
            background: rgba(255,255,255,0.04) !important;
        }

        div[data-testid="stRadio"] label p {
            color: var(--text-muted) !important;
            font-weight: 600 !important;
        }

        div[data-testid="stRadio"] label:has(input:checked) {
            background: rgba(255,255,255,0.07) !important;
            border: 1px solid var(--line-strong) !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.18);
        }

        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #ffffff !important;
        }

        /* ---------- Hero ---------- */
        .hero-wrap {
            animation: slideUp 0.8s ease-out;
        }

        .hero-dark {
            position: relative;
            overflow: hidden;
            border-radius: 28px;
            padding: 3.4rem 2.4rem;
            background:
                radial-gradient(circle at 82% 24%, rgba(255,91,46,0.22), transparent 20%),
                radial-gradient(circle at 64% 18%, rgba(0,183,255,0.20), transparent 16%),
                linear-gradient(135deg, #06080d 0%, #0b1120 46%, #140d0b 100%);
            color: var(--text);
            box-shadow: 0 18px 42px rgba(0,0,0,0.26);
            border: 1px solid var(--line);
            margin-bottom: 1rem;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 1.18fr 0.82fr;
            gap: 2rem;
            align-items: center;
        }

        .hero-label {
            color: rgba(255,255,255,0.64);
            font-size: 0.76rem;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            margin-bottom: 1rem;
            animation: fadeIn 1s ease-out;
        }

        .hero-title {
            font-size: 4.15rem;
            font-weight: 700;
            line-height: 0.96;
            letter-spacing: 0.01em;
            margin-bottom: 1rem;
            animation: slideUp 0.9s ease-out;
        }

        .hero-title .accent {
            color: var(--accent);
        }

        .hero-title .accent-warm {
            color: var(--accent-warm);
        }

        .hero-copy {
            color: rgba(255,255,255,0.78);
            font-size: 1.08rem;
            line-height: 1.75;
            max-width: 760px;
            margin-bottom: 1.2rem;
            animation: fadeIn 1.05s ease-out;
        }

        .hero-pill-row {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-bottom: 1.35rem;
            animation: fadeIn 1.1s ease-out;
        }

        .hero-pill {
            display: inline-block;
            padding: 0.42rem 0.8rem;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.05);
            color: rgba(255,255,255,0.82);
            font-size: 0.78rem;
        }

        .hero-visual {
            min-height: 320px;
            border-radius: 24px;
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)),
                radial-gradient(circle at 24% 24%, rgba(0,183,255,0.16), transparent 18%),
                radial-gradient(circle at 78% 28%, rgba(255,91,46,0.18), transparent 18%),
                linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
            border: 1px solid rgba(255,255,255,0.09);
            animation: slideLeft 0.95s ease-out;
        }

        .hero-visual::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(120deg, transparent 0%, transparent 34%, rgba(255,255,255,0.08) 35%, transparent 38%),
                repeating-linear-gradient(
                    135deg,
                    rgba(255,91,46,0.24) 0px,
                    rgba(255,91,46,0.24) 3px,
                    transparent 3px,
                    transparent 14px
                );
            opacity: 0.56;
        }

        .hero-visual-glow {
            position: absolute;
            inset: auto 12% 10% 12%;
            height: 64px;
            background: radial-gradient(circle, rgba(0,183,255,0.45), transparent 60%);
            filter: blur(14px);
            animation: pulseGlow 3.2s ease-in-out infinite;
        }

        @keyframes pulseGlow {
            0%, 100% { opacity: 0.55; transform: scale(1); }
            50% { opacity: 0.9; transform: scale(1.06); }
        }

        .hero-visual-inner {
            position: absolute;
            left: 2rem;
            right: 2rem;
            bottom: 2rem;
            z-index: 2;
        }

        .hero-visual-kicker {
            color: rgba(255,255,255,0.58);
            font-size: 0.78rem;
            letter-spacing: 0.24em;
            text-transform: uppercase;
            margin-bottom: 0.7rem;
        }

        .hero-visual-title {
            color: #ffffff;
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 700;
            margin-bottom: 0.7rem;
        }

        .hero-visual-copy {
            color: rgba(255,255,255,0.74);
            font-size: 0.94rem;
            line-height: 1.62;
        }

        /* ---------- Overview Sections ---------- */
        .section-surface {
            background: rgba(14,20,33,0.72);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1.2rem;
            box-shadow: 0 8px 20px rgba(0,0,0,0.14);
            height: 100%;
            backdrop-filter: blur(12px);
        }

        .section-title {
            font-size: 1.45rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.35rem;
        }

        .section-copy {
            color: var(--text-muted);
            font-size: 0.94rem;
            line-height: 1.66;
        }

        .feature-title {
            font-size: 1.08rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.35rem;
        }

        .feature-copy {
            color: var(--text-muted);
            font-size: 0.92rem;
            line-height: 1.62;
        }

        .dark-band {
            background:
                radial-gradient(circle at 80% 20%, rgba(255,91,46,0.12), transparent 22%),
                linear-gradient(135deg, rgba(8,8,10,0.94) 0%, rgba(17,10,10,0.94) 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 1.5rem;
            color: #ffffff;
            box-shadow: 0 16px 30px rgba(0,0,0,0.18);
        }

        .dark-band-title {
            color: #ffffff;
            font-size: 1.85rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }

        .dark-band-copy {
            color: rgba(255,255,255,0.76);
            font-size: 0.98rem;
            line-height: 1.72;
        }

        .stat-row {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .stat-chip {
            min-width: 150px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 1rem;
        }

        .stat-number {
            font-size: 1.95rem;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 0.25rem;
        }

        .stat-label {
            font-size: 0.85rem;
            color: rgba(255,255,255,0.74);
        }

        /* ---------- Workspace ---------- */
        .workspace-header {
            margin-bottom: 1rem;
            animation: fadeIn 0.7s ease-out;
        }

        .workspace-title {
            font-size: 1.9rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.22rem;
        }

        .workspace-subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 1rem;
            box-shadow: 0 10px 24px rgba(0,0,0,0.14);
            height: 100%;
            backdrop-filter: blur(12px);
            animation: slideUp 0.7s ease-out;
        }

        .panel-title {
            font-size: 1.35rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.25rem;
        }

        .panel-copy {
            color: var(--text-muted);
            font-size: 0.92rem;
            line-height: 1.6;
            margin-bottom: 0.8rem;
        }

        .soft-box {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 0.95rem 1rem;
            color: #c1c8d2;
            font-size: 0.9rem;
            line-height: 1.62;
        }

        .preview-box {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 1rem;
            color: #ffffff;
        }

        .caption {
            color: var(--text-dim);
            font-size: 0.8rem;
            margin-bottom: 0.65rem;
        }

        .success-box {
            background: rgba(30,215,96,0.10);
            border: 1px solid rgba(30,215,96,0.28);
            border-radius: 14px;
            padding: 0.85rem 1rem;
            color: #95f1b2;
            text-align: center;
            font-weight: 600;
            margin-top: 0.9rem;
        }

        .divider-space {
            height: 0.9rem;
        }

        /* ---------- Inputs ---------- */
        .stButton > button {
            width: 100% !important;
            background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.92rem 1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 10px 20px rgba(0,183,255,0.18) !important;
            transition: transform .15s ease, box-shadow .15s ease, opacity .15s ease !important;
        }

        .stButton > button p,
        .stButton > button span,
        .stButton > button div {
            color: #ffffff !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 28px rgba(0,183,255,0.22) !important;
            opacity: 0.96;
        }

        .stDownloadButton > button {
            width: 100% !important;
            background: rgba(255,255,255,0.06) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 14px !important;
            padding: 0.92rem 1rem !important;
            font-weight: 600 !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: #0f1522 !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
        }

        [data-testid="stWidgetLabel"] p {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        input::placeholder,
        textarea::placeholder {
            color: #8a94a3 !important;
            opacity: 1 !important;
        }

        .stFileUploader > div {
            background: #0f1522 !important;
            border: 1px dashed rgba(255,255,255,0.14) !important;
            border-radius: 14px !important;
        }

        .stProgress > div > div {
            background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
        }

        .stAlert {
            background: rgba(255,255,255,0.05) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
        }

        h1, h2, h3 {
            color: #ffffff !important;
        }

        p, span, label {
            color: var(--text-muted);
        }

        @media (max-width: 900px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 2.7rem;
            }
            .hero-dark {
                padding: 2rem 1.25rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def get_api_key() -> str:
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""
    return secret_key or os.getenv("GROQ_API_KEY", "") or LOCAL_GROQ_API_KEY


def parse_policy_data(raw_output: str):
    if "POLICY_DATA = {" in raw_output:
        dict_str = raw_output[raw_output.index("POLICY_DATA = {"):]
    else:
        dict_str = raw_output

    namespace = {}
    exec(dict_str, {}, namespace)
    return namespace.get("POLICY_DATA", None)


def extract_text_from_docx(uploaded_file) -> str:
    doc = Document(uploaded_file)
    lines = []

    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            lines.append(text)

    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = " ".join(
                    para.text.strip() for para in cell.paragraphs if para.text.strip()
                ).strip()
                if cell_text:
                    row_text.append(cell_text)
            if row_text:
                lines.append(" | ".join(row_text))

    return "\n".join(lines)


def get_uploaded_text(uploaded_file) -> str:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".docx"):
        return extract_text_from_docx(uploaded_file)
    return uploaded_file.read().decode("utf-8", errors="ignore")


def normalize_date_input(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%-m/%-d/%Y")
        except Exception:
            pass
    return value


def parse_date_safe(value: str):
    value = normalize_date_input(value)
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y")
    except Exception:
        return None


def default_if_blank(current: str, source: str) -> str:
    return current if str(current).strip() else source


def validate_dates(effective_date, last_reviewed, last_revised, date_signed, date_approved):
    errors = []
    eff = parse_date_safe(effective_date)
    revw = parse_date_safe(last_reviewed)
    revd = parse_date_safe(last_revised)
    signed = parse_date_safe(date_signed)
    approved = parse_date_safe(date_approved)

    if eff and revw and revw < eff:
        errors.append("Last Reviewed cannot be earlier than Effective Date.")
    if eff and revd and revd < eff:
        errors.append("Last Revised cannot be earlier than Effective Date.")
    if signed and approved and approved < signed:
        errors.append("Date Approved cannot be earlier than Date Signed.")
    return errors


def split_lines(text: str):
    return [line.strip() for line in str(text).splitlines() if line.strip()]


def make_procedures_from_text(text: str):
    procedures = []
    for line in split_lines(text):
        if line.startswith("- "):
            procedures.append({"type": "bullet", "text": line[2:].strip()})
        else:
            procedures.append({"type": "para", "text": line})
    return procedures


def build_creation_policy_data(
    policy_name,
    policy_number,
    version,
    grc_id,
    supersedes,
    effective_date,
    last_reviewed,
    last_revised,
    custodians,
    owner_name,
    owner_title,
    approver_name,
    approver_title,
    date_signed,
    date_approved,
    purpose,
    definitions_text,
    policy_statement,
    procedures_text,
    related_policies_text,
    citations_text,
    template_name,
):
    effective_date = normalize_date_input(effective_date)
    last_reviewed = normalize_date_input(default_if_blank(last_reviewed, effective_date))
    last_revised = normalize_date_input(default_if_blank(last_revised, effective_date))
    date_signed = normalize_date_input(default_if_blank(date_signed, effective_date))
    date_approved = normalize_date_input(default_if_blank(date_approved, date_signed))

    definitions = {}
    for line in split_lines(definitions_text):
        if ":" in line:
            key, value = line.split(":", 1)
            definitions[key.strip()] = value.strip()
        else:
            definitions[line.strip()] = ""

    related_policies = split_lines(related_policies_text)
    citations = split_lines(citations_text)
    procedures = make_procedures_from_text(procedures_text)

    applicable_to = {
        "hps_inc": False,
        "agency": True,
        "corporate": True,
        "govt_affairs": False,
        "legal_review": False,
    }

    return {
        "policy_name": policy_name,
        "policy_number": policy_number,
        "version": version or "V1.0",
        "grc_id": grc_id,
        "supersedes": supersedes,
        "effective_date": effective_date,
        "last_reviewed": last_reviewed,
        "last_revised": last_revised,
        "custodians": custodians,
        "owner_name": owner_name,
        "owner_title": owner_title,
        "approver_name": approver_name,
        "approver_title": approver_title,
        "date_signed": date_signed,
        "date_approved": date_approved,
        "applicable_to": applicable_to,
        "policy_types": {
            "carrier_specific": False,
            "cross_carrier": False,
            "global": template_name == "Generic Policy Template",
            "on_off_hix": False,
        },
        "line_of_business": {
            "all_lobs": True,
            "specific_lob": "",
            "specific_lob_checked": False,
        },
        "purpose": purpose,
        "definitions": definitions,
        "policy_statement": policy_statement,
        "procedures": procedures,
        "related_policies": related_policies,
        "citations": citations,
        "revision_history": [],
        "template_name": template_name,
    }


def make_transparent_logo(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    allowed_exts = {".png", ".jpg", ".jpeg", ".webp"}
    if ext not in allowed_exts:
        raise ValueError("Unsupported file type. Please upload PNG, JPG, JPEG, or WEBP.")

    os.makedirs("uploads", exist_ok=True)
    os.makedirs("assets", exist_ok=True)

    safe_name = os.path.splitext(os.path.basename(uploaded_file.name))[0]
    safe_name = "".join(ch for ch in safe_name if ch.isalnum() or ch in ("-", "_")) or "logo"
    original_path = os.path.join("uploads", f"{safe_name}{ext}")
    output_path = os.path.join("assets", f"{safe_name}_transparent.png")

    with open(original_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with open(original_path, "rb") as f:
        input_bytes = f.read()

    output_bytes = remove(input_bytes)

    with open(output_path, "wb") as f:
        f.write(output_bytes)

    return output_path


def render_logo_controls(section_key: str):
    st.markdown('<div class="caption">Optional: upload a logo for the top banner.</div>', unsafe_allow_html=True)
    logo_file = st.file_uploader(
        "Upload a logo",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"logo_upload_{section_key}",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        process_clicked = st.button("Process Logo", key=f"process_logo_{section_key}")
    with c2:
        clear_clicked = st.button("Clear Logo", key=f"clear_logo_{section_key}")

    if process_clicked:
        if not logo_file:
            st.error("Please upload a logo first.")
        else:
            try:
                logo_path = make_transparent_logo(logo_file)
                st.session_state["logo_path"] = logo_path
                st.session_state["logo_preview_name"] = logo_file.name
                st.success("Logo processed and ready for the final document.")
            except Exception as e:
                st.error(f"Logo processing failed: {str(e)}")

    if clear_clicked:
        st.session_state["logo_path"] = None
        st.session_state["logo_preview_name"] = ""
        st.success("Logo cleared.")

    if st.session_state.get("logo_path") and os.path.exists(st.session_state["logo_path"]):
        st.image(
            st.session_state["logo_path"],
            caption=f"Processed Logo Preview — {st.session_state.get('logo_preview_name', 'logo')}",
            use_container_width=True,
        )


def render_policy_preview(policy_data):
    st.markdown('<div class="preview-box">', unsafe_allow_html=True)
    st.markdown(f"### {policy_data.get('policy_name', '')}")
    st.markdown(f"**Template:** {policy_data.get('template_name', 'Current Renderer')}")
    st.markdown(f"**Policy Number:** {policy_data.get('policy_number', '')}")
    st.markdown(f"**Version:** {policy_data.get('version', '')}")
    st.markdown(f"**Owner:** {policy_data.get('owner_name', '')} — {policy_data.get('owner_title', '')}")
    st.markdown(f"**Approver:** {policy_data.get('approver_name', '')} — {policy_data.get('approver_title', '')}")
    st.markdown(f"**Effective Date:** {policy_data.get('effective_date', '')}")

    st.markdown("#### Purpose")
    st.write(policy_data.get("purpose", "") or "Not provided")

    st.markdown("#### Policy Statement")
    st.write(policy_data.get("policy_statement", "") or "Not provided")

    st.markdown("#### Definitions")
    definitions = policy_data.get("definitions", {})
    if definitions:
        for key, value in definitions.items():
            st.markdown(f"- **{key}:** {value}")
    else:
        st.write("Not provided")

    st.markdown("#### Procedures")
    procedures = policy_data.get("procedures", [])
    if procedures:
        for item in procedures:
            item_type = item.get("type", "")
            text = item.get("text", "") or item.get("rest", "")
            if item_type == "bullet":
                st.markdown(f"- {text}")
            elif item_type == "sub-bullet":
                st.markdown(f"  - {text}")
            elif item_type == "heading":
                st.markdown(f"**{text}**")
            elif item_type in ["bold_intro", "bold_intro_semi"]:
                st.markdown(f"**{item.get('bold', '')}** {item.get('rest', '')}")
            else:
                st.write(text)
    else:
        st.write("Not provided")

    st.markdown("</div>", unsafe_allow_html=True)


def build_output_doc(policy_data, logo_path=None):
    policy_name = policy_data.get("policy_name", "Policy")
    policy_number = policy_data.get("policy_number", "SEC-P")
    version = policy_data.get("version", "V1.0")
    out_filename = f"{policy_number} {policy_name} {version}-NEW.docx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name

    build_policy_document(policy_data, tmp_path, logo_path=logo_path)

    with open(tmp_path, "rb") as f:
        docx_bytes = f.read()

    return out_filename, docx_bytes


def run_llm_transform(source_text: str, template_name: str):
    api_key = get_api_key()
    if not api_key:
        st.error("No Groq API key found. Set GROQ_API_KEY in Streamlit secrets or use the local fallback for testing.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    try:
        status.markdown('<div class="caption">Reading document…</div>', unsafe_allow_html=True)
        progress.progress(15)

        client = Groq(api_key=api_key)

        status.markdown('<div class="caption">Extracting policy structure…</div>', unsafe_allow_html=True)
        progress.progress(35)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": EXTRACTION_PROMPT + "\\n\\n" + source_text}],
            temperature=0.1,
            max_tokens=8000,
        )

        raw_output = response.choices[0].message.content.strip()

        status.markdown('<div class="caption">Parsing extracted data…</div>', unsafe_allow_html=True)
        progress.progress(60)

        policy_data = parse_policy_data(raw_output)

        if not policy_data:
            st.error("The model response could not be parsed into POLICY_DATA.")
            with st.expander("Raw model output"):
                st.code(raw_output)
            st.stop()

        policy_data["template_name"] = template_name
        progress.progress(100)
        status.empty()
        return policy_data

    except Exception as e:
        st.error(f"Midnight failed: {str(e)}")
        return None


# =========================================================
# NAV
# =========================================================
st.markdown('<div class="topnav-shell">', unsafe_allow_html=True)
st.markdown('<div class="topnav">', unsafe_allow_html=True)
nav_left, nav_right = st.columns([0.68, 0.32])

with nav_left:
    st.markdown('<div class="brand-title">MIDNIGHT</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

with nav_right:
    selected_page = st.radio(
        "Navigation",
        PAGE_OPTIONS,
        horizontal=True,
        label_visibility="collapsed",
        index=PAGE_OPTIONS.index(st.session_state["page"]),
        key="top_nav",
    )
    st.session_state["page"] = selected_page

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# OVERVIEW
# =========================================================
if st.session_state["page"] == "Overview":
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="hero-dark">', unsafe_allow_html=True)
    st.markdown('<div class="hero-grid">', unsafe_allow_html=True)

    with st.container():
        hero_left, hero_right = st.columns([1.18, 0.82])

        with hero_left:
            st.markdown('<div class="hero-label">Policy intelligence engine</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="hero-title">Move policy work out of the <span class="accent-warm">manual</span> era</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="hero-copy">Midnight helps teams migrate legacy policies, create new policies from structured intake, and produce cleaner, more consistent documentation through a controlled workflow.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="hero-pill-row">
                    <span class="hero-pill">Reduce audit prep time</span>
                    <span class="hero-pill">Standardize document structure</span>
                    <span class="hero-pill">Generate controlled output</span>
                    <span class="hero-pill">Support repeatable policy operations</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            cta1, cta2 = st.columns([0.28, 0.28])
            with cta1:
                if st.button("Migrate a Policy", key="hero_migrate"):
                    st.session_state["page"] = "Migrate a Policy"
                    st.rerun()
            with cta2:
                if st.button("Create a Policy", key="hero_create"):
                    st.session_state["page"] = "Create a Policy"
                    st.rerun()

        with hero_right:
            st.markdown(
                """
                <div class="hero-visual">
                    <div class="hero-visual-glow"></div>
                    <div class="hero-visual-inner">
                        <div class="hero-visual-kicker">Controlled documentation workflow</div>
                        <div class="hero-visual-title">One engine. Two core workflows.</div>
                        <div class="hero-visual-copy">
                            Use Midnight to transform existing policy documents or generate new ones from a structured intake process.
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="section-surface slide-up">', unsafe_allow_html=True)
        st.markdown('<div class="feature-title">Migrate Policy</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-copy">Upload an existing document and convert it into the selected template without manual copy-and-paste reconstruction.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-surface slide-up">', unsafe_allow_html=True)
        st.markdown('<div class="feature-title">Create Policy</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-copy">Build a new policy from structured intake with smart defaults, preview, and controlled final document generation.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="section-surface slide-up">', unsafe_allow_html=True)
        st.markdown('<div class="feature-title">How it works</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-copy">Select a template, upload or enter content, review the preview, then generate a standardized final document.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([0.56, 0.44])

    with bottom_left:
        st.markdown('<div class="dark-band slide-up">', unsafe_allow_html=True)
        st.markdown('<div class="dark-band-title">A cleaner way to manage policy operations</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="dark-band-copy">Manual policy updates consume time, create inconsistency, and slow down audit readiness. Midnight is designed to reduce that burden and provide a more controlled path from source content to final document.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="stat-row">
                <div class="stat-chip">
                    <div class="stat-number">80h</div>
                    <div class="stat-label">Manual effort that can be reduced across a backlog</div>
                </div>
                <div class="stat-chip">
                    <div class="stat-number">1</div>
                    <div class="stat-label">Structured workflow from source to final output</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with bottom_right:
        st.markdown('<div class="section-surface slide-up">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">What Midnight does</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Midnight is built to standardize policy creation and policy migration. It helps teams work faster, maintain cleaner structure, and reduce repetitive formatting effort when documentation needs to align to a template.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="soft-box"><strong>Use cases:</strong> policy migration, policy creation, document normalization, and controlled output preparation.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# MIGRATE
# =========================================================
elif st.session_state["page"] == "Migrate a Policy":
    st.markdown('<div class="workspace-header fade-in">', unsafe_allow_html=True)
    st.markdown('<div class="workspace-title">Migrate a Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="workspace-subtitle">Convert an existing document into a structured template.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    top_left, top_right = st.columns([0.35, 0.65], gap="medium")

    with top_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Settings</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-copy">Select a template and run a transformation against an uploaded source document.</div>', unsafe_allow_html=True)

        selected_template = st.selectbox(
            "Template",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="migrate_template",
        )
        st.session_state["selected_template"] = selected_template

        st.markdown(
            '<div class="soft-box">Upload a source document, transform it into the selected template, review the preview, and generate the final output.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with top_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Upload</div>', unsafe_allow_html=True)
        st.markdown('<div class="caption">Supported formats: .docx, .txt, .md</div>', unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload a legacy policy document",
            type=["docx", "txt", "md"],
            label_visibility="collapsed",
            key="migrate_upload",
        )

        render_logo_controls("migrate")

        run_migration = st.button("Transform Policy", key="run_migration")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Preview</div>', unsafe_allow_html=True)
    if st.session_state["migration_policy_data"]:
        render_policy_preview(st.session_state["migration_policy_data"])
    else:
        st.info("Upload a document and run the transform to preview the extracted policy.")
    st.markdown('</div>', unsafe_allow_html=True)

    if run_migration:
        if not uploaded_file:
            st.error("Please upload a legacy policy document.")
            st.stop()

        doc_text = get_uploaded_text(uploaded_file)
        if len(doc_text.strip()) < 50:
            st.error("Document appears to be empty or too short.")
            st.stop()

        policy_data = run_llm_transform(doc_text, st.session_state["selected_template"])
        if policy_data:
            st.session_state["migration_policy_data"] = policy_data
            st.success("Preview ready. Review the output, then generate the final document.")
            st.rerun()

    if st.session_state["migration_policy_data"]:
        st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
        a, b, c = st.columns([1, 1.2, 1])
        with b:
            if st.button("Generate Final Document", key="generate_migrated_doc"):
                try:
                    out_filename, docx_bytes = build_output_doc(
                        st.session_state["migration_policy_data"],
                        logo_path=st.session_state.get("logo_path"),
                    )
                    st.session_state["migration_filename"] = out_filename
                    st.session_state["migration_docx"] = docx_bytes
                except Exception as e:
                    st.error(f"Document build failed: {str(e)}")

            if "migration_docx" in st.session_state:
                st.markdown('<div class="success-box">✓ Transformation complete</div>', unsafe_allow_html=True)
                st.download_button(
                    label=f"Download {st.session_state['migration_filename']}",
                    data=st.session_state["migration_docx"],
                    file_name=st.session_state["migration_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_migrated_doc",
                )

# =========================================================
# CREATE
# =========================================================
else:
    st.markdown('<div class="workspace-header fade-in">', unsafe_allow_html=True)
    st.markdown('<div class="workspace-title">Create a Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="workspace-subtitle">Generate a new policy from structured intake.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    settings_col, form_col = st.columns([0.34, 0.66], gap="medium")

    with settings_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Settings</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-copy">Select a template and use structured intake with smart defaults before generating the preview.</div>', unsafe_allow_html=True)

        selected_template = st.selectbox(
            "Template",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="create_template",
        )
        st.session_state["selected_template"] = selected_template

        st.markdown(
            '<div class="soft-box">This page supports structured policy creation with auto-filled date relationships and validation before generation.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with form_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Intake</div>', unsafe_allow_html=True)

        with st.form("create_policy_form"):
            policy_name = st.text_input("Policy Name", value="")
            policy_number = st.text_input("Policy Number", value="")
            version = st.text_input("Version", value="V1.0")
            grc_id = st.text_input("GRC ID", value="")

            effective_date = st.text_input("Effective Date", value=date.today().strftime("%-m/%-d/%Y"))
            last_reviewed = st.text_input("Last Reviewed", value="")
            last_revised = st.text_input("Last Revised", value="")
            supersedes = st.text_input("Supersedes", value="")
            custodians = st.text_input("Custodians", value="")

            owner_name = st.text_input("Owner Name", value="")
            owner_title = st.text_input("Owner Title", value="")
            approver_name = st.text_input("Approver Name", value="")
            approver_title = st.text_input("Approver Title", value="")

            date_signed = st.text_input("Date Signed", value="")
            date_approved = st.text_input("Date Approved", value="")

            purpose = st.text_area("Purpose and Scope", value="", height=120)
            definitions_text = st.text_area("Definitions (one per line, format: Term: Definition)", value="", height=120)
            policy_statement = st.text_area("Policy Statement", value="", height=140)
            procedures_text = st.text_area("Procedures (one line per step; use '- ' for bullets)", value="", height=200)
            related_policies_text = st.text_area("Related Policies (one per line)", value="", height=100)
            citations_text = st.text_area("Citations / References (one per line)", value="", height=100)

            create_preview = st.form_submit_button("Build Preview")

        st.markdown('</div>', unsafe_allow_html=True)

    preview_defaults = {
        "last_reviewed": normalize_date_input(default_if_blank(last_reviewed, effective_date)),
        "last_revised": normalize_date_input(default_if_blank(last_revised, effective_date)),
        "date_signed": normalize_date_input(default_if_blank(date_signed, effective_date)),
        "date_approved": normalize_date_input(default_if_blank(date_approved, default_if_blank(date_signed, effective_date))),
    }

    st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

    summary_left, summary_right = st.columns([0.42, 0.58], gap="medium")

    with summary_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Smart Defaults</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="soft-box">
                <strong>Last Reviewed:</strong> {preview_defaults["last_reviewed"] or "—"}<br>
                <strong>Last Revised:</strong> {preview_defaults["last_revised"] or "—"}<br>
                <strong>Date Signed:</strong> {preview_defaults["date_signed"] or "—"}<br>
                <strong>Date Approved:</strong> {preview_defaults["date_approved"] or "—"}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with summary_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Preview</div>', unsafe_allow_html=True)
        if st.session_state["created_policy_data"]:
            render_policy_preview(st.session_state["created_policy_data"])
        else:
            st.info("Complete the intake form and build a preview to review the policy before generating the final document.")
        st.markdown('</div>', unsafe_allow_html=True)

    if create_preview:
        date_errors = validate_dates(
            effective_date,
            preview_defaults["last_reviewed"],
            preview_defaults["last_revised"],
            preview_defaults["date_signed"],
            preview_defaults["date_approved"],
        )

        if date_errors:
            for err in date_errors:
                st.error(err)
        else:
            created_policy_data = build_creation_policy_data(
                policy_name,
                policy_number,
                version,
                grc_id,
                supersedes,
                effective_date,
                last_reviewed,
                last_revised,
                custodians,
                owner_name,
                owner_title,
                approver_name,
                approver_title,
                date_signed,
                date_approved,
                purpose,
                definitions_text,
                policy_statement,
                procedures_text,
                related_policies_text,
                citations_text,
                st.session_state["selected_template"],
            )
            st.session_state["created_policy_data"] = created_policy_data
            st.success("Preview ready.")
            st.rerun()

    if st.session_state["created_policy_data"]:
        st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            if st.button("Generate Created Policy", key="generate_created_doc"):
                try:
                    out_filename, docx_bytes = build_output_doc(st.session_state["created_policy_data"])
                    st.session_state["created_filename"] = out_filename
                    st.session_state["created_docx"] = docx_bytes
                except Exception as e:
                    st.error(f"Document build failed: {str(e)}")

            if "created_docx" in st.session_state:
                st.markdown('<div class="success-box">✓ Policy generated</div>', unsafe_allow_html=True)
                st.download_button(
                    label=f"Download {st.session_state['created_filename']}",
                    data=st.session_state["created_docx"],
                    file_name=st.session_state["created_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_created_doc",
                )
