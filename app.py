"""
MIDNIGHT — Policy Migration Engine
Takeoff Product
"""

import os
import tempfile
from datetime import datetime, date

import streamlit as st
from groq import Groq
from docx import Document
from hps_policy_migration_builder import build_policy_document

# ── rembg removed — causes model download timeout on Streamlit Cloud ──────────
REMBG_OK = False


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════════════════════
LOCAL_GROQ_API_KEY = ""

TEMPLATE_OPTIONS = [
    "Generic Policy Template",
    "Wipro HealthPlan Services",
]

PAGE_OPTIONS = ["Overview", "Migrate a Policy", "Create a Policy"]

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
  "para"           = standalone paragraph
  "heading"        = bold underlined subsection title
  "bullet"         = first-level bullet
  "sub-bullet"     = second-level bullet
  "bold_intro"     = paragraph that starts with a bold label; use keys "bold" and "rest"
  "bold_intro_semi"= same as bold_intro but "rest" contains semicolons
  "empty"          = blank spacer line

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
        "hps_inc": False,
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


# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Midnight",
    page_icon="🌑",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═════════════════════════════════════════════════════════════════════════════
_defaults = {
    "page":                  "Overview",
    "selected_template":     TEMPLATE_OPTIONS[0],
    "migration_policy_data": None,
    "created_policy_data":   None,
    "logo_path":             None,
    "logo_preview_name":     "",
    "migration_filename":    None,
    "migration_docx":        None,
    "created_filename":      None,
    "created_docx":          None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ═════════════════════════════════════════════════════════════════════════════
# CSS — Palo Alto Networks design language
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
html, body, [class*="css"] { background: transparent !important; }

:root {
    --bg:      #020916;
    --s1:      #0a1628;
    --s2:      #0d1b2e;
    --s3:      #111f36;
    --b0:      rgba(255,255,255,0.06);
    --b1:      rgba(255,255,255,0.10);
    --b2:      rgba(255,255,255,0.16);
    --t0:      #ffffff;
    --t1:      #e8edf5;
    --t2:      #8a9bb5;
    --t3:      #4f6180;
    --cyan:    #00c3e3;
    --cyan-bg: rgba(0,195,227,0.10);
    --cyan-bd: rgba(0,195,227,0.28);
    --orange:  #fa5a28;
    --green:   #00d68f;
    --green-bg:rgba(0,214,143,0.10);
    --green-bd:rgba(0,214,143,0.28);
    --r:       8px;
    --rl:      10px;
}

.stApp {
    background: var(--bg) !important;
    color: var(--t1);
    font-family: 'Inter','Segoe UI',system-ui,sans-serif;
}

.block-container {
    max-width: 1300px !important;
    padding-top: 0.8rem !important;
    padding-bottom: 2rem !important;
    background: transparent !important;
}

header { visibility: hidden !important; }
div[data-testid="stVerticalBlock"] > div { background: transparent !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── Nav bar ─────────────────────────────────────────────────────────────── */
.mn-bar {
    background: var(--s1);
    border: 1px solid var(--b0);
    border-radius: var(--rl);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}
.mn-brand { display: flex; flex-direction: column; }
.mn-eye {
    color: var(--t3);
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    margin-bottom: 1px;
}
.mn-name {
    color: var(--t0);
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.07em;
}
.mn-sub { color: var(--t3); font-size: 11px; margin-top: 1px; }

/* Nav radio → pills */
div[data-testid="stRadio"] > div { gap: 3px; flex-direction: row !important; }
div[data-testid="stRadio"] label {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 6px !important;
    padding: 5px 13px !important;
    transition: all .15s ease;
}
div[data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,0.04) !important;
}
div[data-testid="stRadio"] label p {
    color: var(--t3) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background: var(--cyan-bg) !important;
    border-color: var(--cyan-bd) !important;
}
div[data-testid="stRadio"] label:has(input:checked) p {
    color: var(--cyan) !important;
    font-weight: 600 !important;
}

/* ── Hero ────────────────────────────────────────────────────────────────── */
.mn-hero {
    background: var(--s1);
    border: 1px solid var(--b0);
    border-radius: var(--rl);
    padding: 38px 32px;
    margin-bottom: 10px;
    position: relative;
    overflow: hidden;
}
.mn-hero::after {
    content: '';
    position: absolute;
    top: -50px; right: -70px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(0,195,227,0.07), transparent 65%);
    pointer-events: none;
}
.mn-hero-eye {
    color: var(--cyan);
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 14px;
}
.mn-hero-h {
    color: var(--t0);
    font-size: 34px;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.01em;
    margin-bottom: 12px;
}
.mn-hero-h .hl { color: var(--cyan); }
.mn-hero-b {
    color: var(--t2);
    font-size: 15px;
    line-height: 1.65;
    max-width: 560px;
    margin-bottom: 0;
}

