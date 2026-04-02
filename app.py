"""
╔══════════════════════════════════════════════════════════════════════╗
║                               MIDNIGHT                               ║
║                     Policy Migration Engine                          ║
║               A product developed by Takeoff                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import tempfile
import streamlit as st
from groq import Groq
from hps_policy_migration_builder import build_policy_document

# ============================================================================
# 🔑 API KEY CONFIGURATION
# ============================================================================
# 👉 LINE BELOW = WHERE YOU PUT YOUR KEY FOR DEMO
LOCAL_GROQ_API_KEY = ""

def get_api_key():
    return (
        st.secrets.get("GROQ_API_KEY", "")
        or os.environ.get("GROQ_API_KEY", "")
        or LOCAL_GROQ_API_KEY
    )

# ============================================================================
# 🧠 PROMPT CONFIGURATION
# ============================================================================
EXTRACTION_PROMPT = """
You are a policy migration specialist.

Extract ALL content into a structured POLICY_DATA dictionary.

RULES:
- Do NOT summarize or remove content
- Preserve wording as closely as possible
- Fix minor grammar/spacing only
- Map content correctly into fields

Return ONLY:
POLICY_DATA = { ... }

HERE IS THE DOCUMENT:
"""

# ============================================================================
# 🎨 UI CONFIG
# ============================================================================
st.set_page_config(page_title="Midnight", page_icon="🌑", layout="centered")

st.markdown("<h3 style='text-align:center;'>MIDNIGHT</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray;'>Policy Migration Engine</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Policy (.txt)", type=["txt"])
run = st.button("Transform Policy")

# ============================================================================
# 🔄 MAIN PIPELINE
# ============================================================================
if run:

    api_key = get_api_key()

    if not api_key:
        st.error("API key missing")
        st.stop()

    if not uploaded_file:
        st.error("Upload a file first")
        st.stop()

    doc_text = uploaded_file.read().decode("utf-8")

    client = Groq(api_key=api_key)

    with st.spinner("Running Midnight..."):

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT + doc_text
            }],
            temperature=0.1
        )

        raw_output = response.choices[0].message.content

        if "POLICY_DATA" not in raw_output:
            st.error("Failed to parse output")
            st.code(raw_output)
            st.stop()

        namespace = {}
        exec(raw_output, {}, namespace)
        policy_data = namespace["POLICY_DATA"]

        # Build document
        tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
        build_policy_document(policy_data, tmp_path)

        with open(tmp_path, "rb") as f:
            doc_bytes = f.read()

        st.success("Transformation Complete")

        st.download_button(
            "Download Policy",
            doc_bytes,
            file_name="midnight_output.docx"
        )
