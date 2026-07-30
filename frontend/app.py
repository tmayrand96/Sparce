import sys
from io import BytesIO
from pathlib import Path

# Add project root directory to Python's import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.core.pipeline import process_document as run_pipeline
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple

from PIL import Image, ImageOps

try:
    import streamlit as st
except ImportError:  # pragma: no cover - defensive fallback for test environments
    st = None

from backend.core.pipeline import process_document as run_pipeline


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
        .stApp {
            background: #FFFFFF;
            color: #111827;
        }
        header, .main, .block-container {
            background: #FFFFFF;
            color: #111827;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 960px;
        }
        html, body, div, span, p, h1, h2, h3, h4, h5, h6, label, .stMarkdown, .stTextInput, .stSelectbox {
            color: #111827 !important;
        }
        .hero-card {
            border: 1px solid #E5E7EB;
            border-radius: 20px;
            padding: 1.25rem 1.4rem;
            background: #FFFFFF;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.06);
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }
        .pill {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: #F3F4F6;
            color: #111827;
            font-weight: 600;
            margin-top: 0.35rem;
            border: 1px solid #D1D5DB;
        }
        div[data-testid="stButton"] > button {
            width: 100%;
            border-radius: 999px;
            border: 1px solid #2563EB;
            background: #2563EB;
            color: #FFFFFF;
            font-weight: 700;
            padding: 0.7rem 1rem;
        }
        div[data-testid="stButton"] > button:hover {
            background: #1D4ED8;
            border-color: #1D4ED8;
            color: #FFFFFF;
            transform: translateY(-1px);
        }
        .summary-card {
            border: 1px solid #E5E7EB;
            border-left: 4px solid #2563EB;
            padding: 1rem 1.1rem;
            border-radius: 16px;
            background: #FFFFFF;
            color: #111827;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            white-space: pre-wrap;
        }
        [data-testid="stFileUploader"], [data-testid="stDownloadButton"], .stDownloadButton > button {
            background: #FFFFFF !important;
            border: 1px solid #D1D5DB !important;
            color: #111827 !important;
        }
        .stAlert {
            background: #F9FAFB !important;
            border: 1px solid #E5E7EB !important;
            color: #111827 !important;
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

    st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
    logo_col_1, logo_col_2, logo_col_3 = st.columns([1, 2, 1])
    with logo_col_2:
        if logo_path is not None:
            st.image(str(logo_path), width=280)
        else:
            st.title("Sparce AI")
        st.caption("Handwritten Notes & Document Intelligence")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("Upload a handwritten note, scan, or PDF and turn it into a clean summary.")

    uploaded_file = st.file_uploader(
        "",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Drag and drop or browse device (Accepted formats: PNG, JPEG, PDF)",
    )

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

    use_custom_prompt = st.checkbox("Enable Prompt", value=False)
    custom_question = ""
    if use_custom_prompt:
        custom_question = st.text_input(
            "Ask a specific question about the document",
            placeholder="e.g. What are the key takeaways?",
        )

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
                    )
                st.session_state["summary"] = summary
            except Exception as exc:  # pragma: no cover - UI-level fallback
                st.session_state["summary"] = f"Processing failed: {exc}"
            finally:
                Path(temp_path).unlink(missing_ok=True)

    if "summary" in st.session_state and st.session_state["summary"]:
        st.markdown(
            f"<div class='summary-card'>{st.session_state['summary'].replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
