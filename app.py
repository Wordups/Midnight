import streamlit as st
from datetime import datetime
from docx import Document
import io

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Midnight",
    page_icon="🌙",
    layout="wide"
)

# -----------------------------
# SESSION STATE (NAVIGATION)
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "overview"

# -----------------------------
# GLOBAL STYLING (APPLE FEEL)
# -----------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #f5f5f7;
}

.block-container {
    padding-top: 2rem;
    max-width: 1100px;
}

h1, h2, h3 {
    color: #1d1d1f;
}

.stButton>button {
    background-color: #1d1d1f;
    color: white;
    border-radius: 10px;
    padding: 0.6rem 1.2rem;
    border: none;
}

.stButton>button:hover {
    background-color: #333;
}

.section-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #e5e5e5;
    margin-bottom: 20px;
}

.subtle {
    color: #6e6e73;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# NAV BAR
# -----------------------------
col1, col2, col3 = st.columns([6,1,1])

with col1:
    st.markdown("### MIDNIGHT")

with col2:
    if st.button("Overview"):
        st.session_state.page = "overview"

with col3:
    if st.button("Workspace"):
        st.session_state.page = "migrate"

# -----------------------------
# HELPER: DOC GENERATION
# -----------------------------
def generate_docx(title, body):
    doc = Document()
    doc.add_heading(title, level=1)

    for section, content in body.items():
        doc.add_heading(section, level=2)
        doc.add_paragraph(content)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# -----------------------------
# PAGE: OVERVIEW
# -----------------------------
if st.session_state.page == "overview":

    st.markdown("## Policy Migration Engine")
    st.markdown("Automate policy creation, migration, and audit readiness through a controlled documentation workflow.")

    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Migrate a Policy"):
            st.session_state.page = "migrate"

    with col2:
        if st.button("Create a Policy"):
            st.session_state.page = "create"

    st.write("")
    st.markdown("### What this does")
    st.markdown("""
- Convert legacy documents into structured templates  
- Generate new policies from structured intake  
- Standardize outputs across your organization  
- Reduce audit preparation time significantly  
""")

# -----------------------------
# PAGE: MIGRATE POLICY
# -----------------------------
elif st.session_state.page == "migrate":

    st.markdown("## Migrate a Policy")
    st.markdown("Convert an existing document into a structured template.")

    template = st.selectbox(
        "Template",
        ["Generic Policy Template", "Custom Enterprise Template"]
    )

    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["docx", "txt", "md"]
    )

    if uploaded_file:
        content = uploaded_file.read()

        st.markdown("### Preview")
        st.text(content[:1500].decode(errors="ignore"))

        if st.button("Transform Policy"):

            # Simulated transformation
            body = {
                "Purpose and Scope": "Generated from uploaded content.",
                "Policy Statement": "Standardized output aligned to template.",
                "Procedures": "Structured procedural breakdown created.",
                "References": "Mapped to compliance standards."
            }

            doc = generate_docx("Transformed Policy", body)

            st.download_button(
                label="Download Document",
                data=doc,
                file_name="transformed_policy.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

# -----------------------------
# PAGE: CREATE POLICY
# -----------------------------
elif st.session_state.page == "create":

    st.markdown("## Create a Policy")
    st.markdown("Generate a new policy from structured intake.")

    template = st.selectbox(
        "Template",
        ["Generic Policy Template", "Custom Enterprise Template"]
    )

    st.markdown("### Intake")

    policy_name = st.text_input("Policy Name")
    policy_number = st.text_input("Policy Number")

    version = st.text_input("Version", value="V1.0")

    today = datetime.today().strftime("%m/%d/%Y")
    effective_date = st.text_input("Effective Date", value=today)

    owner = st.text_input("Policy Owner")
    approver = st.text_input("Policy Approver")

    st.markdown("### Content")

    purpose = st.text_area("Purpose and Scope")
    statement = st.text_area("Policy Statement")
    procedures = st.text_area("Procedures")

    if st.button("Generate Policy"):

        body = {
            "Purpose and Scope": purpose,
            "Policy Statement": statement,
            "Procedures": procedures,
            "Owner": owner,
            "Approver": approver,
            "Effective Date": effective_date
        }

        doc = generate_docx(policy_name or "New Policy", body)

        st.download_button(
            label="Download Policy",
            data=doc,
            file_name=f"{policy_name or 'policy'}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
