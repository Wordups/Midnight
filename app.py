"""
╔══════════════════════════════════════════════════════════════════════╗
║                        M I D N I G H T                              ║
║              Policy Migration Pipeline  —  Wipro HPS                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import json
import re
import io
import os
from groq import Groq
from hps_policy_migration_builder import build_policy_document

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Midnight — Policy Migration",
    page_icon="🌑",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── Styling ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark background */
    .stApp { background-color: #0a0a0a; }

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 780px;
    }

    /* Hide default header */
    header { visibility: hidden; }

    /* Title */
    .midnight-title {
        font-family: 'Arial', sans-serif;
        font-size: 3.2rem;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: 0.18em;
        text-align: center;
        margin-bottom: 0.1rem;
    }

    .midnight-subtitle {
        font-family: 'Arial', sans-serif;
        font-size: 0.95rem;
        color: #555555;
        text-align: center;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 2.5rem;
    }

    .midnight-divider {
        border: none;
        border-top: 1px solid #1e1e1e;
        margin: 1.5rem 0;
    }

    /* Upload area */
    .stFileUploader > div {
        background-color: #111111 !important;
        border: 1px dashed #333333 !important;
        border-radius: 8px !important;
    }

    /* Button */
    .stButton > button {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.1em !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.65rem 2rem !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #dddddd !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: 1px solid #333333 !important;
        border-radius: 6px !important;
        width: 100% !important;
        padding: 0.65rem 2rem !important;
    }
    .stDownloadButton > button:hover {
        background-color: #252525 !important;
        border-color: #555555 !important;
    }

    /* Status text */
    .status-text {
        font-family: 'Arial', sans-serif;
        font-size: 0.85rem;
        color: #888888;
        text-align: center;
        font-style: italic;
    }

    /* Success */
    .success-box {
        background-color: #0d1f0d;
        border: 1px solid #1a4d1a;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        text-align: center;
        color: #4caf50;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    /* Info box */
    .info-box {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        color: #666666;
        font-size: 0.85rem;
        line-height: 1.6;
    }

    /* API key input */
    .stTextInput > div > div > input {
        background-color: #111111 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
        border-radius: 6px !important;
        font-family: monospace !important;
    }

    /* Labels */
    label {
        color: #aaaaaa !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.05em !important;
    }

    /* Progress */
    .stProgress > div > div {
        background-color: #ffffff !important;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #ffffff !important;
    }

    p, li { color: #888888; }
    h1, h2, h3 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────
st.markdown('<div class="midnight-title">MIDNIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="midnight-subtitle">Policy Migration Pipeline</div>
st.markdown('<hr class="midnight-divider">', unsafe_allow_html=True)

# ── API Key ────────────────────────────────────────────────────────────
api_key = os.environ.get("GROQ_API_KEY", "")

if not api_key:
    with st.expander("⚙️  Enter your Groq API Key", expanded=True):
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Get your free API key at console.groq.com"
        )
        st.markdown(
            '<div class="info-box">Your key is never stored. '
            'It lives only in this session. '
            'Get a free key at <strong>console.groq.com</strong></div>',
            unsafe_allow_html=True
        )

st.markdown('<hr class="midnight-divider">', unsafe_allow_html=True)

# ── Upload ─────────────────────────────────────────────────────────────
st.markdown("#### Upload Legacy Policy Document")
st.markdown('<p style="color:#555;font-size:0.85rem;margin-bottom:1rem;">Supported formats: .txt, .md — PDF/DOCX: paste text content as .txt</p>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drop your legacy policy document here",
    type=["txt", "md"],
    label_visibility="collapsed"
)

st.markdown('<hr class="midnight-divider">', unsafe_allow_html=True)

# ── Run Button ─────────────────────────────────────────────────────────
run_button = st.button("🌑  Run Midnight")

# ── Extraction prompt ──────────────────────────────────────────────────
EXTRACTION_PROMPT = """
You are a policy migration specialist for Wipro HealthPlan Services (WHPS).

Your task is to read the attached legacy policy document and extract ALL content into the exact Python dictionary structure below.

STRICT RULES:
- Do NOT summarize, rewrite, or remove any content
- Preserve original wording exactly
- Map ALL content into the correct field
- After every semicolon in procedure text, the system will auto-insert a line break
- For procedure items classify each using EXACTLY one type:
  "para" = standalone paragraph
  "heading" = bold underlined sub-section title
  "bullet" = first level bullet point
  "sub-bullet" = second level indented bullet
  "bold_intro" = paragraph starting with bold label: use keys "bold" and "rest"
  "bold_intro_semi" = bold_intro where "rest" contains semicolons: use keys "bold" and "rest"
  "empty" = blank spacer line

Return ONLY the Python dictionary. No explanation. No markdown fences. No preamble.
Start your response with: POLICY_DATA = {
End with: }

