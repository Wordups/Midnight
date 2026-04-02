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
# Leave blank for Streamlit Cloud / production.
# For local testing only, you may paste your key between the quotes.
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
            --bg-0: #020202;
            --bg-1: #080808;
            --bg-2: #0d0d0d;
            --bg-3: #111111;
            --line: #1f1f1f;
            --line-soft: #2a2a2a;
            --text: #f5f5f7;
            --muted: #9a9aa0;
            --muted-2: #727277;
            --accent: #ffffff;
        }

        .stApp {
            background:
                radial-gradient(circle at top, #1a1a1c 0%, #0b0b0d 38%, #020202 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 1120px;
            margin: 0 auto;
            padding-top: 1.05rem;
            padding-bottom: 2rem;
        }

        header {visibility: hidden;}

        .hero-shell {
            background:
                linear-gradient(180deg, rgba(13,13,14,.96), rgba(8,8,9,.98));
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 28px;
            padding: 1.35rem 1.35rem 1.2rem 1.35rem;
            box-shadow:
                0 20px 60px rgba(0,0,0,.34),
                inset 0 1px 0 rgba(255,255,255,.03);
            margin-bottom: 1rem;
            backdrop-filter: blur(10px);
        }

        .eyebrow {
            text-align: center;
            color: #7f7f85;
            font-size: 0.74rem;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            margin-bottom: 0.52rem;
        }

        .hero-title {
            text-align: center;
            color: #ffffff;
            font-size: 3.25rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            margin-bottom: 0.10rem;
            text-transform: uppercase;
        }

        .hero-subtitle {
            text-align: center;
            color: #a4a4aa;
            font-size: 0.94rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.95rem;
        }

        .hero-copy {
            max-width: 760px;
            margin: 0 auto 1rem auto;
            text-align: center;
            color: #b3b3b8;
            font-size: 0.98rem;
            line-height: 1.72;
        }

        .glass-card {
            background: linear-gradient(180deg, rgba(16,16,17,.96), rgba(11,11,12,.96));
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 22px;
            padding: 1rem;
            height: 100%;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,.03),
                0 10px 30px rgba(0,0,0,.18);
        }

        .card-title {
            color: #ffffff;
            font-weight: 700;
            font-size: 0.98rem;
            margin-bottom: 0.55rem;
        }

        .card-copy {
            color: #9a9aa0;
            font-size: 0.89rem;
            line-height: 1.64;
        }

        .chip {
            display: inline-block;
            padding: 0.34rem 0.72rem;
            border-radius: 999px;
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.08);
            color: #b3b3b8;
            font-size: 0.75rem;
            margin-right: 0.4rem;
            margin-bottom: 0.45rem;
        }

        .steps-shell {
            background: linear-gradient(180deg, rgba(15,15,16,.96), rgba(10,10,11,.96));
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 20px;
            padding: 0.92rem 1rem;
            margin-top: 0.92rem;
        }

        .step-pill {
            display: inline-block;
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.08);
            color: #d4d4d8;
            border-radius: 999px;
            padding: 0.30rem 0.70rem;
            font-size: 0.75rem;
            margin-right: 0.42rem;
            margin-bottom: 0.35rem;
        }

        .section-shell {
            background: linear-gradient(180deg, rgba(12,12,13,.97), rgba(8,8,9,.98));
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 26px;
            padding: 1.1rem;
            box-shadow:
                0 18px 48px rgba(0,0,0,.28),
                inset 0 1px 0 rgba(255,255,255,.02);
        }

        .panel-card {
            background: linear-gradient(180deg, rgba(16,16,17,.96), rgba(11,11,12,.96));
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 20px;
            padding: 1rem;
            height: 100%;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,.02),
                0 8px 22px rgba(0,0,0,.16);
        }

        .preview-box {
            background: linear-gradient(180deg, rgba(10,10,11,1), rgba(7,7,8,1));
            border: 1px solid rgba(255,255,255,.05);
            border-radius: 16px;
            padding: 1rem;
        }

        .note {
            color: #8f8f94;
            font-size: 0.86rem;
            line-height: 1.58;
            background: rgba(255,255,255,.02);
            border: 1px solid rgba(255,255,255,.05);
            border-radius: 16px;
            padding: 0.86rem 0.95rem;
            margin: 0.55rem 0 0.9rem 0;
        }

        .success-box {
            background: linear-gradient(180deg, rgba(17,38,22,.95), rgba(11,24,14,.95));
            border: 1px solid rgba(110,225,140,.24);
            border-radius: 16px;
            padding: 0.95rem 1rem;
            color: #84e79a;
            text-align: center;
            font-weight: 700;
            margin-top: 0.9rem;
        }

        .status-text {
            color: #9c9ca1;
            text-align: center;
            font-style: italic;
            font-size: 0.88rem;
        }

        .caption-text {
            color: #6d6d72;
            font-size: 0.81rem;
            margin-bottom: 0.7rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            margin-bottom: 0.4rem;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,.02);
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 14px;
            padding: 0.60rem 0.95rem;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(255,255,255,.05) !important;
            border-color: rgba(255,255,255,.12) !important;
        }

        .stButton > button {
            width: 100% !important;
            border-radius: 14px !important;
            border: none !important;
            background: linear-gradient(180deg, #ffffff 0%, #e6e6e8 100%) !important;
            color: #000000 !important;
            font-weight: 700 !important;
            letter-spacing: 0.03em !important;
            padding: 0.92rem 1rem !important;
            box-shadow:
                0 12px 26px rgba(255,255,255,.05),
                inset 0 1px 0 rgba(255,255,255,.5) !important;
        }

        .stDownloadButton > button {
            width: 100% !important;
            border-radius: 14px !important;
            border: 1px solid rgba(255,255,255,.10) !important;
            background: linear-gradient(180deg, rgba(22,22,23,1), rgba(14,14,15,1)) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            padding: 0.90rem 1rem !important;
        }

        .stFileUploader > div {
            background: rgba(255,255,255,.02) !important;
            border: 1px dashed rgba(255,255,255,.12) !important;
            border-radius: 16px !important;
        }

        .stProgress > div > div {
            background-color: #ffffff !important;
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stDateInput input {
            border-radius: 14px !important;
            background: rgba(255,255,255,.02) !important;
            border: 1px solid rgba(255,255,255,.07) !important;
        }

        h1, h2, h3 {
            margin-bottom: 0.45rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# TEMPLATE OPTIONS
# ============================================================================
TEMPLATE_OPTIONS = [
    "Generic Policy Template",
    "Wipro HealthPlan Services (Current)",
]


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
    else:
        st.write("No procedures captured.")

    st.markdown("#### Related Policies")
    related = policy_data.get("related_policies", [])
    if related:
        for item in related:
            st.markdown(f"- {item}")
    else:
        st.write("No related policies captured.")

    st.markdown("#### Citations")
    citations = policy_data.get("citations", [])
    if citations:
        for item in citations:
            st.markdown(f"- {item}")
    else:
        st.write("No citations captured.")

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


# ============================================================================
# STATE
# ============================================================================
if "selected_template" not in st.session_state:
    st.session_state["selected_template"] = TEMPLATE_OPTIONS[0]


# ============================================================================
# HERO / HOMEPAGE
# ============================================================================
st.markdown('<div class="hero-shell">', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">MIDNIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="hero-copy">'
    'Standardize legacy policies, generate new policies from structured intake, and review output before download. '
    'Midnight is designed to reduce manual policy rework during audit preparation with a cleaner, controlled workflow.'
    '</div>',
    unsafe_allow_html=True,
)

top_left, top_mid, top_right = st.columns([1.3, 1, 1])

with top_left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">How to Use Midnight</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-copy">'
        'Choose a workflow below. Use <strong>Migrate Policy</strong> to convert an existing document into the selected template. '
        'Use <strong>Create Policy</strong> to generate a new policy from structured intake. '
        'Preview the output before generating the final .docx document.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with top_mid:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Current Capabilities</div>', unsafe_allow_html=True)
    st.markdown('<span class="chip">.docx Upload</span>', unsafe_allow_html=True)
    st.markdown('<span class="chip">Migration</span>', unsafe_allow_html=True)
    st.markdown('<span class="chip">Policy Creation</span>', unsafe_allow_html=True)
    st.markdown('<span class="chip">Preview</span>', unsafe_allow_html=True)
    st.markdown('<span class="chip">Template Selection</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with top_right:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Template Target</div>', unsafe_allow_html=True)
    selected_template = st.selectbox(
        "Template Selector",
        TEMPLATE_OPTIONS,
        index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
        label_visibility="collapsed",
        key="hero_template_selector",
    )
    st.session_state["selected_template"] = selected_template
    st.markdown(
        '<div class="card-copy" style="margin-top:0.55rem;">'
        'Generic Policy Template is available for neutral builds. '
        'Wipro HealthPlan Services remains available as the current org-specific target.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="steps-shell">'
    '<span class="step-pill">1 · Select Template</span>'
    '<span class="step-pill">2 · Select Workflow</span>'
    '<span class="step-pill">3 · Upload or Create</span>'
    '<span class="step-pill">4 · Review Preview</span>'
    '<span class="step-pill">5 · Generate Final Output</span>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)


# ============================================================================
# WORKSPACE
# ============================================================================
st.markdown('<div class="section-shell">', unsafe_allow_html=True)
tab_migrate, tab_create = st.tabs(["Migrate Policy", "Create Policy"])

with tab_migrate:
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Upload Legacy Policy")
        st.markdown(
            f'<div class="caption-text">Target template: {st.session_state["selected_template"]} · Supported formats: .docx, .txt, .md</div>',
            unsafe_allow_html=True,
        )

        migrate_template = st.selectbox(
            "Migrate Template",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="migrate_template_selector",
        )
        st.session_state["selected_template"] = migrate_template

        uploaded_file = st.file_uploader(
            "Upload a legacy policy document",
            type=["docx", "txt", "md"],
            label_visibility="collapsed",
            key="migrate_upload",
        )

        st.markdown(
            '<div class="note"><strong>System note:</strong> API access should be configured on the backend using Streamlit secrets or environment variables. End users should not enter credentials in the interface.</div>',
            unsafe_allow_html=True,
        )

        run_migration = st.button("Transform Policy", key="run_migration")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Preview")
        if "migration_policy_data" in st.session_state:
            render_policy_preview(st.session_state["migration_policy_data"])
        else:
            st.info("Run a migration to preview the extracted policy before generating the final document.")
        st.markdown("</div>", unsafe_allow_html=True)

    if run_migration:
        api_key = get_api_key()

        if not api_key:
            st.error("No Groq API key found. Set GROQ_API_KEY in Streamlit secrets or use the local fallback for testing.")
            st.stop()

        if not uploaded_file:
            st.error("Please upload a legacy policy document.")
            st.stop()

        doc_text = get_uploaded_text(uploaded_file)

        if len(doc_text.strip()) < 50:
            st.error("Document appears to be empty or too short.")
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
                        "content": EXTRACTION_PROMPT + "\n\n" + doc_text,
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

            policy_data["template_name"] = st.session_state["selected_template"]
            st.session_state["migration_policy_data"] = policy_data

            status.markdown('<div class="status-text">Preview ready…</div>', unsafe_allow_html=True)
            progress.progress(100)
            status.empty()

            st.success("Preview ready. Review the output on the right, then generate the final document.")

        except Exception as e:
            st.error(f"Midnight failed: {str(e)}")

    if "migration_policy_data" in st.session_state:
        st.markdown("---")
        a, b, c = st.columns([1, 1.4, 1])
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
                    label=f"⬇ Download {st.session_state['migration_filename']}",
                    data=st.session_state["migration_docx"],
                    file_name=st.session_state["migration_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_migrated_doc",
                )

with tab_create:
    form_col, preview_col = st.columns([1.15, 1])

    with form_col:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("### Create Policy from Intake")

        with st.form("create_policy_form"):
            create_template = st.selectbox(
                "Template Target",
                TEMPLATE_OPTIONS,
                index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
                key="create_template_selector",
            )
            st.session_state["selected_template"] = create_template

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
        st.markdown("---")
        c1, c2, c3 = st.columns([1, 1.4, 1])
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
                    label=f"⬇ Download {st.session_state['created_filename']}",
                    data=st.session_state["created_docx"],
                    file_name=st.session_state["created_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_created_doc",
                )

st.markdown("</div>", unsafe_allow_html=True)