/* ── Cards ───────────────────────────────────────────────────────────────── */
.mn-card {
    background: var(--s1);
    border: 1px solid var(--b0);
    border-radius: var(--rl);
    padding: 18px;
    height: 100%;
}
.mn-card-d {
    background: var(--s2);
    border: 1px solid var(--b0);
    border-radius: var(--rl);
    padding: 20px;
    height: 100%;
}
.mn-card-t {
    color: var(--t0);
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
}
.mn-card-b { color: var(--t2); font-size: 13px; line-height: 1.58; }

.mn-icon {
    width: 28px; height: 28px;
    background: var(--cyan-bg);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 10px;
    font-size: 14px;
}

/* Stats */
.mn-stats { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.mn-stat {
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--b0);
    border-radius: 8px;
    padding: 12px 14px;
    min-width: 110px;
}
.mn-stat-n { color: var(--cyan); font-size: 24px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.mn-stat-l { color: var(--t3); font-size: 11px; line-height: 1.4; }

/* ── Workspace ───────────────────────────────────────────────────────────── */
.mn-ws-t { color: var(--t0); font-size: 20px; font-weight: 700; margin-bottom: 3px; }
.mn-ws-s { color: var(--t2); font-size: 13px; margin-bottom: 14px; }

/* ── Note / info boxes ───────────────────────────────────────────────────── */
.mn-note {
    background: var(--s2);
    border-left: 2px solid var(--b2);
    border-radius: 0 6px 6px 0;
    padding: 9px 12px;
    color: var(--t2);
    font-size: 12px;
    line-height: 1.55;
    margin: 8px 0;
}
.mn-note strong { color: var(--t1); }

.mn-success {
    background: var(--green-bg);
    border: 1px solid var(--green-bd);
    border-radius: 8px;
    padding: 9px 14px;
    color: #4df0b8;
    font-weight: 600;
    text-align: center;
    margin: 8px 0;
    font-size: 13px;
}

.mn-preview {
    background: var(--s2);
    border: 1px solid var(--b0);
    border-radius: 8px;
    padding: 14px;
}

.mn-caption {
    color: var(--t3);
    font-size: 11px;
    margin-bottom: 6px;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
.stButton > button {
    width: 100% !important;
    background: var(--cyan) !important;
    color: #000 !important;
    border: none !important;
    border-radius: var(--r) !important;
    padding: 9px 14px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    transition: opacity .15s, transform .12s !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    opacity: 0.87 !important;
    transform: translateY(-1px) !important;
}
.stButton > button p,
.stButton > button span,
.stButton > button div { color: #000 !important; }

.stDownloadButton > button {
    width: 100% !important;
    background: var(--s2) !important;
    color: var(--t1) !important;
    border: 1px solid var(--b1) !important;
    border-radius: var(--r) !important;
    padding: 9px 14px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover {
    border-color: var(--cyan) !important;
    color: var(--cyan) !important;
}

.stTextInput input,
.stTextArea textarea {
    background: var(--s2) !important;
    color: var(--t1) !important;
    border: 1px solid var(--b0) !important;
    border-radius: var(--r) !important;
    font-size: 13px !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 2px rgba(0,195,227,0.12) !important;
}

.stSelectbox > div > div {
    background: var(--s2) !important;
    border: 1px solid var(--b0) !important;
    border-radius: var(--r) !important;
    color: var(--t1) !important;
}

[data-testid="stWidgetLabel"] p {
    color: var(--t1) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}

.stFileUploader > div {
    background: var(--s2) !important;
    border: 1px dashed var(--b1) !important;
    border-radius: var(--r) !important;
}

.stProgress > div > div { background: var(--cyan) !important; }

.stAlert {
    background: var(--s2) !important;
    border: 1px solid var(--b0) !important;
    border-radius: var(--r) !important;
    color: var(--t1) !important;
}

input::placeholder, textarea::placeholder {
    color: var(--t3) !important;
    opacity: 1 !important;
}

h1, h2, h3, h4 { color: var(--t0) !important; }
p { color: var(--t2); }

/* Expander */
details summary { color: var(--t2) !important; font-size: 13px !important; }
details { background: var(--s2) !important; border: 1px solid var(--b0) !important; border-radius: var(--r) !important; }

/* Gap util */
.gap { height: 8px; }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS  (document-4 working logic — unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def get_api_key() -> str:
    try:
        secret = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret = ""
    return secret or os.getenv("GROQ_API_KEY", "") or LOCAL_GROQ_API_KEY


def parse_policy_data(raw_output: str):
    if "POLICY_DATA = {" in raw_output:
        dict_str = raw_output[raw_output.index("POLICY_DATA = {"):]
    else:
        dict_str = raw_output
    dict_str = (dict_str
                .replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2019", "'"))
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
                ct = " ".join(
                    para.text.strip() for para in cell.paragraphs if para.text.strip()
                ).strip()
                if ct:
                    row_text.append(ct)
            if row_text:
                lines.append(" | ".join(row_text))
    return "\n".join(lines)


def get_uploaded_text(uploaded_file) -> str:
    if uploaded_file.name.lower().endswith(".docx"):
        return extract_text_from_docx(uploaded_file)
    return uploaded_file.read().decode("utf-8", errors="ignore")


def normalize_date_input(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return f"{dt.month}/{dt.day}/{dt.year}"
        except Exception:
            pass
    return value


def parse_date_safe(value: str):
    value = normalize_date_input(value)
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%d/%Y")
    except Exception:
        return None


def default_if_blank(current: str, source: str) -> str:
    return current if str(current).strip() else source


def validate_dates(effective_date, last_reviewed, last_revised, date_signed, date_approved):
    errors = []
    eff    = parse_date_safe(effective_date)
    revw   = parse_date_safe(last_reviewed)
    revd   = parse_date_safe(last_revised)
    signed = parse_date_safe(date_signed)
    approv = parse_date_safe(date_approved)
    if eff and revw   and revw   < eff:    errors.append("Last Reviewed cannot be earlier than Effective Date.")
    if eff and revd   and revd   < eff:    errors.append("Last Revised cannot be earlier than Effective Date.")
    if signed and approv and approv < signed: errors.append("Date Approved cannot be earlier than Date Signed.")
    return errors


def split_lines(text: str):
    return [l.strip() for l in str(text).splitlines() if l.strip()]


def make_procedures_from_text(text: str):
    procs = []
    for line in split_lines(text):
        if line.startswith("- "):
            procs.append({"type": "bullet", "text": line[2:].strip()})
        else:
            procs.append({"type": "para",   "text": line})
    return procs


def build_creation_policy_data(
    policy_name, policy_number, version, grc_id, supersedes,
    effective_date, last_reviewed, last_revised, custodians,
    owner_name, owner_title, approver_name, approver_title,
    date_signed, date_approved, purpose, definitions_text,
    policy_statement, procedures_text, related_policies_text,
    citations_text, template_name,
):
    effective_date = normalize_date_input(effective_date)
    last_reviewed  = normalize_date_input(default_if_blank(last_reviewed,  effective_date))
    last_revised   = normalize_date_input(default_if_blank(last_revised,   effective_date))
    date_signed    = normalize_date_input(default_if_blank(date_signed,    effective_date))
    date_approved  = normalize_date_input(default_if_blank(date_approved,  date_signed))

    definitions = {}
    for line in split_lines(definitions_text):
        if ":" in line:
            k, v = line.split(":", 1)
            definitions[k.strip()] = v.strip()
        else:
            definitions[line.strip()] = ""

    return {
        "policy_name":    policy_name,
        "policy_number":  policy_number,
        "version":        version or "V1.0",
        "grc_id":         grc_id,
        "supersedes":     supersedes,
        "effective_date": effective_date,
        "last_reviewed":  last_reviewed,
        "last_revised":   last_revised,
        "custodians":     custodians,
        "owner_name":     owner_name,
        "owner_title":    owner_title,
        "approver_name":  approver_name,
        "approver_title": approver_title,
        "date_signed":    date_signed,
        "date_approved":  date_approved,
        "applicable_to":  {"hps_inc": False, "agency": True, "corporate": True,
                           "govt_affairs": False, "legal_review": False},
        "policy_types":   {"carrier_specific": False, "cross_carrier": False,
                           "global": template_name == "Generic Policy Template",
                           "on_off_hix": False},
        "line_of_business": {"all_lobs": True, "specific_lob": "", "specific_lob_checked": False},
        "purpose":          purpose,
        "definitions":      definitions,
        "policy_statement": policy_statement,
        "procedures":       make_procedures_from_text(procedures_text),
        "related_policies": split_lines(related_policies_text),
        "citations":        split_lines(citations_text),
        "revision_history": [],
        "template_name":    template_name,
    }


def save_logo(uploaded_file) -> str:
    """Save logo as-is to /tmp. rembg disabled on Cloud."""
    tmp_dir = os.path.join(tempfile.gettempdir(), "midnight_logos")
    os.makedirs(tmp_dir, exist_ok=True)
    stem = "".join(c for c in os.path.splitext(uploaded_file.name)[0]
                   if c.isalnum() or c in "-_") or "logo"
    ext  = os.path.splitext(uploaded_file.name)[1].lower()
    out  = os.path.join(tmp_dir, f"{stem}{ext}")
    with open(out, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return out


def render_logo_controls(key: str):
    st.markdown('<div class="mn-caption">Optional — upload a logo for the document header.</div>',
                unsafe_allow_html=True)
    logo_file = st.file_uploader(
        "Logo", type=["png", "jpg", "jpeg", "webp"],
        key=f"logo_{key}", label_visibility="collapsed",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Set Logo", key=f"set_{key}"):
            if not logo_file:
                st.error("Upload a logo first.")
            else:
                try:
                    path = save_logo(logo_file)
                    st.session_state["logo_path"]         = path
                    st.session_state["logo_preview_name"] = logo_file.name
                    st.success("Logo set.")
                except Exception as e:
                    st.error(f"Logo error: {e}")
    with c2:
        if st.button("Clear Logo", key=f"clr_{key}"):
            st.session_state["logo_path"]         = None
            st.session_state["logo_preview_name"] = ""
            st.success("Cleared.")

    lp = st.session_state.get("logo_path")
    if lp and os.path.exists(lp):
        st.image(lp, caption=st.session_state.get("logo_preview_name","Logo"),
                 use_container_width=True)


def render_policy_preview(policy_data: dict):
    st.markdown('<div class="mn-preview">', unsafe_allow_html=True)
    st.markdown(f"### {policy_data.get('policy_name','—')}")
    st.markdown(
        f"**{policy_data.get('policy_number','')}** &nbsp;·&nbsp; "
        f"**{policy_data.get('version','')}** &nbsp;·&nbsp; "
        f"{policy_data.get('effective_date','')}"
    )
    st.divider()
    st.markdown(f"**Owner:** {policy_data.get('owner_name','')} — {policy_data.get('owner_title','')}")
    st.markdown(f"**Approver:** {policy_data.get('approver_name','')} — {policy_data.get('approver_title','')}")

    purpose = policy_data.get("purpose","")
    if purpose:
        st.markdown("#### Purpose")
        st.write(purpose[:500] + ("…" if len(purpose) > 500 else ""))

    stmt = policy_data.get("policy_statement","")
    if stmt:
        st.markdown("#### Policy Statement")
        st.write(stmt[:350] + ("…" if len(stmt) > 350 else ""))

    defs = policy_data.get("definitions") or {}
    if defs:
        st.markdown("#### Definitions")
        for k, v in list(defs.items())[:4]:
            st.markdown(f"- **{k}:** {v}")
        if len(defs) > 4:
            st.caption(f"+ {len(defs)-4} more")

    procs = policy_data.get("procedures") or []
    if procs:
        st.markdown("#### Procedures")
        for item in procs[:6]:
            kind = item.get("type","")
            text = item.get("text","") or item.get("rest","")
            if kind == "bullet":        st.markdown(f"- {text}")
            elif kind == "sub-bullet":  st.markdown(f"  - {text}")
            elif kind == "heading":     st.markdown(f"**{text}**")
            elif kind in ("bold_intro","bold_intro_semi"):
                st.markdown(f"**{item.get('bold','')}** {item.get('rest','')}")
            elif text:                  st.write(text)
        if len(procs) > 6:
            st.caption(f"+ {len(procs)-6} more items")

    rev = policy_data.get("revision_history") or []
    if rev:
        st.markdown(f"#### Revision History  ({len(rev)} entries)")

    st.markdown("</div>", unsafe_allow_html=True)


def build_output_doc(policy_data: dict, logo_path=None) -> tuple[str, bytes]:
    name   = policy_data.get("policy_name",   "Policy")
    number = policy_data.get("policy_number", "SEC-P")
    ver    = policy_data.get("version",       "V1.0")
    fname  = f"{number} {name} {ver}-NEW.docx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name

    build_policy_document(policy_data, tmp_path, logo_path=logo_path)

    with open(tmp_path, "rb") as f:
        docx_bytes = f.read()

    os.unlink(tmp_path)
    return fname, docx_bytes


def run_llm_transform(source_text: str, template_name: str):
    api_key = get_api_key()
    if not api_key:
        st.error("No Groq API key. Set GROQ_API_KEY in Streamlit secrets.")
        return None

    prog   = st.progress(0)
    status = st.empty()

    try:
        status.markdown('<div class="mn-caption">Reading document…</div>', unsafe_allow_html=True)
        prog.progress(15)

        client = Groq(api_key=api_key)

        status.markdown('<div class="mn-caption">Extracting policy structure…</div>', unsafe_allow_html=True)
        prog.progress(35)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": EXTRACTION_PROMPT + "\n\n" + source_text}],
            temperature=0.1,
            max_tokens=8000,
        )

        raw = response.choices[0].message.content.strip()

        status.markdown('<div class="mn-caption">Parsing extracted data…</div>', unsafe_allow_html=True)
        prog.progress(65)

        policy_data = parse_policy_data(raw)

        if not policy_data:
            st.error("Model response could not be parsed into POLICY_DATA.")
            with st.expander("Raw model output"):
                st.code(raw)
            return None

        policy_data["template_name"] = template_name
        prog.progress(100)
        status.empty()
        return policy_data

    except Exception as e:
        prog.empty()
        status.empty()
        st.error(f"Extraction failed: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# NAV
# ═════════════════════════════════════════════════════════════════════════════
nav_l, nav_r = st.columns([0.52, 0.48])

with nav_l:
    st.markdown("""
    <div class="mn-bar">
        <div class="mn-brand">
            <div class="mn-eye">Takeoff Product</div>
            <div class="mn-name">MIDNIGHT</div>
            <div class="mn-sub">Policy Migration Engine</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with nav_r:
    st.markdown('<div style="padding-top:14px"></div>', unsafe_allow_html=True)
    selected = st.radio(
        "nav", PAGE_OPTIONS, horizontal=True,
        label_visibility="collapsed",
        index=PAGE_OPTIONS.index(st.session_state["page"]),
        key="top_nav",
    )
    st.session_state["page"] = selected


# ═════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "Overview":

    st.markdown("""
    <div class="mn-hero">
        <div class="mn-hero-eye">Policy intelligence engine</div>
        <div class="mn-hero-h">Migrate. Create.<br><span class="hl">Ship cleaner policy.</span></div>
        <div class="mn-hero-b">Convert legacy documents and structured intake into audit-ready,
        template-faithful Word output — without the manual effort.</div>
    </div>
    """, unsafe_allow_html=True)

    cta1, cta2, _sp = st.columns([0.18, 0.18, 0.64])
    with cta1:
        if st.button("Migrate a Policy", key="ov_migrate"):
            st.session_state["page"]    = "Migrate a Policy"
            st.session_state["top_nav"] = "Migrate a Policy"
            st.session_state["top_nav"] = "Migrate a Policy"
            st.rerun()
    with cta2:
        if st.button("Create a Policy", key="ov_create"):
            st.session_state["page"]    = "Create a Policy"
            st.session_state["top_nav"] = "Create a Policy"
            st.session_state["top_nav"] = "Create a Policy"
            st.rerun()

    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="mn-card">
            <div class="mn-icon">↑</div>
            <div class="mn-card-t">Migrate Policy</div>
            <div class="mn-card-b">Upload a legacy .docx, .txt, or .md and convert it
            using AI extraction into the selected template.</div>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="mn-card">
            <div class="mn-icon">+</div>
            <div class="mn-card-t">Create Policy</div>
            <div class="mn-card-b">Build a new policy from structured intake with smart
            date defaults, inline preview, and controlled final output.</div>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="mn-card">
            <div class="mn-icon">↓</div>
            <div class="mn-card-t">Download Ready</div>
            <div class="mn-card-b">Review extracted data, then generate a pixel-faithful
            HPS-template Word document in one click.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    bl, br = st.columns([0.55, 0.45], gap="large")
    with bl:
        st.markdown("""
        <div class="mn-card-d">
            <div class="mn-card-t" style="font-size:16px;margin-bottom:8px">
                Built for policy operations teams
            </div>
            <div class="mn-card-b">
                Manual policy updates create inconsistency and slow audit prep.
                Midnight provides a controlled path from source content to final
                document — extraction, preview, and generation in one workflow.
            </div>
            <div class="mn-stats">
                <div class="mn-stat">
                    <div class="mn-stat-n">80h</div>
                    <div class="mn-stat-l">Reducible manual effort across a typical backlog</div>
                </div>
                <div class="mn-stat">
                    <div class="mn-stat-n">1</div>
                    <div class="mn-stat-l">Structured workflow from source to final output</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with br:
        st.markdown("""
        <div class="mn-card">
            <div class="mn-card-t" style="font-size:15px;margin-bottom:8px">How it works</div>
            <div class="mn-card-b">
                Select a template, choose a workflow, upload or enter content,
                review the live preview, then generate the final document.<br><br>
                Supports .docx, .txt, and .md source files. Revision history,
                definitions, and all metadata carry through automatically.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MIGRATE A POLICY
# ═════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "Migrate a Policy":

    st.markdown('<div class="mn-ws-t">Migrate a Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="mn-ws-s">Convert an existing document into a structured template.</div>',
                unsafe_allow_html=True)

    left, right = st.columns([0.34, 0.66], gap="medium")

    with left:
        st.markdown('<div class="mn-card">', unsafe_allow_html=True)
        st.markdown('<div class="mn-card-t">Settings</div>', unsafe_allow_html=True)

        sel = st.selectbox(
            "Target Template", TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="m_tmpl",
        )
        st.session_state["selected_template"] = sel

        st.markdown("""
        <div class="mn-note">
            <strong>Workflow:</strong> Upload → Transform → Review preview → Generate final document.
        </div>
        """, unsafe_allow_html=True)

        render_logo_controls("migrate")
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="mn-card">', unsafe_allow_html=True)
        st.markdown('<div class="mn-card-t">Upload Legacy Policy</div>', unsafe_allow_html=True)
        st.markdown('<div class="mn-caption">Supported: .docx, .txt, .md</div>',
                    unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "upload", type=["docx", "txt", "md"],
            label_visibility="collapsed", key="m_upload",
        )

        st.markdown("""
        <div class="mn-note">
            <strong>Note:</strong> API key is configured via Streamlit secrets on the backend.
        </div>
        """, unsafe_allow_html=True)

        run_btn = st.button("Transform Policy", key="m_run")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    st.markdown('<div class="mn-card">', unsafe_allow_html=True)
    st.markdown('<div class="mn-card-t">Preview</div>', unsafe_allow_html=True)
    if st.session_state["migration_policy_data"]:
        render_policy_preview(st.session_state["migration_policy_data"])
    else:
        st.markdown("""
        <div class="mn-note">
            Upload a document and click Transform to preview the extracted policy here.
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if run_btn:
        if not uploaded:
            st.error("Please upload a legacy policy document.")
            st.stop()
        src = get_uploaded_text(uploaded)
        if len(src.strip()) < 50:
            st.error("Document appears empty or too short.")
            st.stop()
        pd = run_llm_transform(src, st.session_state["selected_template"])
        if pd:
            st.session_state["migration_policy_data"] = pd
            st.session_state["migration_docx"]        = None
            st.session_state["migration_filename"]    = None
            st.rerun()

    if st.session_state["migration_policy_data"]:
        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
        _, gc, _ = st.columns([1, 1.2, 1])
        with gc:
            if st.button("Generate Final Document", key="m_gen"):
                try:
                    fname, docx_bytes = build_output_doc(
                        st.session_state["migration_policy_data"],
                        logo_path=st.session_state.get("logo_path"),
                    )
                    st.session_state["migration_filename"] = fname
                    st.session_state["migration_docx"]     = docx_bytes
                except Exception as e:
                    st.error(f"Build failed: {e}")

            if st.session_state.get("migration_docx"):
                st.markdown('<div class="mn-success">✓ Transformation complete</div>',
                            unsafe_allow_html=True)
                st.download_button(
                    label=f"↓  Download  {st.session_state['migration_filename']}",
                    data=st.session_state["migration_docx"],
                    file_name=st.session_state["migration_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="m_dl",
                )


# ═════════════════════════════════════════════════════════════════════════════
# CREATE A POLICY
# ═════════════════════════════════════════════════════════════════════════════
else:

    st.markdown('<div class="mn-ws-t">Create a Policy</div>', unsafe_allow_html=True)
    st.markdown('<div class="mn-ws-s">Generate a new policy from structured intake.</div>',
                unsafe_allow_html=True)

    sl, fl = st.columns([0.34, 0.66], gap="medium")

    with sl:
        st.markdown('<div class="mn-card">', unsafe_allow_html=True)
        st.markdown('<div class="mn-card-t">Settings</div>', unsafe_allow_html=True)

        sel = st.selectbox(
            "Target Template", TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(st.session_state["selected_template"]),
            key="c_tmpl",
        )
        st.session_state["selected_template"] = sel

        st.markdown("""
        <div class="mn-note">
            Blank date fields auto-fill from the Effective Date.
        </div>
        """, unsafe_allow_html=True)

        render_logo_controls("create")
        st.markdown('</div>', unsafe_allow_html=True)

    with fl:
        st.markdown('<div class="mn-card">', unsafe_allow_html=True)
        st.markdown('<div class="mn-card-t">Intake</div>', unsafe_allow_html=True)

        with st.form("create_form"):
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                policy_name    = st.text_input("Policy Name",    value="")
                policy_number  = st.text_input("Policy Number",  value="")
                version        = st.text_input("Version",        value="V1.0")
                grc_id         = st.text_input("GRC ID",         value="")
                today          = date.today()
                effective_date = st.text_input(
                    "Effective Date",
                    value=f"{today.month}/{today.day}/{today.year}",
                )
                last_reviewed  = st.text_input("Last Reviewed", value="",
                                               placeholder="Defaults to Effective Date")
                last_revised   = st.text_input("Last Revised",  value="",
                                               placeholder="Defaults to Effective Date")
                supersedes     = st.text_input("Supersedes",    value="")
            with r1c2:
                custodians     = st.text_input("Custodians",     value="")
                owner_name     = st.text_input("Owner Name",     value="")
                owner_title    = st.text_input("Owner Title",    value="")
                approver_name  = st.text_input("Approver Name",  value="")
                approver_title = st.text_input("Approver Title", value="")
                date_signed    = st.text_input("Date Signed",    value="",
                                               placeholder="Defaults to Effective Date")
                date_approved  = st.text_input("Date Approved",  value="",
                                               placeholder="Defaults to Date Signed")

            purpose                = st.text_area("Purpose and Scope",         height=100)
            definitions_text       = st.text_area("Definitions  (Term: Definition, one per line)", height=90)
            policy_statement       = st.text_area("Policy Statement",           height=110)
            procedures_text        = st.text_area("Procedures  (use '- ' for bullets)", height=160)
            related_policies_text  = st.text_area("Related Policies  (one per line)", height=80)
            citations_text         = st.text_area("Citations / References  (one per line)", height=80)

            preview_btn = st.form_submit_button("Build Preview")

        st.markdown('</div>', unsafe_allow_html=True)

    preview_defaults = {
        "last_reviewed": normalize_date_input(default_if_blank(last_reviewed, effective_date)),
        "last_revised":  normalize_date_input(default_if_blank(last_revised,  effective_date)),
        "date_signed":   normalize_date_input(default_if_blank(date_signed,   effective_date)),
        "date_approved": normalize_date_input(
            default_if_blank(date_approved, default_if_blank(date_signed, effective_date))
        ),
    }

    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    dfl, prl = st.columns([0.38, 0.62], gap="medium")

    with dfl:
        st.markdown('<div class="mn-card">', unsafe_allow_html=True)
        st.markdown('<div class="mn-card-t">Smart Defaults</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="mn-note">
            <strong>Last Reviewed:</strong> {preview_defaults["last_reviewed"] or "—"}<br>
            <strong>Last Revised:</strong>  {preview_defaults["last_revised"]  or "—"}<br>
            <strong>Date Signed:</strong>   {preview_defaults["date_signed"]   or "—"}<br>
            <strong>Date Approved:</strong> {preview_defaults["date_approved"] or "—"}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with prl:
        st.markdown('<div class="mn-card">', unsafe_allow_html=True)
        st.markdown('<div class="mn-card-t">Preview</div>', unsafe_allow_html=True)
        if st.session_state["created_policy_data"]:
            render_policy_preview(st.session_state["created_policy_data"])
        else:
            st.markdown("""
            <div class="mn-note">
                Complete the intake form and click Build Preview.
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if preview_btn:
        errs = validate_dates(
            effective_date,
            preview_defaults["last_reviewed"],
            preview_defaults["last_revised"],
            preview_defaults["date_signed"],
            preview_defaults["date_approved"],
        )
        if errs:
            for e in errs:
                st.error(e)
        else:
            pd = build_creation_policy_data(
                policy_name, policy_number, version, grc_id, supersedes,
                effective_date, last_reviewed, last_revised, custodians,
                owner_name, owner_title, approver_name, approver_title,
                date_signed, date_approved, purpose, definitions_text,
                policy_statement, procedures_text, related_policies_text,
                citations_text, st.session_state["selected_template"],
            )
            st.session_state["created_policy_data"] = pd
            st.session_state["created_docx"]        = None
            st.session_state["created_filename"]    = None
            st.rerun()

    if st.session_state["created_policy_data"]:
        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
        _, gc, _ = st.columns([1, 1.2, 1])
        with gc:
            if st.button("Generate Policy Document", key="c_gen"):
                try:
                    fname, docx_bytes = build_output_doc(
                        st.session_state["created_policy_data"],
                        logo_path=st.session_state.get("logo_path"),
                    )
                    st.session_state["created_filename"] = fname
                    st.session_state["created_docx"]     = docx_bytes
                except Exception as e:
                    st.error(f"Build failed: {e}")

            if st.session_state.get("created_docx"):
                st.markdown('<div class="mn-success">✓ Policy generated</div>',
                            unsafe_allow_html=True)
                st.download_button(
                    label=f"↓  Download  {st.session_state['created_filename']}",
                    data=st.session_state["created_docx"],
                    file_name=st.session_state["created_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="c_dl",
                )
