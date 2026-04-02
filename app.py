"""
MIDNIGHT — Policy Migration Engine
A product developed by Takeoff
"""

import os
import tempfile
import streamlit as st
from groq import Groq
from docx import Document
from hps_policy_migration_builder import build_policy_document

# ============================================================================
# API CONFIG
# ============================================================================
LOCAL_GROQ_API_KEY = ""


def get_api_key() -> str:
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""
    return secret_key or os.getenv("GROQ_API_KEY", "") or LOCAL_GROQ_API_KEY


# ============================================================================
# PROMPT CONFIG
# ============================================================================
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

# ============================================================================
# DEMO SAMPLE
# ============================================================================
DEMO_SOURCE_TEXT = """
SEC-P020 Mobile Device Management in the Workplace

Purpose:
This policy defines the requirements for managing mobile devices used to access company systems and data.

Definitions:
iGel: Thin client endpoint environment.
WYSE: Thin client platform.
Jail-broken: A mobile device that has been modified to bypass manufacturer restrictions.

Policy Statement:
All mobile devices used to access company systems must be approved, secured, and managed in accordance with company requirements.

Procedures:
1. Only approved mobile devices may connect to company email or applications.
2. Devices must use strong authentication.
3. Lost or stolen devices must be reported immediately.
4. Unsupported or jail-broken devices are prohibited.
5. Mobile device settings must align with security baselines.
6. Exceptions must be reviewed and approved.

Related Policies:
SEC-P001 Information Security Governing Policy
SEC-C002 Access Control Standard

Citations:
PCI DSS
HIPAA Security Rule
"""

DEMO_SCENARIO_AMY = """
**Amy (Compliance Manager):**  
“Hey Brian — we have audits coming up. We refined the template and need these documents updated.”
"""

DEMO_SCENARIO_BRIAN = """
**Brian (GRC):**  
“Got it.”

At this point, Brian has to manually review the documents, copy and paste content into the updated structure, validate formatting, and cross-reference the result.

**Manual effort:** 60–80 hours  
**Risk:** inconsistency, missed updates, audit pressure
"""

TEMPLATE_OPTIONS = [
    "Generic Policy Template",
    "Wipro HealthPlan Services (Current)",
]

