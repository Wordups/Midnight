"""
╔══════════════════════════════════════════════════════════════════════╗
║                               MIDNIGHT                               ║
║                     Policy Migration Engine                          ║
║                     A product developed by Takeoff                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import os
from groq import Groq
from hps_policy_migration_builder import build_policy_document

st.set_page_config(
    page_title="Takeoff — Midnight",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at top, #151515 0%, #0a0a0a 42%, #050505 100%);
    }
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 2rem;
        max-width: 820px;
    }
    header { visibility: hidden; }

    .takeoff-eyebrow {
        font-family: Arial, sans-serif;
        font-size: 0.78rem;
        color: #7f7f7f;
        text-align: center;
        letter-spacing: 0.28em;
        text-transform: uppercase;
        margin-bottom: 0.65rem;
    }
    .takeoff-title {
        font-family: Arial, sans-serif;
        font-size: 3.3rem;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: 0.16em;
        text-align: center;
        margin-bottom: 0.2rem;
        text-transform: uppercase;
    }
    .takeoff-subtitle {
        font-family: Arial, sans-serif;
        font-size: 0.95rem;
        color: #9a9a9a;
        text-align: center;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 2.3rem;
    }
    .takeoff-panel {
        background: linear-gradient(180deg, rgba(20,20,20,.92), rgba(10,10,10,.96));
        border: 1px solid #222222;
        border-radius: 16px;
        padding: 1.2rem 1.2rem 1rem 1.2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,.35);
        margin-bottom: 1rem;
    }
    .takeoff-divider {
        border: none;
        border-top: 1px solid #1d1d1d;
        margin: 1.35rem 0;
    }
    .stFileUploader > div {
        background-color: #111111 !important;
        border: 1px dashed #3a3a3a !important;
        border-radius: 12px !important;
    }
    .stButton > button {
        background: linear-gradient(180deg, #ffffff 0%, #dddddd 100%) !important;
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 0.98rem !important;
        letter-spacing: 0.12em !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.8rem 1.4rem !important;
        width: 100% !important;
        box-shadow: 0 8px 18px rgba(255,255,255,.08) !important;
        transition: all 0.18s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        background: linear-gradient(180deg, #ffffff 0%, #d3d3d3 100%) !important;
    }
    .stDownloadButton > button {
        background-color: #121212 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: 1px solid #343434 !important;
        border-radius: 10px !important;
        width: 100% !important;
        padding: 0.8rem 1.4rem !important;
    }
    .stDownloadButton > button:hover {
        background-color: #1d1d1d !important;
        border-color: #5a5a5a !important;
    }
    .status-text {
        font-family: Arial, sans-serif;
        font-size: 0.86rem;
        color: #9a9a9a;
        text-align: center;
        font-style: italic;
    }
    .success-box {
        background: linear-gradient(180deg, rgba(14,35,18,.95), rgba(10,24,13,.95));
        border: 1px solid #295f33;
        border-radius: 12px;
        padding: 1rem 1.35rem;
        margin: 1rem 0;
        text-align: center;
        color: #7ce38d;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .info-box {
        background-color: #101010;
        border: 1px solid #242424;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: 1rem 0 0.3rem 0;
        color: #7f7f7f;
        font-size: 0.85rem;
        line-height: 1.65;
    }
    .stTextInput > div > div > input {
        background-color: #101010 !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
        font-family: monospace !important;
    }
    label {
        color: #b5b5b5 !important;
        font-size: 0.84rem !important;
        letter-spacing: 0.05em !important;
    }
    .stProgress > div > div { background-color: #ffffff !important; }
    p, li { color: #9b9b9b; }
    h1, h2, h3, h4 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="takeoff-eyebrow">Takeoff Product</div>', unsafe_allow_html=True)
st.markdown('<div class="takeoff-title">MIDNIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="takeoff-subtitle">Policy Migration Engine</div>', unsafe_allow_html=True)

api_key = os.environ.get("GROQ_API_KEY", "")

with st.container():
    st.markdown('<div class="takeoff-panel">', unsafe_allow_html=True)

    if not api_key:
        with st.expander("⚙️ Enter your Groq API Key", expanded=True):
            api_key = st.text_input(
                "Groq API Key",
                type="password",
                placeholder="gsk_...",
                help="Get your free API key at console.groq.com"
            )
            st.markdown(
                '<div class="info-box">Your key is never stored. It is used only for the current session. '
                'Get a free key at <strong>console.groq.com</strong>.</div>',
                unsafe_allow_html=True
            )

    st.markdown('<hr class="takeoff-divider">', unsafe_allow_html=True)
    st.markdown("#### Upload Legacy Policy Document")
    st.markdown(
        '<p style="color:#6f6f6f;font-size:0.85rem;margin-bottom:1rem;">'
        'Supported formats: .txt, .md — for PDF or DOCX, paste the text into a .txt file first.'
        '</p>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Drop your legacy policy document here",
        type=["txt", "md"],
        label_visibility="collapsed"
    )

    st.markdown('<hr class="takeoff-divider">', unsafe_allow_html=True)
    run_button = st.button("✦ Run Midnight")
    st.markdown('</div>', unsafe_allow_html=True)

EXTRACTION_PROMPT = """
You are a policy migration specialist.

