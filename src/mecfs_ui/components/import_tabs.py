import gradio as gr
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.mecfs_ui.components.file_handlers import (
    process_clinical_data_file,
    process_biospecimen_file,
    process_assay_file,
    parse_assay_metadata
)


def create_import_tabs(current_user: gr.State):
    """Create import functionality tabs."""

    with gr.Tabs():
        # Clinical Data Import
        with gr.TabItem("Clinical Data"):
            gr.Markdown("### Import Clinical/Demographic Data")
            gr.Markdown("Upload an Excel file containing patient demographic and clinical information.")

            clinical_file = gr.File(
                label="Upload Clinical Data Excel File",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )
            clinical_preview = gr.Dataframe(
                label="Data Preview (first 10 rows)",
                interactive=False,
                visible=False
            )
            clinical_import_btn = gr.Button("Import to Database", variant="primary")
            clinical_status = gr.HTML(value="")
            clinical_log = gr.Textbox(
                label="Import Log",
                lines=10,
                max_lines=20,
                interactive=False,
                visible=False
            )

            def preview_clinical(file_path):
                if not file_path:
                    return gr.update(visible=False), ""
                try:
                    ext = os.path.splitext(file_path)[1].lower()
                    engine = 'xlrd' if ext == '.xls' else 'openpyxl'
                    df = pd.read_excel(file_path, nrows=10, engine=engine)
                    return gr.update(value=df, visible=True), ""
                except Exception as e:
                    return gr.update(visible=False), f"<span class='error-msg'>Error: {e}</span>"

            clinical_file.change(
                fn=preview_clinical,
                inputs=[clinical_file],
                outputs=[clinical_preview, clinical_status]
            )

            def import_clinical(file_path, user):
                if not user:
                    return "<span class='error-msg'>Please login first</span>", gr.update(visible=False)
                if not file_path:
                    return "<span class='error-msg'>Please upload a file</span>", gr.update(visible=False)

                try:
                    result, log = process_clinical_data_file(file_path, user)
                    if result:
                        return (
                            f"<span class='success-msg'>Successfully imported clinical data</span>",
                            gr.update(value=log, visible=True)
                        )
                    return (
                        f"<span class='error-msg'>Import failed</span>",
                        gr.update(value=log, visible=True)
                    )
                except Exception as e:
                    return (
                        f"<span class='error-msg'>Error: {e}</span>",
                        gr.update(visible=False)
                    )

            clinical_import_btn.click(
                fn=import_clinical,
                inputs=[clinical_file, current_user],
                outputs=[clinical_status, clinical_log]
            )

        # Biospecimen Data Import
        with gr.TabItem("Biospecimen Data"):
            gr.Markdown("### Import Biospecimen Data")
            gr.Markdown("Upload an Excel file containing biospecimen storage and tracking information.")

            biospecimen_file = gr.File(
                label="Upload Biospecimen Data Excel File",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )
            biospecimen_preview = gr.Dataframe(
                label="Data Preview (first 10 rows)",
                interactive=False,
                visible=False
            )
            biospecimen_import_btn = gr.Button("Import to Database", variant="primary")
            biospecimen_status = gr.HTML(value="")
            biospecimen_log = gr.Textbox(
                label="Import Log",
                lines=10,
                max_lines=20,
                interactive=False,
                visible=False
            )

            def preview_biospecimen(file_path):
                if not file_path:
                    return gr.update(visible=False), ""
                try:
                    ext = os.path.splitext(file_path)[1].lower()
                    engine = 'xlrd' if ext == '.xls' else 'openpyxl'
                    df = pd.read_excel(file_path, nrows=10, engine=engine)
                    return gr.update(value=df, visible=True), ""
                except Exception as e:
                    return gr.update(visible=False), f"<span class='error-msg'>Error: {e}</span>"

            biospecimen_file.change(
                fn=preview_biospecimen,
                inputs=[biospecimen_file],
                outputs=[biospecimen_preview, biospecimen_status]
            )

            def import_biospecimen(file_path, user):
                if not user:
                    return "<span class='error-msg'>Please login first</span>", gr.update(visible=False)
                if not file_path:
                    return "<span class='error-msg'>Please upload a file</span>", gr.update(visible=False)

                try:
                    result, log = process_biospecimen_file(file_path, user)
                    if result:
                        return (
                            f"<span class='success-msg'>Successfully imported biospecimen data</span>",
                            gr.update(value=log, visible=True)
                        )
                    return (
                        f"<span class='error-msg'>Import failed</span>",
                        gr.update(value=log, visible=True)
                    )
                except Exception as e:
                    return (
                        f"<span class='error-msg'>Error: {e}</span>",
                        gr.update(visible=False)
                    )

            biospecimen_import_btn.click(
                fn=import_biospecimen,
                inputs=[biospecimen_file, current_user],
                outputs=[biospecimen_status, biospecimen_log]
            )

        # Assay Data Import
        with gr.TabItem("Assay Data"):
            gr.Markdown("### Import Assay Data")
            gr.Markdown("Upload an Excel file with 'Metadata' and 'Data Table' sheets.")
            gr.Markdown("Supported assay types: Proteomics, Cytokines, Metabolomics, miRNA-seq, scRNA-seq, Seahorse, etc.")

            assay_file = gr.File(
                label="Upload Assay Data Excel File",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )

            # Metadata display
            with gr.Accordion("Metadata Preview", open=True):
                metadata_display = gr.JSON(label="Parsed Metadata", visible=False)

            assay_preview = gr.Dataframe(
                label="Data Preview (first 10 rows)",
                interactive=False,
                visible=False
            )

            # Confirmation checkbox for assay type
            assay_confirm = gr.Checkbox(
                label="I confirm the metadata above is correct",
                value=False,
                visible=False
            )

            assay_import_btn = gr.Button("Import to Database", variant="primary", interactive=False)
            assay_status = gr.HTML(value="")
            assay_log = gr.Textbox(
                label="Import Log",
                lines=10,
                max_lines=20,
                interactive=False,
                visible=False
            )

            def preview_assay(file_path):
                if not file_path:
                    return (
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(interactive=False),
                        ""
                    )
                try:
                    ext = os.path.splitext(file_path)[1].lower()
                    engine = 'xlrd' if ext == '.xls' else 'openpyxl'

                    # Parse metadata sheet
                    metadata_dict, error = parse_assay_metadata(file_path)
                    if error:
                        return (
                            gr.update(visible=False),
                            gr.update(visible=False),
                            gr.update(visible=False),
                            gr.update(interactive=False),
                            f"<span class='error-msg'>Error parsing metadata: {error}</span>"
                        )

                    # Parse data sheet
                    data_df = pd.read_excel(file_path, sheet_name='Data Table', nrows=10, engine=engine)

                    return (
                        gr.update(value=metadata_dict, visible=True),
                        gr.update(value=data_df, visible=True),
                        gr.update(visible=True, value=False),
                        gr.update(interactive=False),
                        ""
                    )
                except Exception as e:
                    return (
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(interactive=False),
                        f"<span class='error-msg'>Error parsing file: {e}</span>"
                    )

            assay_file.change(
                fn=preview_assay,
                inputs=[assay_file],
                outputs=[metadata_display, assay_preview, assay_confirm, assay_import_btn, assay_status]
            )

            # Enable import button when confirmed
            assay_confirm.change(
                fn=lambda x: gr.update(interactive=x),
                inputs=[assay_confirm],
                outputs=[assay_import_btn]
            )

            def import_assay(file_path, user, confirmed):
                if not user:
                    return "<span class='error-msg'>Please login first</span>", gr.update(visible=False)
                if not file_path:
                    return "<span class='error-msg'>Please upload a file</span>", gr.update(visible=False)
                if not confirmed:
                    return "<span class='error-msg'>Please confirm metadata is correct</span>", gr.update(visible=False)

                try:
                    result, log = process_assay_file(file_path, user)
                    if result:
                        return (
                            f"<span class='success-msg'>Successfully imported assay data</span>",
                            gr.update(value=log, visible=True)
                        )
                    return (
                        f"<span class='error-msg'>Import failed</span>",
                        gr.update(value=log, visible=True)
                    )
                except Exception as e:
                    return (
                        f"<span class='error-msg'>Error: {e}</span>",
                        gr.update(visible=False)
                    )

            assay_import_btn.click(
                fn=import_assay,
                inputs=[assay_file, current_user, assay_confirm],
                outputs=[assay_status, assay_log]
            )

    return {}
