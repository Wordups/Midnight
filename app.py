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
            --bg-0: #000000;
            --bg-1: #050505;
            --bg-2: #0b0b0b;
            --bg-3: #111111;
            --line: rgba(255,255,255,.08);
            --line-soft: rgba(255,255,255,.05);
            --text: #f5f5f7;
            --muted: #a1a1a6;
            --muted-2: #6e6e73;
        }

        .stApp {
            background:
                radial-gradient(circle at top, #161616 0%, #080808 38%, #000000 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 1120px;
            margin: 0 auto;
            padding-top: 0.8rem;
            padding-bottom: 2rem;
        }

        header {visibility: hidden;}

        .hero-shell {
            min-height: 74vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            flex-direction: column;
            padding: 1rem 0 2rem 0;
        }

        .eyebrow {
            color: #7e7e83;
            font-size: 0.74rem;
            letter-spacing: 0.30em;
            text-transform: uppercase;
            margin-bottom: 0.7rem;
        }

        .hero-title {
            color: #ffffff;
            font-size: 4.6rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            line-height: 1;
            margin-bottom: 0.85rem;
            text-transform: uppercase;
        }

        .hero-subtitle {
            color: #a1a1a6;
            font-size: 1rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 1.15rem;
        }

        .hero-copy {
            max-width: 680px;
            color: #b0b0b6;
            font-size: 1.02rem;
            line-height: 1.7;
            margin-bottom: 1.6rem;
        }

        .template-bar {
            width: 100%;
            max-width: 420px;
            margin: 0 auto 1.4rem auto;
        }

        .action-card {
            background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.015));
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 24px;
            padding: 1.4rem;
            min-height: 180px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform .15s ease, border-color .15s ease, background .15s ease;
        }

        .action-card:hover {
            transform: translateY(-2px);
            border-color: rgba(255,255,255,.14);
            background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
        }

        .action-title {
            color: #ffffff;
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }

        .action-copy {
            color: #9d9da2;
            font-size: 0.93rem;
            line-height: 1.62;
        }

        .mini-label {
            color: #6f6f74;
            font-size: 0.75rem;
            letter-spacing: 0.10em;
            text-transform: uppercase;
        }

        .workspace-shell {
            background: linear-gradient(180deg, rgba(13,13,14,.96), rgba(8,8,9,.98));
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 28px;
            padding: 1.1rem;
            box-shadow:
                0 18px 48px rgba(0,0,0,.28),
                inset 0 1px 0 rgba(255,255,255,.02);
            margin-top: 0.4rem;
        }

        .workspace-title {
            color: #ffffff;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .workspace-subtitle {
            color: #8e8e93;
            font-size: 0.92rem;
            margin-bottom: 1rem;
        }

        .panel-card {
            background: linear-gradient(180deg, rgba(17,17,18,.96), rgba(11,11,12,.96));
            border: 1px solid rgba(255,255,255,.06);
            border-radius: 22px;
            padding: 1rem;
            height: 100%;
        }

        .preview-box {
            background: linear-gradient(180deg, rgba(10,10,11,1), rgba(7,7,8,1));
            border: 1px solid rgba(255,255,255,.05);
            border-radius: 18px;
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
            border-radius: 16px !important;
            border: none !important;
            background: linear-gradient(180deg, #ffffff 0%, #e8e8ea 100%) !important;
            color: #000000 !important;
            font-weight: 700 !important;
            font-size: 0.98rem !important;
            letter-spacing: 0.02em !important;
            padding: 1rem 1rem !important;
            box-shadow:
                0 10px 24px rgba(255,255,255,.04),
                inset 0 1px 0 rgba(255,255,255,.55) !important;
        }

        .stDownloadButton > button {
            width: 100% !important;
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,.10) !important;
            background: linear-gradient(180deg, rgba(22,22,23,1), rgba(14,14,15,1)) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            padding: 1rem 1rem !important;
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
            border-radius: 16px !important;
            background: rgba(255,255,255,.02) !important;
            border: 1px solid rgba(255,255,255,.07) !important;
        }

        h1, h2, h3 {
            margin-bottom: 0.45rem !important;
        }

        .divider-space {
            height: 0.6rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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

if "active_mode" not in st.session_state:
    st.session_state["active_mode"] = None


# ============================================================================
# HERO
# ============================================================================
st.markdown('<div class="hero-shell">', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">MIDNIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="hero-copy">'
    'Standardize policy workflows.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="template-bar">', unsafe_allow_html=True)
selected_template = st.selectbox(
    "Template Target",
    TEMPLATE_OPTIONS,
    index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
    key="hero_template_selector",
    label_visibility="collapsed",
)
st.session_state["selected_template"] = selected_template
st.markdown("</div>", unsafe_allow_html=True)

cta1, cta2 = st.columns(2)

with cta1:
    if st.button("Migrate Policy", key="hero_migrate"):
        st.session_state["active_mode"] = "migrate"

with cta2:
    if st.button("Create Policy", key="hero_create"):
        st.session_state["active_mode"] = "create"

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# WORKSPACE
# ============================================================================
if st.session_state["active_mode"] is not None:
    st.markdown('<div class="workspace-shell">', unsafe_allow_html=True)

    if st.session_state["active_mode"] == "migrate":
        st.markdown('<div class="workspace-title">Migrate Policy</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="workspace-subtitle">Target template: {st.session_state["selected_template"]}</div>',
            unsafe_allow_html=True,
        )

        left, right = st.columns([1.08, 1])

        with left:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown("### Upload")
            st.markdown(
                '<div class="caption-text">Supported formats: .docx, .txt, .md</div>',
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

                st.success("Preview ready. Review the output, then generate the final document.")

            except Exception as e:
                st.error(f"Midnight failed: {str(e)}")

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

    elif st.session_state["active_mode"] == "create":
        st.markdown('<div class="workspace-title">Create Policy</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="workspace-subtitle">Target template: {st.session_state["selected_template"]}</div>',
            unsafe_allow_html=True,
        )

        form_col, preview_col = st.columns([1.08, 1])

        with form_col:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown("### Intake")

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
