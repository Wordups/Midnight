import os
from pathlib import Path
from datetime import datetime

import streamlit as st

from hps_policy_migration_builder_final import (
    build_policy_document,
    POLICY_DATA,
    DEFAULT_LOGO_PATH,
)

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
ASSETS_DIR = BASE_DIR / "assets"

for d in (UPLOADS_DIR, OUTPUTS_DIR, ASSETS_DIR):
    d.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Midnight Policy Migration", layout="wide")


def save_uploaded_file(uploaded_file, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    file_path = destination_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


@st.cache_data(show_spinner=False)
def process_logo_bytes(file_bytes: bytes) -> bytes:
    if not REMBG_AVAILABLE:
        raise RuntimeError(
            "Background removal requires rembg. Install it with: pip install rembg"
        )
    return remove(file_bytes)


def create_processed_logo(uploaded_file) -> Path:
    original_path = save_uploaded_file(uploaded_file, UPLOADS_DIR)
    base_name = Path(uploaded_file.name).stem
    processed_path = ASSETS_DIR / f"{base_name}_transparent.png"

    input_bytes = original_path.read_bytes()
    output_bytes = process_logo_bytes(input_bytes)
    processed_path.write_bytes(output_bytes)
    return processed_path


st.title("Midnight Policy Migration")
st.caption("Upload policy files, process a logo, and generate the final Word document.")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Migration Inputs")
    source_file = st.file_uploader(
        "Upload Source Policy",
        type=["docx", "doc", "pdf", "txt"],
        key="source_policy",
    )
    template_file = st.file_uploader(
        "Upload Target Template",
        type=["docx"],
        key="target_template",
    )

    st.subheader("Branding")
    logo_file = st.file_uploader(
        "Upload Logo",
        type=["png", "jpg", "jpeg", "webp"],
        key="logo_upload",
        help="PNG works best. JPG/JPEG/WEBP can be converted to a transparent PNG.",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        process_clicked = st.button("Process Logo", use_container_width=True)
    with col2:
        clear_clicked = st.button("Clear Logo", use_container_width=True)

    if clear_clicked:
        st.session_state.pop("processed_logo_path", None)
        st.session_state.pop("processed_logo_name", None)
        st.session_state.pop("original_logo_path", None)
        st.success("Logo selection cleared.")

    if process_clicked:
        if logo_file is None:
            st.warning("Upload a logo first.")
        else:
            try:
                original_path = save_uploaded_file(logo_file, UPLOADS_DIR)
                st.session_state["original_logo_path"] = str(original_path)

                if logo_file.type == "image/png":
                    processed_path = ASSETS_DIR / f"{Path(logo_file.name).stem}_transparent.png"
                    processed_path.write_bytes(original_path.read_bytes())
                else:
                    processed_path = create_processed_logo(logo_file)

                st.session_state["processed_logo_path"] = str(processed_path)
                st.session_state["processed_logo_name"] = processed_path.name
                st.success("Logo processed and ready for the template header.")
            except Exception as exc:
                st.error(f"Logo processing failed: {exc}")

with right:
    st.subheader("Logo Preview")
    processed_logo_path = st.session_state.get("processed_logo_path")
    if processed_logo_path and Path(processed_logo_path).exists():
        st.image(processed_logo_path, caption=Path(processed_logo_path).name, use_container_width=True)
    elif Path(DEFAULT_LOGO_PATH).exists():
        st.info("No processed logo yet. Default logo is currently active.")
        st.image(DEFAULT_LOGO_PATH, caption="Default Logo", use_container_width=True)
    else:
        st.info("Upload a logo to preview it here.")

    st.subheader("Current Files")
    st.write(f"Source policy: {source_file.name if source_file else 'Not uploaded'}")
    st.write(f"Template: {template_file.name if template_file else 'Not uploaded'}")
    st.write(
        f"Active logo: {st.session_state.get('processed_logo_name', Path(DEFAULT_LOGO_PATH).name)}"
    )

st.divider()

st.subheader("Generate Document")
output_default_name = (
    f"{POLICY_DATA['policy_number']} {POLICY_DATA['policy_name']} {POLICY_DATA['version']}-NEW.docx"
)
output_name = st.text_input("Output filename", value=output_default_name)

if st.button("Run Migration", type="primary", use_container_width=True):
    try:
        active_logo_path = st.session_state.get("processed_logo_path", DEFAULT_LOGO_PATH)
        output_path = OUTPUTS_DIR / output_name

        # Keep uploaded files on disk for downstream logic even if this builder does not use them yet.
        if source_file is not None:
            save_uploaded_file(source_file, UPLOADS_DIR)
        if template_file is not None:
            save_uploaded_file(template_file, UPLOADS_DIR)

        build_policy_document(
            data=POLICY_DATA,
            output_path=str(output_path),
            logo_path=str(active_logo_path) if active_logo_path else None,
        )

        st.success(f"Document generated: {output_path.name}")
        with open(output_path, "rb") as f:
            st.download_button(
                "Download Final Document",
                data=f,
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    except Exception as exc:
        st.error(f"Document generation failed: {exc}")

with st.expander("Notes"):
    st.markdown(
        """
- Put `app.py` in the same folder as `hps_policy_migration_builder_final.py`.
- If JPG/JPEG/WEBP background removal does not work yet, install `rembg` first.
- The builder uses the processed logo in the top gray banner.
- Source policy and template uploads are saved and ready for future extraction/template logic.
        """
    )
