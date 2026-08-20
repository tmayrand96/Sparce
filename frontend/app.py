import sys
from io import BytesIO
from pathlib import Path

# Add project root directory to Python's import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.core.workforce_pipeline import SHIFT_OPTIONS, convert_workforce_pdf
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple

try:
    import streamlit as st
except ImportError:  # pragma: no cover - defensive fallback for test environments
    st = None


def detect_document_format(uploaded_file) -> Tuple[str, str]:
    """Return a normalized document type and a user-facing label for the upload."""
    if uploaded_file is None:
        return "unknown", "Detected Format: Waiting for upload"

    filename = getattr(uploaded_file, "name", "") or ""
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "pdf", "Detected Format: PDF Document"
    if suffix in {".png", ".jpg", ".jpeg"}:
        image_label = "PNG Image" if suffix == ".png" else "JPEG Image"
        return "image", f"Detected Format: {image_label}"

    return "unknown", "Detected Format: Unsupported Format"


def _get_logo_path() -> Optional[Path]:
    base_dir = Path(__file__).resolve().parent
    logo_path = base_dir / "assets" / "SPARCE-AI-LOGO.png"
    if logo_path.exists():
        return logo_path
    return None


def _render_custom_css() -> None:
    if st is None:
        return

    st.markdown(
        """
        <style>
        .stApp, .st-emotion-cache-1wmy9hl, .st-emotion-cache-1y4p8pa, .st-emotion-cache-1r6slb0 {
            background: #FFFFFF !important;
        }
        [data-testid="stSidebar"] {
            background: #FFFFFF !important;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 960px;
        }
        .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6,
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stCheckbox > label,
        .stRadio > label,
        .stButton button,
        [data-testid="stFileUploader"],
        [data-testid="stDownloadButton"],
        .stDownloadButton > button,
        .stAlert,
        .stAlert p,
        .stAlert label,
        .stCaption,
        .stDataFrame,
        .stDataFrame td,
        .stDataFrame th {
            color: #000000 !important;
        }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div,
        .stButton button,
        [data-testid="stFileUploader"],
        [data-testid="stDownloadButton"],
        .stDownloadButton > button,
        .stAlert {
            background: #FFFFFF !important;
            border: 1px solid #000000 !important;
        }
        .stButton button:hover,
        .stButton button:focus,
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stNumberInput > div > div > input:focus,
        .stSelectbox > div > div:focus,
        [data-testid="stFileUploader"]:focus-within,
        .stDownloadButton > button:focus {
            background: #FFFFFF !important;
            border-color: #000000 !important;
            box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.2) !important;
        }
        .hero-card {
            border: 1px solid #000000;
            border-radius: 20px;
            padding: 1.25rem 1.4rem;
            background: #FFFFFF;
            margin-bottom: 1rem;
        }
        .pill {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: #FFFFFF;
            color: #000000;
            font-weight: 600;
            margin-top: 0.35rem;
            border: 1px solid #000000;
        }
        .summary-card {
            border: 1px solid #000000;
            border-left: 4px solid #000000;
            padding: 1rem 1.1rem;
            border-radius: 16px;
            background: #FFFFFF;
            color: #000000;
            white-space: pre-wrap;
        }
        img, svg, .logo-container, [data-testid="stImage"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    if st is None:
        raise RuntimeError("streamlit must be installed to run the UI")

    st.set_page_config(page_title="Sparce AI", page_icon="🚀", layout="wide")
    _render_custom_css()

    logo_path = _get_logo_path()

    logo_col_1, logo_col_2, logo_col_3 = st.columns([1, 2, 1])
    with logo_col_2:
        if logo_path is not None:
            st.image(str(logo_path), width=280)
        else:
            st.title("Sparce AI")
        st.caption("Handwritten Notes & Document Intelligence")

    st.write("Upload a workforce report PDF and convert it into a formatted Excel file.")

    uploaded_file = st.file_uploader(
        "",
        type=["pdf"],
        help="Drag and drop or browse device (Accepted format: PDF)",
    )
    selected_shift = st.selectbox("Quart de travail", SHIFT_OPTIONS)

    if uploaded_file is not None:
        file_type, label = detect_document_format(uploaded_file)
        st.markdown(f"<div class='pill'>{label}</div>", unsafe_allow_html=True)

        if file_type == "pdf":
            st.markdown(
                "<div class='hero-card'><strong>PDF document ready for conversion.</strong></div>",
                unsafe_allow_html=True,
            )

    use_custom_prompt = st.checkbox("Enable Prompt", value=False, disabled=True)
    custom_question = ""
    if use_custom_prompt:  # Kept for compatibility with the former AI UI.
        custom_question = st.text_input("Ask a specific question about the document", disabled=True)

    challenge_mode = st.checkbox(
        "Challenge Me", value=False, key="challenge_mode_toggle", disabled=True
    )

    if st.button("Convert to XLSX", type="primary", use_container_width=True, disabled=uploaded_file is None):
        if uploaded_file is None:
            st.warning("Please upload a PDF before converting.")
        else:
            suffix = Path(getattr(uploaded_file, "name", "rapport.pdf")).suffix.lower() or ".pdf"
            with NamedTemporaryFile("wb", suffix=suffix, delete=False) as temp_file:
                uploaded_file.seek(0)
                temp_file.write(uploaded_file.getvalue())
                temp_path = temp_file.name

            st.caption(
                f"PDF size: {Path(temp_path).stat().st_size / 1024:.2f} KB. "
                "Native text extraction and OCR fallback enabled."
            )

            try:
                with st.spinner("Converting PDF to Excel..."):
                    workbook = convert_workforce_pdf(temp_path, selected_shift)
                original_name = Path(getattr(uploaded_file, "name", "report")).stem
                st.session_state["workforce_xlsx"] = workbook.getvalue()
                st.session_state["workforce_xlsx_file_name"] = f"{original_name}_{selected_shift.lower()}.xlsx"
            except Exception as exc:  # pragma: no cover - UI-level fallback
                st.session_state["workforce_xlsx_error"] = f"Conversion failed: {exc}"
            finally:
                Path(temp_path).unlink(missing_ok=True)

    if st.session_state.get("workforce_xlsx_error"):
        st.error(st.session_state["workforce_xlsx_error"])
    if st.session_state.get("workforce_xlsx"):
        st.download_button(
            "Download Excel File",
            data=st.session_state["workforce_xlsx"],
            file_name=st.session_state.get("workforce_xlsx_file_name", "output_effectifs.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_workforce_xlsx",
        )


if __name__ == "__main__":
    main()
