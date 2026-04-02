"""
╔══════════════════════════════════════════════════════════════════════╗
║                                MIDNIGHT                              ║
║                      Policy Migration Engine                         ║
║                A product developed by Takeoff                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import tempfile
import streamlit as st
from groq import Groq
from docx import Document
from hps_policy_migration_builder import build_policy_document

# ============================================================================
# API KEY CONFIGURATION
# ============================================================================
# LOCAL TESTING ONLY. LEAVE BLANK FOR STREAMLIT CLOUD / PRODUCTION.
LOCAL_GROQ_API_KEY = ""


def get_api_key() -> str:
    secrets_key = ""
    try:
        secrets_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secrets_key = ""

    return secrets_key or os.environ.get("GROQ_API_KEY", "") or LOCAL_GROQ_API_KEY


# ============================================================================
# PROMPT CONFIGURATION
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
# STREAMLIT CONFIG
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
        .stApp {
            background: linear-gradient(180deg, #050505 0%, #0b0b0b 60%, #111111 100%);
        }
        .block-container {
            max-width: 1220px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        header {visibility: hidden;}
        .midnight-shell {
            background: rgba(15,15,15,0.96);
            border: 1px solid #232323;
            border-radius: 24px;
            padding: 1.4rem 1.4rem 1.2rem 1.4rem;
            box-shadow: 0 18px 50px rgba(0,0,0,0.34);
        }
        .midnight-eyebrow {
            text-align:center;
            color:#7f7f7f;
            font-size:0.8rem;
            letter-spacing:0.28em;
            text-transform:uppercase;
            margin-bottom:0.5rem;
        }
        .midnight-title {
            text-align:center;
            color:#ffffff;
            font-size:3.15rem;
            font-weight:900;
            letter-spacing:0.16em;
            margin-bottom:0.15rem;
        }
        .midnight-subtitle {
            text-align:center;
            color:#a0a0a0;
            font-size:0.95rem;
            letter-spacing:0.14em;
            text-transform:uppercase;
            margin-bottom:1.6rem;
        }
        .midnight-card {
            background:#101010;
            border:1px solid #222222;
            border-radius:18px;
            padding:1.1rem 1.1rem 1rem 1.1rem;
            height:100%;
        }
        .midnight-note {
            color:#8c8c8c;
            font-size:0.88rem;
            line-height:1.6;
            background:#101010;
            border:1px solid #212121;
            border-radius:14px;
            padding:0.95rem 1rem;
            margin:0.4rem 0 0.9rem 0;
        }
        .midnight-success {
            background: linear-gradient(180deg, rgba(16,43,21,.95), rgba(10,27,14,.95));
            border: 1px solid #2c6a37;
            border-radius: 14px;
            padding: 1rem 1.15rem;
            color: #7be38f;
            text-align:center;
            font-weight:700;
            margin-top: 1rem;
        }
        .midnight-status {
            color:#9d9d9d;
            text-align:center;
            font-style:italic;
            font-size:0.9rem;
        }
        .midnight-chip {
            display:inline-block;
            padding:0.28rem 0.6rem;
            border-radius:999px;
            background:#181818;
            border:1px solid #2a2a2a;
            color:#9e9e9e;
            font-size:0.78rem;
            margin-right:0.45rem;
            margin-bottom:0.5rem;
        }
        .caption {
            color:#6f6f6f;
            font-size:0.85rem;
            margin-bottom:0.85rem;
        }
        .stButton > button {
            width:100% !important;
            border-radius:12px !important;
            border:none !important;
            background: linear-gradient(180deg, #ffffff 0%, #dddddd 100%) !important;
            color:#000000 !important;
            font-weight:800 !important;
            letter-spacing:0.08em !important;
            padding:0.92rem 1.1rem !important;
        }
        .stDownloadButton > button {
            width:100% !important;
            border-radius:12px !important;
            border:1px solid #3a3a3a !important;
            background:#121212 !important;
            color:#ffffff !important;
            font-weight:700 !important;
            padding:0.88rem 1.1rem !important;
        }
        .stFileUploader > div {
            background:#101010 !important;
            border:1px dashed #3a3a3a !important;
            border-radius:14px !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            background:#111111;
            border:1px solid #242424;
            border-radius:12px;
            padding:0.65rem 1rem;
        }
        .stProgress > div > div {
            background-color:#ffffff !important;
        }
        .preview-box {
            background:#0e0e0e;
            border:1px solid #202020;
            border-radius:16px;
            padding:1rem;
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
        "applicable_to": {
            "hps_inc": True,
            "agency": True,
            "corporate": True,
            "govt_affairs": False,
            "legal_review": False,
        },
        "policy_types": {
            "carrier_specific": False,
            "cross_carrier": False,
            "global": False,
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
    }


def render_policy_preview(policy_data):
    st.markdown('<div class="preview-box">', unsafe_allow_html=True)
    st.markdown(f"### {policy_data.get('policy_name', '')}")
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
            elif item_type in ["heading"]:
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
# HEADER
# ============================================================================
st.markdown('<div class="midnight-shell">', unsafe_allow_html=True)
st.markdown('<div class="midnight-eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
st.markdown('<div class="midnight-title">MIDNIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="midnight-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

top_left, top_mid, top_right = st.columns([2.2, 1.2, 1.4])

with top_left:
    st.markdown(
        '<div class="midnight-note"><strong>Midnight</strong> transforms legacy policy documents into a controlled template structure and can also generate new policies directly from structured intake.</div>',
        unsafe_allow_html=True,
    )

with top_mid:
    st.markdown("**Template Selector**")
    st.selectbox(
        "Template Selector",
        ["Wipro HealthPlan Services (Current)"],
        index=0,
        disabled=True,
        label_visibility="collapsed",
    )
    st.caption("Additional templates — coming soon")

with top_right:
    st.markdown("**Current Capability**")
    st.markdown('<span class="midnight-chip">.docx Upload</span>', unsafe_allow_html=True)
    st.markdown('<span class="midnight-chip">Migration</span>', unsafe_allow_html=True)
    st.markdown('<span class="midnight-chip">Policy Creation</span>', unsafe_allow_html=True)
    st.markdown('<span class="midnight-chip">Preview</span>', unsafe_allow_html=True)

tab_migrate, tab_create = st.tabs(["Migrate Policy", "Create Policy"])

# ============================================================================
# MIGRATE TAB
# ============================================================================
with tab_migrate:
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown('<div class="midnight-card">', unsafe_allow_html=True)
        st.markdown("#### Upload Legacy Policy Document")
        st.markdown(
            '<div class="caption">Supported formats: .docx, .txt, .md</div>',
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Upload a legacy policy document",
            type=["docx", "txt", "md"],
            label_visibility="collapsed",
            key="migrate_upload",
        )

        st.markdown(
            '<div class="midnight-note"><strong>Demo note:</strong> the AI key should be configured on the backend using Streamlit secrets or environment variables.</div>',
            unsafe_allow_html=True,
        )

        run_migration = st.button("Transform Policy", key="run_migration")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="midnight-card">', unsafe_allow_html=True)
        st.markdown("#### Preview")
        if "migration_policy_data" in st.session_state:
            render_policy_preview(st.session_state["migration_policy_data"])
        else:
            st.info("Run a migration to preview the extracted policy before download.")
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
            status.markdown('<div class="midnight-status">Reading document…</div>', unsafe_allow_html=True)
            progress.progress(15)

            client = Groq(api_key=api_key)

            status.markdown('<div class="midnight-status">Extracting policy structure…</div>', unsafe_allow_html=True)
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

            status.markdown('<div class="midnight-status">Parsing extracted data…</div>', unsafe_allow_html=True)
            progress.progress(60)

            policy_data = parse_policy_data(raw_output)

            if not policy_data:
                st.error("The model response could not be parsed into POLICY_DATA.")
                with st.expander("Raw model output"):
                    st.code(raw_output)
                st.stop()

            st.session_state["migration_policy_data"] = policy_data

            status.markdown('<div class="midnight-status">Building preview…</div>', unsafe_allow_html=True)
            progress.progress(100)
            status.empty()

            st.success("Preview ready. Review the output on the right, then download below.")

        except Exception as e:
            st.error(f"Midnight failed: {str(e)}")

    if "migration_policy_data" in st.session_state:
        st.markdown("---")
        col_a, col_b, col_c = st.columns([1, 1.4, 1])
        with col_b:
            if st.button("Generate Final Document", key="generate_migrated_doc"):
                try:
                    out_filename, docx_bytes = build_output_doc(st.session_state["migration_policy_data"])
                    st.session_state["migration_filename"] = out_filename
                    st.session_state["migration_docx"] = docx_bytes
                except Exception as e:
                    st.error(f"Document build failed: {str(e)}")

            if "migration_docx" in st.session_state:
                st.markdown('<div class="midnight-success">✓ Transformation complete</div>', unsafe_allow_html=True)
                st.download_button(
                    label=f"⬇ Download {st.session_state['migration_filename']}",
                    data=st.session_state["migration_docx"],
                    file_name=st.session_state["migration_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_migrated_doc",
                )

# ============================================================================
# CREATE TAB
# ============================================================================
with tab_create:
    form_col, preview_col = st.columns([1.15, 1])

    with form_col:
        st.markdown('<div class="midnight-card">', unsafe_allow_html=True)
        st.markdown("#### Create New Policy")

        policy_name = st.text_input("Policy Name", key="create_policy_name")
        meta1, meta2, meta3 = st.columns(3)
        with meta1:
            policy_number = st.text_input("Policy Number", key="create_policy_number")
        with meta2:
            version = st.text_input("Version", value="V1.0", key="create_version")
        with meta3:
            grc_id = st.text_input("GRC ID", key="create_grc_id")

        meta4, meta5, meta6 = st.columns(3)
        with meta4:
            effective_date = st.text_input("Effective Date", key="create_effective_date")
        with meta5:
            last_reviewed = st.text_input("Last Reviewed", key="create_last_reviewed")
        with meta6:
            last_revised = st.text_input("Last Revised", key="create_last_revised")

        supersedes = st.text_input("Supersedes", key="create_supersedes")
        custodians = st.text_input("Custodians", key="create_custodians")

        owner1, owner2 = st.columns(2)
        with owner1:
            owner_name = st.text_input("Owner Name", key="create_owner_name")
        with owner2:
            owner_title = st.text_input("Owner Title", key="create_owner_title")

        approver1, approver2 = st.columns(2)
        with approver1:
            approver_name = st.text_input("Approver Name", key="create_approver_name")
        with approver2:
            approver_title = st.text_input("Approver Title", key="create_approver_title")

        signed1, signed2 = st.columns(2)
        with signed1:
            date_signed = st.text_input("Date Signed", key="create_date_signed")
        with signed2:
            date_approved = st.text_input("Date Approved", key="create_date_approved")

        purpose = st.text_area("Purpose", height=120, key="create_purpose")
        definitions_text = st.text_area(
            "Definitions (one per line, format: Term: Definition)",
            height=120,
            key="create_definitions",
        )
        policy_statement = st.text_area("Policy Statement", height=140, key="create_policy_statement")
        procedures_text = st.text_area(
            "Procedures (one line per step; use '- ' for bullets)",
            height=220,
            key="create_procedures",
        )
        related_policies_text = st.text_area(
            "Related Policies (one per line)",
            height=100,
            key="create_related_policies",
        )
        citations_text = st.text_area(
            "Citations / References (one per line)",
            height=100,
            key="create_citations",
        )

        create_preview = st.button("Build Preview", key="create_preview_button")
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
            )
            st.session_state["created_policy_data"] = created_policy_data
            st.success("Preview ready.")

    with preview_col:
        st.markdown('<div class="midnight-card">', unsafe_allow_html=True)
        st.markdown("#### Preview")
        if "created_policy_data" in st.session_state:
            render_policy_preview(st.session_state["created_policy_data"])
        else:
            st.info("Complete the intake form and build a preview to review the policy before download.")
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
                st.markdown('<div class="midnight-success">✓ Policy generated</div>', unsafe_allow_html=True)
                st.download_button(
                    label=f"⬇ Download {st.session_state['created_filename']}",
                    data=st.session_state["created_docx"],
                    file_name=st.session_state["created_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_created_doc",
                )

st.markdown("</div>", unsafe_allow_html=True)
