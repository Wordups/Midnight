"""
╔══════════════════════════════════════════════════════════════════════╗
║                                MIDNIGHT                              ║
║                      Policy Migration Engine                         ║
║                 A product developed by Takeoff                       ║
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
# FOR LOCAL TESTING ONLY:
# Paste your Groq API key between the quotes below if you are running locally.
# For Streamlit Cloud / production, leave this blank and use Secrets instead.
LOCAL_GROQ_API_KEY = ""


def get_api_key() -> str:
    return (
        st.secrets.get("GROQ_API_KEY", "")
        or os.environ.get("GROQ_API_KEY", "")
        or LOCAL_GROQ_API_KEY
    )


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
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at top, #1a1a1a 0%, #0a0a0a 45%, #050505 100%);
        }
        .block-container {
            max-width: 860px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        header {visibility: hidden;}
        .midnight-wrap {
            background: rgba(14,14,14,0.94);
            border: 1px solid #242424;
            border-radius: 18px;
            padding: 1.35rem 1.35rem 1rem 1.35rem;
            box-shadow: 0 14px 32px rgba(0,0,0,0.35);
        }
        .midnight-eyebrow {
            text-align:center;
            color:#7f7f7f;
            font-size:0.8rem;
            letter-spacing:0.28em;
            text-transform:uppercase;
            margin-bottom:0.55rem;
        }
        .midnight-title {
            text-align:center;
            color:#ffffff;
            font-size:3rem;
            font-weight:900;
            letter-spacing:0.16em;
            margin-bottom:0.2rem;
        }
        .midnight-subtitle {
            text-align:center;
            color:#a0a0a0;
            font-size:0.95rem;
            letter-spacing:0.14em;
            text-transform:uppercase;
            margin-bottom:1.85rem;
        }
        .midnight-note {
            color:#8c8c8c;
            font-size:0.88rem;
            line-height:1.6;
            background:#101010;
            border:1px solid #212121;
            border-radius:12px;
            padding:0.9rem 1rem;
            margin:0.6rem 0 1rem 0;
        }
        .midnight-success {
            background: linear-gradient(180deg, rgba(16,43,21,.95), rgba(10,27,14,.95));
            border: 1px solid #2c6a37;
            border-radius: 12px;
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
        .stButton > button {
            width:100% !important;
            border-radius:10px !important;
            border:none !important;
            background: linear-gradient(180deg, #ffffff 0%, #dddddd 100%) !important;
            color:#000000 !important;
            font-weight:800 !important;
            letter-spacing:0.1em !important;
            padding:0.85rem 1.1rem !important;
        }
        .stDownloadButton > button {
            width:100% !important;
            border-radius:10px !important;
            border:1px solid #3a3a3a !important;
            background:#121212 !important;
            color:#ffffff !important;
            font-weight:700 !important;
            padding:0.85rem 1.1rem !important;
        }
        .stFileUploader > div {
            background:#101010 !important;
            border:1px dashed #3a3a3a !important;
            border-radius:12px !important;
        }
        .stProgress > div > div {
            background-color:#ffffff !important;
        }
        .caption {
            color:#6f6f6f;
            font-size:0.85rem;
            margin-bottom:0.85rem;
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


# ============================================================================
# HEADER
# ============================================================================
st.markdown('<div class="midnight-eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
st.markdown('<div class="midnight-title">MIDNIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="midnight-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

st.markdown('<div class="midnight-wrap">', unsafe_allow_html=True)
st.markdown("#### Upload Legacy Policy Document")
st.markdown(
    '<div class="caption">Supported formats: .docx, .txt, .md</div>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a legacy policy document",
    type=["docx", "txt", "md"],
    label_visibility="collapsed",
)

st.markdown(
    '<div class="midnight-note"><strong>Demo note:</strong> the AI key should be configured on the backend. '
    'This app supports Streamlit secrets or environment variables. '
    'The local fallback is only for quick local testing.</div>',
    unsafe_allow_html=True,
)

run_button = st.button("Transform Policy")
st.markdown('</div>', unsafe_allow_html=True)


# ============================================================================
# MAIN PIPELINE
# ============================================================================
if run_button:
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

        status.markdown('<div class="midnight-status">Building formatted document…</div>', unsafe_allow_html=True)
        progress.progress(80)

        policy_name = policy_data.get("policy_name", "Policy")
        policy_number = policy_data.get("policy_number", "SEC-P")
        version = policy_data.get("version", "V1.0")
        out_filename = f"{policy_number} {policy_name} {version}-NEW.docx"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp_path = tmp.name

        build_policy_document(policy_data, tmp_path)

        with open(tmp_path, "rb") as f:
            docx_bytes = f.read()

        progress.progress(100)
        status.empty()

        st.markdown('<div class="midnight-success">✓ Transformation complete</div>', unsafe_allow_html=True)

        _, center, _ = st.columns([1, 2, 1])
        with center:
            st.download_button(
                label=f"⬇ Download {out_filename}",
                data=docx_bytes,
                file_name=out_filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        with st.expander("View extracted policy data"):
            st.markdown(f"**Policy Name:** {policy_data.get('policy_name', '')}")
            st.markdown(f"**Policy Number:** {policy_data.get('policy_number', '')}")
            st.markdown(f"**Version:** {policy_data.get('version', '')}")
            st.markdown(f"**Owner:** {policy_data.get('owner_name', '')} — {policy_data.get('owner_title', '')}")
            st.markdown(f"**Approver:** {policy_data.get('approver_name', '')} — {policy_data.get('approver_title', '')}")
            st.markdown(f"**Procedures:** {len(policy_data.get('procedures', []))} items extracted")
            st.markdown(f"**Revision History:** {len(policy_data.get('revision_history', []))} entries")

    except Exception as e:
        st.error(f"Midnight failed: {str(e)}")
