import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<style>

/* ===== GLOBAL INPUT FIX ===== */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1px solid rgba(0,0,0,0.14) !important;
    border-radius: 14px !important;
}

/* ===== LABEL FIX ===== */
[data-testid="stWidgetLabel"] p {
    color: #111111 !important;
    font-weight: 600 !important;
}

/* ===== PLACEHOLDER FIX ===== */
input::placeholder,
textarea::placeholder {
    color: #8a8a8f !important;
    opacity: 1 !important;
}

</style>
""", unsafe_allow_html=True)
import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""
<style>

/* ===== GLOBAL INPUT FIX ===== */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1px solid rgba(0,0,0,0.14) !important;
    border-radius: 14px !important;
}

/* ===== LABEL FIX ===== */
[data-testid="stWidgetLabel"] p {
    color: #111111 !important;
    font-weight: 600 !important;
}

/* ===== PLACEHOLDER FIX ===== */
input::placeholder,
textarea::placeholder {
    color: #8a8a8f !important;
    opacity: 1 !important;
}

</style>
""", unsafe_allow_html=True)