Your task is to read the attached legacy policy document and extract ALL content into the exact Python dictionary structure below.

STRICT RULES:
- Do NOT summarize, rewrite, or remove any content
- Preserve original wording as closely as possible
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

if run_button:
    if not api_key:
        st.error("Please enter your Groq API key above.")
        st.stop()

    if not uploaded_file:
        st.error("Please upload a legacy policy document.")
        st.stop()

    doc_text = uploaded_file.read().decode("utf-8", errors="ignore")

    if len(doc_text.strip()) < 50:
        st.error("Document appears to be empty or too short.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    status.markdown('<div class="status-text">Reading document...</div>', unsafe_allow_html=True)
    progress.progress(15)

    try:
        client = Groq(api_key=api_key)

        status.markdown('<div class="status-text">Extracting policy structure...</div>', unsafe_allow_html=True)
        progress.progress(35)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": EXTRACTION_PROMPT + "\\n\\n" + doc_text}],
            temperature=0.1,
            max_tokens=8000
        )

        raw_output = response.choices[0].message.content.strip()

        status.markdown('<div class="status-text">Parsing extracted data...</div>', unsafe_allow_html=True)
        progress.progress(55)

    except Exception as e:
        st.error(f"Extraction failed: {str(e)}")
        st.stop()

    try:
        if "POLICY_DATA = {" in raw_output:
            dict_str = raw_output[raw_output.index("POLICY_DATA = {"):]
        else:
            dict_str = raw_output

        namespace = {}
        exec(dict_str, {}, namespace)
        policy_data = namespace.get("POLICY_DATA", None)

        if not policy_data:
            st.error("Could not parse the extracted policy data. Please try again.")
            with st.expander("Raw output"):
                st.code(raw_output)
            st.stop()

        status.markdown('<div class="status-text">Building formatted document...</div>', unsafe_allow_html=True)
        progress.progress(75)

    except Exception as e:
        st.error(f"Parse error: {str(e)}")
        with st.expander("Raw output"):
            st.code(raw_output)
        st.stop()

    try:
        policy_name = policy_data.get("policy_name", "Policy")
        policy_number = policy_data.get("policy_number", "SEC-P")
        version = policy_data.get("version", "V1.0")
        out_filename = f"{policy_number} {policy_name} {version}-NEW.docx"

        tmp_path = f"/tmp/{out_filename}"
        build_policy_document(policy_data, tmp_path)

        progress.progress(95)
        status.markdown('<div class="status-text">Finalizing document...</div>', unsafe_allow_html=True)

        with open(tmp_path, "rb") as f:
            docx_bytes = f.read()

        progress.progress(100)
        status.empty()

    except Exception as e:
        st.error(f"Document build failed: {str(e)}")
        st.stop()

    st.markdown('<div class="success-box">✓ Migration complete</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label=f"⬇ Download {out_filename}",
            data=docx_bytes,
            file_name=out_filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    st.markdown('<hr class="takeoff-divider">', unsafe_allow_html=True)

    with st.expander("View extracted policy data"):
        st.markdown(f"**Policy Name:** {policy_data.get('policy_name', '')}")
        st.markdown(f"**Policy Number:** {policy_data.get('policy_number', '')}")
        st.markdown(f"**Version:** {policy_data.get('version', '')}")
        st.markdown(f"**Owner:** {policy_data.get('owner_name', '')} — {policy_data.get('owner_title', '')}")
        st.markdown(f"**Approver:** {policy_data.get('approver_name', '')} — {policy_data.get('approver_title', '')}")
        st.markdown(f"**Procedures:** {len(policy_data.get('procedures', []))} items extracted")
        st.markdown(f"**Revision History:** {len(policy_data.get('revision_history', []))} entries")

st.markdown('<hr class="takeoff-divider">', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#3c3c3c;font-size:0.75rem;letter-spacing:0.16em;text-transform:uppercase;">'
    'Takeoff Product · Midnight · Policy Migration Engine'
    '</p>',
    unsafe_allow_html=True
)