PAGE_OPTIONS = ["Overview", "Workspace"]
WORKFLOW_OPTIONS = ["Demo Mode", "Migrate Policy", "Create Policy"]

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Midnight",
    page_icon="🌑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        :root {
            --app-bg: #f5f5f7;
            --panel-bg: #ffffff;
            --panel-soft: #fafafc;
            --text-main: #111111;
            --text-sub: #6e6e73;
            --border: rgba(0,0,0,0.07);
            --border-soft: rgba(0,0,0,0.05);
            --shadow: 0 10px 30px rgba(0,0,0,0.05);
        }

        .stApp {
            background: linear-gradient(180deg, #fbfbfc 0%, #f4f4f6 100%);
            color: var(--text-main);
        }

        .block-container {
            max-width: 1320px;
            margin: 0 auto;
            padding-top: 0.9rem;
            padding-bottom: 2rem;
        }

        header {visibility: hidden;}

        .topbar {
            background: rgba(255,255,255,0.78);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-soft);
            border-radius: 24px;
            padding: 1rem 1.15rem;
            margin-bottom: 1rem;
            box-shadow: var(--shadow);
        }

        .topbar-grid {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .topbar-eyebrow {
            color: #8e8e93;
            font-size: 0.72rem;
            letter-spacing: 0.24em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .topbar-title {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: #111111;
            margin-bottom: 0.15rem;
        }

        .topbar-subtitle {
            color: #6e6e73;
            font-size: 0.94rem;
        }

        .hero-shell {
            background: linear-gradient(180deg, rgba(255,255,255,.88), rgba(255,255,255,.78));
            border: 1px solid var(--border-soft);
            border-radius: 30px;
            box-shadow: var(--shadow);
            padding: 3rem 2rem 2.4rem 2rem;
            margin-bottom: 1rem;
        }

        .hero-eyebrow {
            color: #8e8e93;
            font-size: 0.74rem;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            margin-bottom: 0.8rem;
        }

        .hero-title {
            font-size: 4rem;
            font-weight: 700;
            line-height: 0.95;
            color: #111111;
            letter-spacing: 0.06em;
            margin-bottom: 0.9rem;
            text-transform: uppercase;
        }

        .hero-subtitle {
            color: #6e6e73;
            font-size: 1.05rem;
            max-width: 700px;
            line-height: 1.7;
            margin-bottom: 1.5rem;
        }

        .value-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-bottom: 1.4rem;
        }

        .value-pill {
            display: inline-block;
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            background: #ffffff;
            border: 1px solid var(--border);
            color: #5a5a5f;
            font-size: 0.78rem;
        }

        .card-grid-space {
            margin-top: 0.8rem;
        }

        .glass-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: var(--shadow);
            padding: 1.2rem;
            height: 100%;
        }

        .card-title {
            color: #111111;
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .card-copy {
            color: #6e6e73;
            font-size: 0.92rem;
            line-height: 1.65;
        }

        .demo-story {
            background: #fafafc;
            border: 1px solid var(--border-soft);
            border-radius: 18px;
            padding: 1rem;
            margin-top: 0.8rem;
        }

        .shell-card {
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 28px;
            box-shadow: var(--shadow);
            padding: 0;
            overflow: hidden;
        }

        .left-nav {
            background: linear-gradient(180deg, #fbfbfc 0%, #f1f1f4 100%);
            border-right: 1px solid var(--border-soft);
            min-height: 78vh;
            padding: 1.05rem;
        }

        .nav-section-label {
            color: #8e8e93;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .nav-hero {
            padding: 0.35rem 0 1rem 0;
            border-bottom: 1px solid var(--border-soft);
            margin-bottom: 1rem;
        }

        .nav-hero-title {
            font-size: 1.55rem;
            font-weight: 700;
            color: #111111;
            margin-bottom: 0.2rem;
        }

        .nav-hero-copy {
            color: #6e6e73;
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .nav-meta {
            padding: 0.9rem 0 0.85rem 0;
            border-bottom: 1px solid var(--border-soft);
            margin-bottom: 1rem;
        }

        .nav-pill {
            display: inline-block;
            padding: 0.32rem 0.66rem;
            border-radius: 999px;
            background: #ffffff;
            border: 1px solid var(--border);
            color: #5a5a5f;
            font-size: 0.75rem;
            margin-right: 0.35rem;
            margin-bottom: 0.45rem;
        }

        .content-pane {
            background: #ffffff;
            min-height: 78vh;
            padding: 1.1rem;
        }

        .pane-header {
            padding: 0.3rem 0 0.9rem 0;
            border-bottom: 1px solid var(--border-soft);
            margin-bottom: 1rem;
        }

        .pane-title {
            font-size: 1.45rem;
            font-weight: 700;
            color: #111111;
            margin-bottom: 0.2rem;
        }

        .pane-subtitle {
            color: #6e6e73;
            font-size: 0.92rem;
        }

        .panel-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1rem;
            box-shadow: 0 4px 18px rgba(0,0,0,0.03);
            height: 100%;
        }

        .preview-box {
            background: #fafafc;
            border: 1px solid var(--border-soft);
            border-radius: 18px;
            padding: 1rem;
        }

        .demo-box {
            background: linear-gradient(180deg, #fafafc 0%, #f6f6f8 100%);
            border: 1px solid var(--border-soft);
            border-radius: 18px;
            padding: 1rem;
        }

        .metric-box {
            background: #ffffff;
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            padding: 0.9rem;
            text-align: center;
        }

        .metric-number {
            font-size: 1.6rem;
            font-weight: 700;
            color: #111111;
            margin-bottom: 0.2rem;
        }

        .metric-label {
            color: #6e6e73;
            font-size: 0.82rem;
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

        .status-text {
            color: #6e6e73;
            text-align: center;
            font-style: italic;
            font-size: 0.88rem;
        }

        .caption-text {
            color: #8e8e93;
            font-size: 0.8rem;
            margin-bottom: 0.65rem;
        }

        .subtle-note {
            color: #6e6e73;
            font-size: 0.88rem;
            line-height: 1.55;
            background: #fafafc;
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            padding: 0.85rem 0.95rem;
            margin: 0.55rem 0 0.85rem 0;
        }

        .divider-space {
            height: 0.55rem;
        }

        .nav-spacer {
            height: 0.5rem;
        }

        .workflow-help {
            color: #6e6e73;
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .stButton > button {
            width: 100% !important;
            background: #111111 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.92rem 1rem !important;
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
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            padding: 0.92rem 1rem !important;
            font-weight: 600 !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
        }

        .stFileUploader > div {
            background: #fafafc !important;
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
            padding: 0.75rem 0.85rem !important;
            transition: all .15s ease;
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
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        }

        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #111111 !important;
        }

        h1, h2, h3 {
            color: #111111 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# HELPERS
# ============================================================================
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


def split_lines(text: str):
    return [line.strip() for line in text.splitlines() if line.strip()]


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
        "hps_inc": template_name == "Wipro HealthPlan Services (Current)",
        "agency": True,
        "corporate": True,
        "govt_affairs": False,
        "legal_review": False,
    }

    return {
        "policy_name": policy_name,
        "policy_number": policy_number,
        "version": version,
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

    st.markdown("#### Purpose")
    st.write(policy_data.get("purpose", ""))

    st.markdown("#### Policy Statement")
    st.write(policy_data.get("policy_statement", ""))

    st.markdown("#### Definitions")
    definitions = policy_data.get("definitions", {})
    if definitions:
        for key, value in definitions.items():
            st.markdown(f"- **{key}:** {value}")
    else:
        st.write("No definitions captured.")

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


def run_llm_transform(source_text: str, template_name: str):
    api_key = get_api_key()
    if not api_key:
        st.error("No Groq API key found. Set GROQ_API_KEY in Streamlit secrets or use the local fallback for testing.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    try:
        status.markdown('<div class="status-text">Reading document…</div>', unsafe_allow_html=True)
        progress.progress(15)

        client = Groq(api_key=api_key)

        status.markdown('<div class="status-text">Extracting policy structure…</div>', unsafe_allow_html=True)
        progress.progress(35)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + "\n\n" + source_text,
                }
            ],
            temperature=0.1,
            max_tokens=8000,
        )

        raw_output = response.choices[0].message.content.strip()

        status.markdown('<div class="status-text">Parsing extracted data…</div>', unsafe_allow_html=True)
        progress.progress(60)

        policy_data = parse_policy_data(raw_output)

        if not policy_data:
            st.error("The model response could not be parsed into POLICY_DATA.")
            with st.expander("Raw model output"):
                st.code(raw_output)
            st.stop()

        policy_data["template_name"] = template_name

        status.markdown('<div class="status-text">Preview ready…</div>', unsafe_allow_html=True)
        progress.progress(100)
        status.empty()

        return policy_data

    except Exception as e:
        st.error(f"Midnight failed: {str(e)}")
        return None


# ============================================================================
# STATE
# ============================================================================
if "selected_template" not in st.session_state:
    st.session_state["selected_template"] = TEMPLATE_OPTIONS[0]

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Overview"

if "active_mode" not in st.session_state:
    st.session_state["active_mode"] = "Demo Mode"

if "demo_policy_data" not in st.session_state:
    st.session_state["demo_policy_data"] = None


# ============================================================================
# TOP BAR
# ============================================================================
st.markdown('<div class="topbar">', unsafe_allow_html=True)
st.markdown('<div class="topbar-grid">', unsafe_allow_html=True)

with st.container():
    left_top, right_top = st.columns([0.72, 0.28])

    with left_top:
        st.markdown('<div class="topbar-eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
        st.markdown('<div class="topbar-title">MIDNIGHT</div>', unsafe_allow_html=True)
        st.markdown('<div class="topbar-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

    with right_top:
        selected_page = st.radio(
            "Page Navigation",
            PAGE_OPTIONS,
            horizontal=True,
            label_visibility="collapsed",
            index=PAGE_OPTIONS.index(st.session_state["selected_page"]),
            key="page_nav",
        )
        st.session_state["selected_page"] = selected_page

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# OVERVIEW PAGE
# ============================================================================
if st.session_state["selected_page"] == "Overview":
    st.markdown('<div class="hero-shell">', unsafe_allow_html=True)
    st.markdown('<div class="hero-eyebrow">Policy Intelligence Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">MIDNIGHT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">'
        'Automate policy creation, migration, and audit readiness through a controlled documentation workflow.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="value-strip">', unsafe_allow_html=True)
    st.markdown('<span class="value-pill">Reduce audit prep time</span>', unsafe_allow_html=True)
    st.markdown('<span class="value-pill">Standardize policy workflows</span>', unsafe_allow_html=True)
    st.markdown('<span class="value-pill">Generate structured output</span>', unsafe_allow_html=True)
    st.markdown('<span class="value-pill">Support procedures, runbooks, and playbooks</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    hero_cta_left, hero_cta_right = st.columns([0.2, 0.2])
    with hero_cta_left:
        if st.button("Enter Workspace", key="enter_workspace"):
            st.session_state["selected_page"] = "Workspace"
            st.rerun()
    with hero_cta_right:
        if st.button("Open Demo", key="open_demo"):
            st.session_state["selected_page"] = "Workspace"
            st.session_state["active_mode"] = "Demo Mode"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    cards_left, cards_mid, cards_right = st.columns(3)

    with cards_left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Migrate Policy</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-copy">Convert legacy policy documents into the selected template structure without manual rework and formatting cleanup.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with cards_mid:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Create Policy</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-copy">Generate a new policy from structured intake and produce a controlled .docx output aligned to the selected template.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with cards_right:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Runbooks & Procedures</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-copy">Extend the same engine beyond policies to support procedures, runbooks, playbooks, and broader security documentation.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-grid-space"></div>', unsafe_allow_html=True)

    story_left, story_right = st.columns([0.56, 0.44])

    with story_left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Why it matters</div>', unsafe_allow_html=True)
        st.markdown('<div class="demo-story">', unsafe_allow_html=True)
        st.markdown(DEMO_SCENARIO_AMY)
        st.markdown("---")
        st.markdown(DEMO_SCENARIO_BRIAN)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with story_right:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">What Midnight changes</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-copy">'
            'Instead of spending 60–80 hours manually updating documents when templates change, teams can move through a guided workflow, review the preview, and generate structured output in seconds.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="subtle-note"><strong>Positioning:</strong> Midnight turns compliance documentation from manual effort into a controlled system.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# WORKSPACE PAGE
# ============================================================================
else:
    st.markdown('<div class="shell-card">', unsafe_allow_html=True)
    left_col, right_col = st.columns([0.28, 0.72], gap="small")

    with left_col:
        st.markdown('<div class="left-nav">', unsafe_allow_html=True)

        st.markdown('<div class="nav-hero">', unsafe_allow_html=True)
        st.markdown('<div class="nav-hero-title">Workspace</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="nav-hero-copy">Choose a workflow, select a template, review the preview, then generate the final document.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="nav-section-label">Template</div>', unsafe_allow_html=True)
        selected_template = st.selectbox(
            "Template Target",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="left_template_selector",
            label_visibility="collapsed",
        )
        st.session_state["selected_template"] = selected_template

        st.markdown('<div class="nav-meta">', unsafe_allow_html=True)
        st.markdown('<span class="nav-pill">Demo Story</span>', unsafe_allow_html=True)
        st.markdown('<span class="nav-pill">.docx Upload</span>', unsafe_allow_html=True)
        st.markdown('<span class="nav-pill">Preview</span>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="nav-section-label">Workflow</div>', unsafe_allow_html=True)
        mode = st.radio(
            "Workflow",
            WORKFLOW_OPTIONS,
            label_visibility="collapsed",
            index=WORKFLOW_OPTIONS.index(st.session_state["active_mode"]),
        )
        st.session_state["active_mode"] = mode

        st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="workflow-help">Start with Demo Mode to tell the story, then move into migration or policy creation.</div>',
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="content-pane">', unsafe_allow_html=True)

        if st.session_state["active_mode"] == "Demo Mode":
            st.markdown('<div class="pane-header">', unsafe_allow_html=True)
            st.markdown('<div class="pane-title">Demo Mode</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="pane-subtitle">Show the compliance problem, the workflow shift, and the output in one guided flow.</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

            story_left, story_right = st.columns([0.54, 0.46], gap="medium")

            with story_left:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Audit Preparation Scenario")
                st.markdown('<div class="demo-box">', unsafe_allow_html=True)
                st.markdown(DEMO_SCENARIO_AMY)
                st.markdown("---")
                st.markdown(DEMO_SCENARIO_BRIAN)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with story_right:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Business Impact")
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown('<div class="metric-box"><div class="metric-number">80h</div><div class="metric-label">Manual effort avoided</div></div>', unsafe_allow_html=True)
                with m2:
                    st.markdown('<div class="metric-box"><div class="metric-number">1</div><div class="metric-label">Controlled workflow</div></div>', unsafe_allow_html=True)
                with m3:
                    st.markdown('<div class="metric-box"><div class="metric-number">Seconds</div><div class="metric-label">To structured output</div></div>', unsafe_allow_html=True)
                st.markdown('<div class="subtle-note">This demo shows how Midnight converts a legacy policy into a structured, audit-ready document instead of forcing manual rework during audit preparation.</div>', unsafe_allow_html=True)
                if st.button("Run Demo", key="run_demo"):
                    st.session_state["demo_policy_data"] = run_llm_transform(
                        DEMO_SOURCE_TEXT,
                        st.session_state["selected_template"],
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)

            demo_left, demo_right = st.columns([0.5, 0.5], gap="medium")

            with demo_left:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Before")
                st.markdown('<div class="preview-box">', unsafe_allow_html=True)
                st.code(DEMO_SOURCE_TEXT, language="text")
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with demo_right:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### After")
                if st.session_state["demo_policy_data"]:
                    render_policy_preview(st.session_state["demo_policy_data"])
                else:
                    st.info("Run the demo to show the transformed output.")
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state["demo_policy_data"]:
                st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
                a, b, c = st.columns([1, 1.25, 1])
                with b:
                    if st.button("Generate Demo Document", key="generate_demo_doc"):
                        try:
                            out_filename, docx_bytes = build_output_doc(st.session_state["demo_policy_data"])
                            st.session_state["demo_filename"] = out_filename
                            st.session_state["demo_docx"] = docx_bytes
                        except Exception as e:
                            st.error(f"Document build failed: {str(e)}")

                    if "demo_docx" in st.session_state:
                        st.markdown('<div class="success-box">✓ Demo complete</div>', unsafe_allow_html=True)
                        st.download_button(
                            label=f"Download {st.session_state['demo_filename']}",
                            data=st.session_state["demo_docx"],
                            file_name=st.session_state["demo_filename"],
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="download_demo_doc",
                        )

        elif st.session_state["active_mode"] == "Migrate Policy":
            st.markdown('<div class="pane-header">', unsafe_allow_html=True)
            st.markdown('<div class="pane-title">Migrate Policy</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="pane-subtitle">Convert an existing document into the selected template · {st.session_state["selected_template"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

            content_left, content_right = st.columns([1.02, 0.98], gap="medium")

            with content_left:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Upload")
                st.markdown(
                    '<div class="caption-text">Supported formats: .docx, .txt, .md</div>',
                    unsafe_allow_html=True,
                )

                uploaded_file = st.file_uploader(
                    "Upload a legacy policy document",
                    type=["docx", "txt", "md"],
                    label_visibility="collapsed",
                    key="migrate_upload",
                )

                run_migration = st.button("Transform Policy", key="run_migration")
                st.markdown("</div>", unsafe_allow_html=True)

            with content_right:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Preview")
                if "migration_policy_data" in st.session_state:
                    render_policy_preview(st.session_state["migration_policy_data"])
                else:
                    st.info("Run a migration to preview the extracted policy before generating the final document.")
                st.markdown("</div>", unsafe_allow_html=True)

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

            if "migration_policy_data" in st.session_state:
                st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
                a, b, c = st.columns([1, 1.25, 1])
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

        else:
            st.markdown('<div class="pane-header">', unsafe_allow_html=True)
            st.markdown('<div class="pane-title">Create Policy</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="pane-subtitle">Generate a new document from structured intake · {st.session_state["selected_template"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

            form_col, preview_col = st.columns([1.02, 0.98], gap="medium")

            with form_col:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Intake")

                with st.form("create_policy_form"):
                    policy_name = st.text_input("Policy Name")
                    meta1, meta2, meta3 = st.columns(3)
                    with meta1:
                        policy_number = st.text_input("Policy Number")
                    with meta2:
                        version = st.text_input("Version", value="V1.0")
                    with meta3:
                        grc_id = st.text_input("GRC ID")

                    meta4, meta5, meta6 = st.columns(3)
                    with meta4:
                        effective_date = st.text_input("Effective Date")
                    with meta5:
                        last_reviewed = st.text_input("Last Reviewed")
                    with meta6:
                        last_revised = st.text_input("Last Revised")

                    supersedes = st.text_input("Supersedes")
                    custodians = st.text_input("Custodians")

                    owner1, owner2 = st.columns(2)
                    with owner1:
                        owner_name = st.text_input("Owner Name")
                    with owner2:
                        owner_title = st.text_input("Owner Title")

                    approver1, approver2 = st.columns(2)
                    with approver1:
                        approver_name = st.text_input("Approver Name")
                    with approver2:
                        approver_title = st.text_input("Approver Title")

                    signed1, signed2 = st.columns(2)
                    with signed1:
                        date_signed = st.text_input("Date Signed")
                    with signed2:
                        date_approved = st.text_input("Date Approved")

                    purpose = st.text_area("Purpose", height=120)
                    definitions_text = st.text_area(
                        "Definitions (one per line, format: Term: Definition)",
                        height=120,
                    )
                    policy_statement = st.text_area("Policy Statement", height=140)
                    procedures_text = st.text_area(
                        "Procedures (one line per step; use '- ' for bullets)",
                        height=220,
                    )
                    related_policies_text = st.text_area(
                        "Related Policies (one per line)",
                        height=100,
                    )
                    citations_text = st.text_area(
                        "Citations / References (one per line)",
                        height=100,
                    )

                    create_preview = st.form_submit_button("Build Preview")

                st.markdown("</div>", unsafe_allow_html=True)

                if create_preview:
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

            with preview_col:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### Preview")
                if "created_policy_data" in st.session_state:
                    render_policy_preview(st.session_state["created_policy_data"])
                else:
                    st.info("Complete the intake form and build a preview to review the policy before generating the final document.")
                st.markdown("</div>", unsafe_allow_html=True)

            if "created_policy_data" in st.session_state:
                st.markdown('<div class="divider-space"></div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 1.25, 1])
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

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)