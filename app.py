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
# 🔑 API CONFIG
# ============================================================================
LOCAL_GROQ_API_KEY = ""

def get_api_key():
    try:
        return st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "") or LOCAL_GROQ_API_KEY
    except:
        return LOCAL_GROQ_API_KEY

# ============================================================================
# 🧠 PROMPT
# ============================================================================
EXTRACTION_PROMPT = """
Extract ALL policy content into a Python dictionary called POLICY_DATA.
Do NOT summarize. Preserve wording. Fix minor grammar only.

Return ONLY:
POLICY_DATA = { ... }
"""

# ============================================================================
# 🎨 UI CONFIG
# ============================================================================
st.set_page_config(page_title="Midnight", page_icon="🌑", layout="wide")

st.markdown("""
<style>
.stApp {background:#050505;}
.block-container {max-width:1200px;}
header {visibility:hidden;}
.step {color:#888;font-size:12px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 🧩 HELPERS
# ============================================================================
def extract_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def parse_policy(raw):
    namespace = {}
    exec(raw, {}, namespace)
    return namespace.get("POLICY_DATA", {})

def preview(policy):
    st.markdown("### " + policy.get("policy_name",""))
    st.write(policy.get("purpose",""))
    st.markdown("#### Procedures")
    for p in policy.get("procedures",[]):
        st.write(p.get("text",""))

def build_doc(policy):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    build_policy_document(policy, tmp)
    with open(tmp, "rb") as f:
        return f.read()

# ============================================================================
# 🧠 HEADER
# ============================================================================
st.markdown("## MIDNIGHT")
st.caption("Policy Migration Engine • Takeoff")

st.selectbox(
    "Template",
    ["Wipro HPS Template"],
    disabled=True
)
st.caption("Additional templates coming soon")

mode = st.radio("Mode", ["Migrate Policy", "Create Policy"])

# ============================================================================
# 🚀 MIGRATION MODE
# ============================================================================
if mode == "Migrate Policy":

    st.markdown("### Step 1 — Upload")

    file = st.file_uploader("Upload policy", type=["docx","txt"])

    if st.button("Transform Policy", disabled=not file):

        key = get_api_key()
        if not key:
            st.error("API key missing")
            st.stop()

        if file.name.endswith(".docx"):
            text = extract_docx(file)
        else:
            text = file.read().decode("utf-8", errors="ignore")

        progress = st.progress(0)
        status = st.empty()

        with st.spinner("Midnight running..."):

            status.write("Reading document...")
            progress.progress(20)

            client = Groq(api_key=key)

            status.write("Extracting structure...")
            progress.progress(50)

            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":EXTRACTION_PROMPT + text}],
                temperature=0.1
            )

            raw = res.choices[0].message.content

            status.write("Parsing...")
            progress.progress(75)

            policy = parse_policy(raw)
            st.session_state["policy"] = policy

            status.write("Preview ready")
            progress.progress(100)

    if "policy" in st.session_state:

        st.markdown("### Step 2 — Preview")
        preview(st.session_state["policy"])

        if st.button("Generate Document"):
            doc = build_doc(st.session_state["policy"])
            st.download_button("Download Policy", doc, "midnight.docx")

# ============================================================================
# 🧠 CREATE MODE
# ============================================================================
else:

    st.markdown("### Step 1 — Input")

    name = st.text_input("Policy Name")
    purpose = st.text_area("Purpose")
    procedures = st.text_area("Procedures (one per line)")

    if st.button("Build Preview"):

        policy = {
            "policy_name": name,
            "purpose": purpose,
            "procedures": [{"type":"para","text":p} for p in procedures.split("\n") if p.strip()]
        }

        st.session_state["policy_create"] = policy

    if "policy_create" in st.session_state:

        st.markdown("### Step 2 — Preview")
        preview(st.session_state["policy_create"])

        if st.button("Generate Policy"):
            doc = build_doc(st.session_state["policy_create"])
            st.download_button("Download Policy", doc, "created_policy.docx")
