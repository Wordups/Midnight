import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<style>

/* ===== GLOBAL INPUT FIX ===== */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1px solid rgba(0,0,0,0.14) !important;
    border-radius: 14px !important;
}

/* ===== LABEL FIX ===== */
[data-testid="stWidgetLabel"] p {
    color: #111111 !important;
    font-weight: 600 !important;
}

/* ===== PLACEHOLDER FIX ===== */
input::placeholder,
textarea::placeholder {
    color: #8a8a8f !important;
    opacity: 1 !important;
}

</style>
""", unsafe_allow_html=True)
import os
import io
import tempfile
from datetime import datetime

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
        "hps_inc": True,
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

st.markdown(
    """
    <style>
        :root {
            --bg: #f5f5f7;
            --surface: #ffffff;
            --surface-soft: #f2f2f4;
            --surface-muted: #fafafc;
            --text: #111111;
            --subtext: #6e6e73;
            --line: rgba(0,0,0,0.08);
            --line-soft: rgba(0,0,0,0.05);
            --shadow: 0 10px 28px rgba(0,0,0,0.05);
            --shadow-soft: 0 4px 16px rgba(0,0,0,0.03);
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        .block-container {
            max-width: 1220px;
            padding-top: 0.9rem;
            padding-bottom: 2rem;
        }

        header {visibility: hidden;}

        .topbar {
            background: rgba(255,255,255,0.82);
            border: 1px solid var(--line-soft);
            border-radius: 18px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: var(--shadow-soft);
        }

        .eyebrow {
            color: #8e8e93;
            font-size: 0.72rem;
            letter-spacing: 0.24em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .brand {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            color: var(--text);
            margin-bottom: 0.08rem;
        }

        .subbrand {
            color: var(--subtext);
            font-size: 0.95rem;
        }

        .hero {
            background: linear-gradient(180deg, #ffffff 0%, #f9f9fb 100%);
            border: 1px solid var(--line-soft);
            border-radius: 26px;
            padding: 2.4rem 2rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }

        .hero-title {
            font-size: 3.6rem;
            font-weight: 700;
            line-height: 0.95;
            color: var(--text);
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }

        .hero-copy {
            max-width: 760px;
            color: var(--subtext);
            font-size: 1.04rem;
            line-height: 1.72;
            margin-bottom: 1rem;
        }

        .pill-row {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-bottom: 1.15rem;
        }

        .pill {
            display: inline-block;
            padding: 0.38rem 0.78rem;
            border-radius: 999px;
            background: var(--surface-muted);
            border: 1px solid var(--line-soft);
            color: #5f5f64;
            font-size: 0.78rem;
        }

        .section {
            background: var(--surface);
            border: 1px solid var(--line-soft);
            border-radius: 22px;
            box-shadow: var(--shadow-soft);
            padding: 1.2rem;
            height: 100%;
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.3rem;
        }

        .section-copy {
            color: var(--subtext);
            font-size: 0.94rem;
            line-height: 1.65;
            margin-bottom: 0.9rem;
        }

        .feature-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.35rem;
        }

        .feature-copy {
            color: var(--subtext);
            font-size: 0.92rem;
            line-height: 1.62;
        }

        .soft-box {
            background: var(--surface-muted);
            border: 1px solid var(--line-soft);
            border-radius: 16px;
            padding: 0.95rem 1rem;
        }

        .workspace-header {
            margin-bottom: 1rem;
        }

        .workspace-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.2rem;
        }

        .workspace-subtitle {
            color: var(--subtext);
            font-size: 0.94rem;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--line-soft);
            border-radius: 20px;
            padding: 1rem;
            box-shadow: var(--shadow-soft);
            height: 100%;
        }

        .preview-box {
            background: var(--surface-muted);
            border: 1px solid var(--line-soft);
            border-radius: 16px;
            padding: 1rem;
        }

        .caption {
            color: #8e8e93;
            font-size: 0.8rem;
            margin-bottom: 0.65rem;
        }

        .success-box {
            background: #eefaf1;
            border: 1px solid #cfead7;
            border-radius: 14px;
            padding: 0.85rem 1rem;
            color: #1d7a3b;
            text-align: center;
            font-weight: 600;
            margin-top: 0.9rem;
        }

        .divider-space {
            height: 0.75rem;
        }

        .stButton > button {
            width: 100% !important;
            background: #111111 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.9rem 1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 8px 16px rgba(0,0,0,0.08) !important;
        }

        .stButton > button:hover {
            background: #000000 !important;
        }

        .stDownloadButton > button {
            width: 100% !important;
            background: #f2f2f4 !important;
            color: #111111 !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
            padding: 0.9rem 1rem !important;
            font-weight: 600 !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
        }

        .stFileUploader > div {
            background: var(--surface-muted) !important;
            border: 1px dashed rgba(0,0,0,0.15) !important;
            border-radius: 14px !important;
        }

        .stProgress > div > div {
            background-color: #111111 !important;
        }

        div[data-testid="stRadio"] > div {
            gap: 0.35rem;
        }

        div[data-testid="stRadio"] label {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 14px !important;
            padding: 0.62rem 0.85rem !important;
        }

        div[data-testid="stRadio"] label:hover {
            background: rgba(0,0,0,0.03) !important;
        }

        div[data-testid="stRadio"] label p {
            color: #3a3a3c !important;
            font-weight: 600 !important;
        }

        div[data-testid="stRadio"] label:has(input:checked) {
            background: #ffffff !important;
            border: 1px solid var(--line) !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        }

        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #111111 !important;
        }

        h1, h2, h3 {
            color: #111111 !important;
        }

        @media (max-width: 768px) {
            .hero-title {
                font-size: 2.6rem;
            }
            .hero {
                padding: 1.6rem 1.2rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
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

# =========================================================
# HELPERS
# =========================================================
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


def build_output_doc(policy_data):
    policy_name = policy_data.get("policy_name", "Policy")
    policy_number = policy_data.get("policy_number", "SEC-P")
    version = policy_data.get("version", "V1.0")
    out_filename = f"{policy_number} {policy_name} {version}-NEW.docx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name

    build_policy_document(policy_data, tmp_path)

    with open(tmp_path, "rb") as f:
        docx_bytes = f.read()

    return out_filename, docx_bytes


def get_api_key() -> str:
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""
    return secret_key or os.getenv("GROQ_API_KEY", "") or LOCAL_GROQ_API_KEY


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
            messages=[{"role": "user", "content": EXTRACTION_PROMPT + "\n\n" + source_text}],
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
# TOP BAR
# =========================================================
st.markdown('<div class="topbar">', unsafe_allow_html=True)
top_left, top_right = st.columns([0.72, 0.28])

with top_left:
    st.markdown('<div class="eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand">MIDNIGHT</div>', unsafe_allow_html=True)
    st.markdown('<div class="subbrand">Policy Migration Engine</div>', unsafe_allow_html=True)

with top_right:
    page_choice = st.radio(
        "Navigation",
        PAGE_OPTIONS,
        horizontal=True,
        label_visibility="collapsed",
        index=PAGE_OPTIONS.index(st.session_state["page"]),
    )
    st.session_state["page"] = page_choice

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# OVERVIEW PAGE
# =========================================================
if st.session_state["page"] == "Overview":
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Policy Intelligence Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">MIDNIGHT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Automate policy creation and policy migration through a controlled documentation workflow built for consistency, speed, and audit readiness.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="pill-row">', unsafe_allow_html=True)
    st.markdown('<span class="pill">Reduce audit prep time</span>', unsafe_allow_html=True)
    st.markdown('<span class="pill">Standardize policy workflows</span>', unsafe_allow_html=True)
    st.markdown('<span class="pill">Generate structured output</span>', unsafe_allow_html=True)
    st.markdown('<span class="pill">Support repeatable documentation</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([0.24, 0.24])
    with c1:
        if st.button("Migrate a Policy", key="go_migrate"):
            st.session_state["page"] = "Migrate a Policy"
            st.rerun()
    with c2:
        if st.button("Create a Policy", key="go_create"):
            st.session_state["page"] = "Create a Policy"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="feature-title">Migrate Policy</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-copy">Upload an existing document and convert it into a structured template without manual copy-and-paste rework.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with r1c2:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="feature-title">Create Policy</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-copy">Generate a new policy from structured intake with smart defaults, preview, and controlled output.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with r1c3:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="feature-title">How it works</div>', unsafe_allow_html=True)
        st.markdown('<div class="feature-copy">Select a template, upload or create content, review the preview, and generate the final document.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([0.56, 0.44])
    with bottom_left:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">What it does</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Midnight helps teams replace repetitive policy formatting work with a cleaner, controlled workflow. Instead of rebuilding documents by hand when templates change, teams can transform content, review it quickly, and produce a standardized final output.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with bottom_right:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Why it matters</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="soft-box">Policy work slows down when formatting, structure, and repeated manual updates consume time. Midnight is designed to reduce that burden and create a cleaner path from source content to final document.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# MIGRATE PAGE
# =========================================================
elif st.session_state["page"] == "Migrate a Policy":
    st.markdown('<div class="workspace-header">', unsafe_allow_html=True)
    st.markdown('<div class="workspace-title">Migrate a Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="workspace-subtitle">Convert an existing document into a structured template.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    top_left, top_right = st.columns([0.38, 0.62], gap="medium")

    with top_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Settings")
        selected_template = st.selectbox(
            "Template",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="migrate_template",
        )
        st.session_state["selected_template"] = selected_template
        st.markdown('<div class="soft-box">Use this page to upload a source document, transform it into the selected template, review the result, and generate the final output.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with top_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Upload")
        st.markdown('<div class="caption">Supported formats: .docx, .txt, .md</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload a legacy policy document",
            type=["docx", "txt", "md"],
            label_visibility="collapsed",
            key="migrate_upload",
        )
        run_migration = st.button("Transform Policy", key="run_migration")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

    preview_col = st.container()
    with preview_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Preview")
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

    if st.session_state["migration_policy_data"]:
        st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
        a, b, c = st.columns([1, 1.2, 1])
        with b:
            if st.button("Generate Final Document", key="generate_migrated_doc"):
                try:
                    out_filename, docx_bytes = build_output_doc(st.session_state["migration_policy_data"])
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
# CREATE PAGE
# =========================================================
else:
    st.markdown('<div class="workspace-header">', unsafe_allow_html=True)
    st.markdown('<div class="workspace-title">Create a Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="workspace-subtitle">Generate a new policy from structured intake.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    settings_col, form_col = st.columns([0.34, 0.66], gap="medium")

    with settings_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Settings")
        selected_template = st.selectbox(
            "Template",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="create_template",
        )
        st.session_state["selected_template"] = selected_template
        st.markdown('<div class="soft-box">This page supports structured policy creation with smart defaults and date validation before generation.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with form_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("### Intake")

        with st.form("create_policy_form"):
            policy_name = st.text_input("Policy Name", value="Mobile Integration")
            policy_number = st.text_input("Policy Number", value="PE-1")
            version = st.text_input("Version", value="V1.0")
            grc_id = st.text_input("GRC ID", value="")

            effective_date = st.text_input("Effective Date", value="4/1/2026")
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
        st.markdown("### Smart Defaults")
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
        st.markdown("### Preview")
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
