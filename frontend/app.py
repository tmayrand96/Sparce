import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

# Add project root directory to Python's import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.core.pipeline import process_document as run_pipeline
from backend.core.workforce_pipeline import SHIFT_OPTIONS, convert_workforce_pdf
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple

from PIL import Image, ImageOps

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

    st.write("Upload a handwritten note, scan, or PDF and turn it into a clean summary.")

    uploaded_file = st.file_uploader(
        "",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Drag and drop or browse device (Accepted formats: PNG, JPEG, PDF)",
    )
    selected_shift = st.selectbox("Quart de travail", SHIFT_OPTIONS)

    if uploaded_file is not None:
        file_type, label = detect_document_format(uploaded_file)
        st.markdown(f"<div class='pill'>{label}</div>", unsafe_allow_html=True)

        if file_type == "image":
            image_bytes = uploaded_file.getvalue()
            try:
                with Image.open(BytesIO(image_bytes)) as img:
                    corrected_image = ImageOps.exif_transpose(img)
                    st.image(corrected_image, use_container_width=True)
            except Exception:
                st.image(image_bytes, use_container_width=True)
        elif file_type == "pdf":
            st.markdown(
                "<div class='hero-card'><strong>📄 PDF document ready for processing.</strong><br>Preview and summary generation will begin once you trigger the pipeline.</div>",
                unsafe_allow_html=True,
            )

            if st.button("Générer le rapport Excel", type="primary", use_container_width=True):
                suffix = Path(getattr(uploaded_file, "name", "rapport.pdf")).suffix.lower() or ".pdf"
                with NamedTemporaryFile("wb", suffix=suffix, delete=False) as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                    temp_path = temp_file.name
                try:
                    with st.spinner("Conversion du rapport en Excel..."):
                        workbook = convert_workforce_pdf(temp_path, selected_shift)
                    original_name = Path(getattr(uploaded_file, "name", "rapport")).stem
                    st.download_button(
                        "Télécharger le rapport Excel",
                        data=workbook.getvalue(),
                        file_name=f"{original_name}_{selected_shift.lower()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_workforce_xlsx",
                    )
                    st.success("Rapport Excel généré.")
                except Exception as exc:  # pragma: no cover - UI-level fallback
                    st.error(f"Conversion échouée: {exc}")
                finally:
                    Path(temp_path).unlink(missing_ok=True)

    use_custom_prompt = st.checkbox("Enable Prompt", value=False)
    custom_question = ""
    if use_custom_prompt:
        custom_question = st.text_input(
            "Ask a specific question about the document",
            placeholder="e.g. What are the key takeaways?",
        )

    challenge_mode = st.checkbox("⚡ Challenge me", value=False, key="challenge_mode_toggle")

    if st.button("Generate Summary", type="primary", use_container_width=True, disabled=uploaded_file is None):
        if uploaded_file is None:
            st.warning("Please upload a document before generating a summary.")
        else:
            suffix = Path(getattr(uploaded_file, "name", "file")).suffix.lower() or ".bin"
            with NamedTemporaryFile("wb", suffix=suffix, delete=False) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_path = temp_file.name

            try:
                with st.spinner("Processing document..."):
                    summary = run_pipeline(
                        temp_path,
                        user_prompt=custom_question if use_custom_prompt else None,
                        max_output_tokens=300,
                        challenge_mode=challenge_mode,
                    )
                st.session_state["summary"] = summary
                st.session_state["challenge_mode"] = challenge_mode
                st.session_state.pop("summary_error", None)
                original_name = Path(getattr(uploaded_file, "name", "sparce_summary")).stem
                st.session_state["summary_file_name"] = (
                    f"{original_name}_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                )
            except Exception as exc:  # pragma: no cover - UI-level fallback
                st.session_state["summary_error"] = f"Processing failed: {exc}"
            finally:
                Path(temp_path).unlink(missing_ok=True)

    if "summary_error" in st.session_state and st.session_state["summary_error"]:
        st.error(st.session_state["summary_error"])

    if "summary" in st.session_state and st.session_state["summary"] and not st.session_state.get("summary_error"):
        if st.session_state.get("challenge_mode"):
            st.markdown("### Summary & Critical Analysis")
        else:
            st.markdown("### Summary")

        st.markdown(
            f"<div class='summary-card'>{st.session_state['summary'].replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )

        st.download_button(
            "📥 Download Summary (.md)",
            data=st.session_state["summary"],
            file_name=st.session_state.get("summary_file_name", "sparce_summary.md"),
            mime="text/markdown",
            key="download_summary",
        )


if __name__ == "__main__":
    main()
