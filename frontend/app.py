import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

# Add project root directory to Python's import path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.core.pipeline import process_document as run_pipeline
from backend.core.workforce import (
    build_workforce_period_report,
    generate_summary_excel,
    generate_topo_24h,
    get_available_quarts,
    load_cibles_reference,
    query_gemini_analysis,
)
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
    if suffix == ".xlsx":
        return "xlsx", "Detected Format: Excel Workforce Workbook"

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
        :root {
            color-scheme: light;
            --sparce-ink: #0073A9;
            --sparce-muted: #526763;
            --sparce-accent: #087f6e;
            --sparce-border: #cbd8d5;
            --sparce-surface: #ffffff;
            --sparce-page: #f3f7f6;
        }
        html, body, [class*="stApp"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        }
        .stApp {
            background: var(--sparce-page) !important;
            color: var(--sparce-ink);
        }
        [data-testid="stSidebar"] {
            background: var(--sparce-surface) !important;
            border-right: 1px solid var(--sparce-border);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1100px;
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
            color: var(--sparce-ink) !important;
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
            background: var(--sparce-surface) !important;
            border: 1px solid var(--sparce-border) !important;
            border-radius: 8px !important;
        }
        .stButton button:hover,
        .stButton button:focus,
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stNumberInput > div > div > input:focus,
        .stSelectbox > div > div:focus,
        [data-testid="stFileUploader"]:focus-within,
        .stDownloadButton > button:focus {
            background: var(--sparce-surface) !important;
            border-color: var(--sparce-accent) !important;
            box-shadow: 0 0 0 2px rgba(8, 127, 110, 0.18) !important;
        }
        .stButton button[kind="primary"] {
            background: var(--sparce-accent) !important;
            border-color: var(--sparce-accent) !important;
            color: white !important;
        }
        .stTextArea > div > div > textarea {
            color: #477fa3 !important;
            caret-color: #477fa3;
        }
        .date-range-instructions {
            padding: 0.75rem 0.9rem;
            border-radius: 8px;
            background: var(--sparce-ink);
            color: #ffffff !important;
            margin-bottom: 0.75rem;
        }
        .hero-card {
            border: 1px solid var(--sparce-border);
            border-radius: 8px;
            padding: 1.25rem 1.4rem;
            background: var(--sparce-surface);
            margin-bottom: 1rem;
        }
        .pill {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: var(--sparce-surface);
            color: var(--sparce-ink);
            font-weight: 600;
            margin-top: 0.35rem;
            border: 1px solid var(--sparce-border);
        }
        .summary-card {
            border: 1px solid var(--sparce-border);
            border-left: 4px solid var(--sparce-accent);
            padding: 1rem 1.1rem;
            border-radius: 8px;
            background: var(--sparce-surface);
            color: var(--sparce-ink);
            white-space: pre-wrap;
        }
        [data-testid="stDialog"] [data-testid="stDateInput"] {
            width: 100%;
        }
        @media (max-width: 640px) {
            .block-container {
                padding: 1rem 1rem 2rem;
            }
            [data-testid="stDialog"] [role="dialog"] {
                width: calc(100vw - 1rem);
                max-width: calc(100vw - 1rem);
                margin: 0.5rem;
            }
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


def _render_date_range_dialog() -> None:
    @st.dialog("Sélection de la période", width="small")
    def date_range_dialog() -> None:
        st.markdown(
            "<div class='date-range-instructions'>Choisissez la date de début, puis la date de fin. "
            "La période apparaîtra en surbrillance.</div>",
            unsafe_allow_html=True,
        )
        dates = st.date_input(
            "Période",
            format="DD/MM/YYYY",
            key="pending_report_period",
        )

        if len(dates) != 2:
            st.caption("Sélectionnez les deux dates pour confirmer.")

        cancel_col, confirm_col = st.columns(2)
        with cancel_col:
            if st.button("Annuler", use_container_width=True, key="cancel_report_period"):
                st.session_state["date_picker_open"] = False
                st.rerun(scope="app")
        with confirm_col:
            if st.button(
                "Ok ✅",
                type="primary",
                use_container_width=True,
                disabled=len(dates) != 2,
                key="confirm_report_period",
            ):
                st.session_state["report_period"] = tuple(dates)
                st.session_state["date_picker_open"] = False
                st.rerun(scope="app")

    date_range_dialog()


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
        st.caption("Workforce planning and replacement activity intelligence")

    st.title("Module: Gestion des activités de remplacement")
    st.write("Importez un classeur Excel multi-feuilles pour analyser les besoins et les surplus.")

    if "report_period" not in st.session_state:
        st.session_state["report_period"] = None
    if "date_picker_open" not in st.session_state:
        st.session_state["date_picker_open"] = False

    with st.sidebar:
        st.subheader("Configuration du rapport")
        date_selection = st.session_state["report_period"] or ()
        if date_selection:
            period_label = f"{date_selection[0]:%d/%m/%Y} – {date_selection[1]:%d/%m/%Y}"
        else:
            period_label = "Choisir une période"
        if st.button(f"📅  {period_label}", use_container_width=True, key="open_date_picker"):
            st.session_state["pending_report_period"] = date_selection
            st.session_state["date_picker_open"] = True

        quart_options = ["JOUR", "SOIR", "NUIT"]
        cibles_load_error: Optional[str] = None
        try:
            df_semaine_sidebar, df_fin_semaine_sidebar = load_cibles_reference()
            common_quarts = get_available_quarts(df_semaine_sidebar, df_fin_semaine_sidebar)
            if common_quarts:
                quart_options = common_quarts
            else:
                cibles_load_error = (
                    "Aucun quart commun trouvé entre les tableaux Semaine et Fin de semaine de Cibles.xlsx."
                )
        except (FileNotFoundError, ValueError) as exc:
            cibles_load_error = f"Dictionnaire de cibles indisponible: {exc}"

        if cibles_load_error:
            st.warning(cibles_load_error)

        quart_selection = st.selectbox("Type de quart", quart_options, disabled=bool(cibles_load_error))

    if st.session_state["date_picker_open"]:
        _render_date_range_dialog()

    uploaded_file = st.file_uploader(
        "Importer un document",
        type=["xlsx", "png", "jpg", "jpeg", "pdf"],
        help="Drag and drop or browse device (Accepted formats: XLSX, PNG, JPEG, PDF)",
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
        custom_question = st.text_area(
            "Ask a specific question about the workforce data",
            placeholder="e.g. What are the key takeaways?",
        )

    if st.button("Generate Personalized Workforce Report", type="primary", use_container_width=True, disabled=uploaded_file is None):
        if len(date_selection) != 2:
            st.warning("Veuillez sélectionner une date de début ET une date de fin pour générer le rapport.")
            st.stop()
        start_date, end_date = date_selection
        if uploaded_file is None:
            st.warning("Please upload a document before generating a summary.")
        else:
            suffix = Path(getattr(uploaded_file, "name", "file")).suffix.lower() or ".bin"
            if suffix == ".xlsx":
                try:
                    with st.spinner("Transforming workforce workbook and generating report..."):
                        df_semaine, df_fin_semaine = load_cibles_reference()
                        df_final = build_workforce_period_report(
                            uploaded_file,
                            start_date,
                            end_date,
                            df_semaine,
                            df_fin_semaine,
                            quart_selection,
                        )

                        df_besoins = df_final[df_final["Besoins"] > 0].reset_index(drop=True)
                        df_surplus = df_final[df_final["Surplus"] > 0].reset_index(drop=True)
                        excel_output = generate_summary_excel(df_besoins, df_surplus)
                        data_summary = {
                            "date_debut": str(start_date),
                            "date_fin": str(end_date),
                            "quart": quart_selection,
                            "lignes_analysees": len(df_final),
                            "besoins": df_besoins.to_dict(orient="records"),
                            "surplus": df_surplus.to_dict(orient="records"),
                        }
                        summary = query_gemini_analysis(data_summary, custom_question)
                    st.session_state["summary"] = summary
                    st.session_state["workforce_xlsx"] = excel_output.getvalue()
                    original_name = Path(getattr(uploaded_file, "name", "sparce_workforce")).stem
                    st.session_state["summary_file_name"] = f"{original_name}_report.md"
                    st.session_state["xlsx_file_name"] = f"{original_name}_summary.xlsx"
                    st.session_state.pop("summary_error", None)
                    st.session_state["report_generated"] = True
                    st.session_state["topo_24h_content"] = None
                except FileNotFoundError as exc:
                    st.session_state["summary_error"] = f"Dictionnaire de cibles introuvable: {exc}"
                except (ValueError, KeyError) as exc:
                    st.session_state["summary_error"] = f"Erreur de traitement des données: {exc}"
                except Exception as exc:
                    st.session_state["summary_error"] = f"Processing failed: {exc}"
                uploaded_file = None
            else:
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
                    st.session_state.pop("summary_error", None)
                    original_name = Path(getattr(uploaded_file, "name", "sparce_summary")).stem
                    st.session_state["summary_file_name"] = (
                        f"{original_name}_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    )
                    st.session_state["report_generated"] = True
                    st.session_state["topo_24h_content"] = None
                except Exception as exc:  # pragma: no cover - UI-level fallback
                    st.session_state["summary_error"] = f"Processing failed: {exc}"
                finally:
                    Path(temp_path).unlink(missing_ok=True)

    if "summary_error" in st.session_state and st.session_state["summary_error"]:
        st.error(st.session_state["summary_error"])

    if "summary" in st.session_state and st.session_state["summary"] and not st.session_state.get("summary_error"):
        st.markdown("### Personalized Workforce Report")

        st.markdown(
            f"<div class='summary-card'>{st.session_state['summary'].replace(chr(10), '<br>')}</div>",
            unsafe_allow_html=True,
        )

        st.download_button(
            "Download MD File",
            data=st.session_state["summary"],
            file_name=st.session_state.get("summary_file_name", "sparce_summary.md"),
            mime="text/markdown",
            key="download_summary",
        )
        if st.session_state.get("workforce_xlsx"):
            st.download_button(
                "Download Summary XLSX",
                data=st.session_state["workforce_xlsx"],
                file_name=st.session_state.get("xlsx_file_name", "workforce_summary.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_workforce_xlsx",
            )

        if "topo_24h_content" not in st.session_state:
            st.session_state["topo_24h_content"] = None

        if st.session_state.get("report_generated"):
            if st.session_state["topo_24h_content"] is None:
                try:
                    with st.spinner("Génération du Topo 24h en cours..."):
                        st.session_state["topo_24h_content"] = generate_topo_24h(st.session_state["summary"])
                except Exception as exc:
                    st.session_state["topo_24h_content"] = None
                    st.error(f"Topo 24h generation failed: {exc}")

            if st.session_state.get("topo_24h_content"):
                st.download_button(
                    "Download Topo 24h",
                    data=st.session_state["topo_24h_content"],
                    file_name="Topo_RH_24h_Fleury.md",
                    mime="text/markdown",
                    key="download_topo_24h",
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()