POLICY_DATA = {
    "policy_name": "",
    "policy_number": "",
    "version": "",
    "grc_id": "",
    "supersedes": "",
    "effective_date": "",
    "last_reviewed": "",
    "last_revised": "",
    "custodians": "Chelsea Sanchez, Alexis Taylor",
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
        "specific_lob": "[INSERT HERE]",
        "specific_lob_checked": False,
    },
    "purpose": "",
    "definitions": {},
    "policy_statement": "",
    "procedures": [],
    "related_policies": [],
    "citations": [],
    "revision_history": [],
}

HERE IS THE LEGACY POLICY DOCUMENT:
"""

# ── Main pipeline ──────────────────────────────────────────────────────
if run_button:

    if not api_key:
        st.error("Please enter your Groq API key above.")
        st.stop()

    if not uploaded_file:
        st.error("Please upload a legacy policy document.")
        st.stop()

    # Read document
    doc_text = uploaded_file.read().decode("utf-8", errors="ignore")

    if len(doc_text.strip()) < 50:
        st.error("Document appears to be empty or too short.")
        st.stop()

    # ── Step 1: Extract ────────────────────────────────────────────────
    progress = st.progress(0)
    status   = st.empty()

    status.markdown('<div class="status-text">Reading document...</div>', unsafe_allow_html=True)
    progress.progress(15)

    try:
        client = Groq(api_key=api_key)

        status.markdown('<div class="status-text">Extracting policy structure...</div>', unsafe_allow_html=True)
        progress.progress(35)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + "\n\n" + doc_text
                }
            ],
            temperature=0.1,
            max_tokens=8000
        )

        raw_output = response.choices[0].message.content.strip()

        status.markdown('<div class="status-text">Parsing extracted data...</div>', unsafe_allow_html=True)
        progress.progress(55)

    except Exception as e:
        st.error(f"Extraction failed: {str(e)}")
        st.stop()

    # ── Step 2: Parse POLICY_DATA ──────────────────────────────────────
    try:
        # Extract just the dictionary
        if "POLICY_DATA = {" in raw_output:
            dict_str = raw_output[raw_output.index("POLICY_DATA = {") + len("POLICY_DATA = "):]
        else:
            dict_str = raw_output

        # Safe eval
        local_vars = {}
        exec(dict_str, {}, local_vars)
        policy_data = local_vars.get("POLICY_DATA", None)

        if not policy_data:
            st.error("Could not parse the extracted policy data. Please try again.")
            with st.expander("Raw output (for debugging)"):
                st.code(raw_output)
            st.stop()

        status.markdown('<div class="status-text">Building formatted document...</div>', unsafe_allow_html=True)
        progress.progress(75)

    except Exception as e:
        st.error(f"Parse error: {str(e)}")
        with st.expander("Raw output (for debugging)"):
            st.code(raw_output)
        st.stop()

    # ── Step 3: Build .docx ────────────────────────────────────────────
    try:
        policy_name   = policy_data.get("policy_name", "Policy")
        policy_number = policy_data.get("policy_number", "SEC-P")
        version       = policy_data.get("version", "V1.0")
        out_filename  = f"{policy_number} {policy_name} {version}-NEW.docx"

        # Build to temp path
        tmp_path = f"/tmp/{out_filename}"
        build_policy_document(policy_data, tmp_path)

        progress.progress(95)
        status.markdown('<div class="status-text">Finalizing document...</div>', unsafe_allow_html=True)

        # Read back for download
        with open(tmp_path, "rb") as f:
            docx_bytes = f.read()

        progress.progress(100)
        status.empty()

    except Exception as e:
        st.error(f"Document build failed: {str(e)}")
        st.stop()

    # ── Step 4: Done ───────────────────────────────────────────────────
    st.markdown(
        '<div class="success-box">✓ &nbsp; Migration complete</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label=f"⬇  Download  {out_filename}",
            data=docx_bytes,
            file_name=out_filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    st.markdown('<hr class="midnight-divider">', unsafe_allow_html=True)

    # Show what was extracted
    with st.expander("📋  View extracted policy data"):
        st.markdown(f"**Policy Name:** {policy_data.get('policy_name', '')}")
        st.markdown(f"**Policy Number:** {policy_data.get('policy_number', '')}")
        st.markdown(f"**Version:** {policy_data.get('version', '')}")
        st.markdown(f"**Owner:** {policy_data.get('owner_name', '')} — {policy_data.get('owner_title', '')}")
        st.markdown(f"**Approver:** {policy_data.get('approver_name', '')} — {policy_data.get('approver_title', '')}")
        st.markdown(f"**Procedures:** {len(policy_data.get('procedures', []))} items extracted")
        st.markdown(f"**Revision History:** {len(policy_data.get('revision_history', []))} entries")

# ── Footer ─────────────────────────────────────────────────────────────
st.markdown('<hr class="midnight-divider">', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#2a2a2a;font-size:0.75rem;letter-spacing:0.1em;">MIDNIGHT &nbsp;·&nbsp; WIPRO HEALTHPLAN SERVICES &nbsp;·&nbsp; POLICY MIGRATION PIPELINE</p>',
    unsafe_allow_html=True
)
