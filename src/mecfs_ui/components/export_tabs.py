import gradio as gr
import pandas as pd
import tempfile
import os
from datetime import datetime
from collections import defaultdict
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import services.data_service as svc
import set_up_globals
import utilities
from src.mecfs_ui.components.file_handlers import modify_df_column_names, parse_assay_metadata


def create_export_tabs(current_user: gr.State):
    """Create export functionality tabs."""

    with gr.Tabs():
        # Binned Summary Export
        with gr.TabItem("Binned Summary"):
            gr.Markdown("### Export Binned Demographic Summary")
            gr.Markdown("Export demographic data with configurable binning for age, BMI, and other fields.")

            with gr.Row():
                with gr.Column():
                    export_format_dropdown = gr.Dropdown(
                        choices=[
                            "Full (with study_id)",
                            "Minimum",
                            "Keller format",
                            "SC Paper format"
                        ],
                        value="Full (with study_id)",
                        label="Export Format"
                    )

            binned_export_btn = gr.Button("Generate Export", variant="primary")
            binned_status = gr.HTML(value="")
            binned_preview = gr.Dataframe(
                label="Export Preview (first 20 rows)",
                interactive=False,
                visible=False
            )
            binned_download = gr.File(
                label="Download TSV File",
                visible=False
            )

            def generate_binned_export(export_format, user):
                if not user:
                    return (
                        "<span class='error-msg'>Please login first</span>",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )

                try:
                    # Select columns based on format
                    if export_format == "Minimum":
                        columns = set_up_globals.exportDemographicColumnsForRTIMinimum
                    elif export_format == "Keller format":
                        columns = set_up_globals.exportDemographicColumnsForRTIKeller
                    elif export_format == "SC Paper format":
                        columns = set_up_globals.exportDemographicColumnsForSCpaper
                    else:
                        columns = set_up_globals.exportDemographicColumnsForRTIFull

                    modified_columns = modify_df_column_names(columns)

                    # Get clinical data from database
                    clinical_data_list = svc.find_clinical_data()

                    if not clinical_data_list:
                        return (
                            "<span class='warning-msg'>No clinical data found in database</span>",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )

                    # Build dataframe
                    data = []
                    for c in clinical_data_list:
                        row_data = {}
                        for col in modified_columns:
                            try:
                                val = getattr(c, col, None)
                                row_data[col] = val
                            except Exception:
                                row_data[col] = None
                        data.append(row_data)

                    df = pd.DataFrame(data)

                    # Apply binning for age and BMI if columns exist
                    for bin_col in ['age', 'bmi']:
                        if bin_col in df.columns:
                            binned_col = f'{bin_col}_binned'
                            if binned_col in modified_columns:
                                bin_ranges = set_up_globals.binnedColumnsDict.get(bin_col, [])
                                df[binned_col] = df[bin_col].apply(
                                    lambda x: get_bin_label(x, bin_ranges) if pd.notna(x) else ''
                                )

                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                    filename = f"binned_demographics_{timestamp}.tsv"

                    # Save to temp file
                    temp_dir = tempfile.gettempdir()
                    filepath = os.path.join(temp_dir, filename)
                    df.to_csv(filepath, sep="\t", index=False)

                    return (
                        f"<span class='success-msg'>Generated {len(df)} records</span>",
                        gr.update(value=df.head(20), visible=True),
                        gr.update(value=filepath, visible=True)
                    )

                except Exception as e:
                    import traceback
                    return (
                        f"<span class='error-msg'>Error: {e}</span>",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )

            binned_export_btn.click(
                fn=generate_binned_export,
                inputs=[export_format_dropdown, current_user],
                outputs=[binned_status, binned_preview, binned_download]
            )

        # RTI Export
        with gr.TabItem("Export for RTI"):
            gr.Markdown("### Export Data for mapMECFS Import")
            gr.Markdown("Upload an assay configuration file to generate RTI-compatible export files.")

            rti_config_file = gr.File(
                label="Upload Assay Configuration Excel File",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )

            with gr.Accordion("Configuration Preview", open=True):
                rti_metadata_display = gr.Markdown(value="*Upload a file to see configuration*", visible=True)

            rti_export_btn = gr.Button("Generate RTI Export", variant="primary")
            rti_status = gr.HTML(value="")

            with gr.Row():
                rti_phenotype_download = gr.File(
                    label="Download Phenotype TSV",
                    visible=False
                )
                rti_assay_download = gr.File(
                    label="Download Assay Data TSV",
                    visible=False
                )

            def preview_rti_config(file_path):
                if not file_path:
                    return gr.update(value="*Upload a file to see configuration*")
                try:
                    metadata_dict, error = parse_assay_metadata(file_path)
                    if error:
                        return gr.update(value=f"**Error:** {error}")

                    # Format metadata as nice markdown
                    md_lines = ["#### Assay Configuration\n"]

                    # Define display order and nice labels
                    field_labels = {
                        'unique_assay_name': 'Assay Name',
                        'assay_type': 'Assay Type',
                        'biospecimen_type': 'Biospecimen Type',
                        'sample_identifier_type': 'Sample Identifier',
                        'normalization': 'Normalization',
                        'data_source': 'Data Source',
                        'platform': 'Platform',
                        'notes': 'Notes'
                    }

                    for key, label in field_labels.items():
                        if key in metadata_dict and metadata_dict[key]:
                            md_lines.append(f"**{label}:** {metadata_dict[key]}  ")

                    # Add any other fields not in the predefined list
                    for key, value in metadata_dict.items():
                        if key not in field_labels and value:
                            nice_key = key.replace('_', ' ').title()
                            md_lines.append(f"**{nice_key}:** {value}  ")

                    return gr.update(value="\n".join(md_lines))
                except Exception as e:
                    return gr.update(value=f"**Error parsing file:** {str(e)}")

            rti_config_file.change(
                fn=preview_rti_config,
                inputs=[rti_config_file],
                outputs=[rti_metadata_display]
            )

            def generate_rti_export(file_path, user):
                if not user:
                    return (
                        "<span class='error-msg'>Please login first</span>",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )
                if not file_path:
                    return (
                        "<span class='error-msg'>Please upload an assay data file</span>",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )

                try:
                    # Parse metadata
                    metadata_dict, error = parse_assay_metadata(file_path)
                    if error:
                        return (
                            f"<span class='error-msg'>Error parsing metadata: {error}</span>",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )

                    unique_assay_name = metadata_dict.get('unique_assay_name', 'unknown')
                    document_name = metadata_dict.get('assay_type', 'unknown')
                    biospecimen_type = metadata_dict.get('biospecimen_type', '')
                    sample_identifier_type = metadata_dict.get('sample_identifier_type', 'ENID+Timepoint')

                    # Read the data table from the Excel file
                    ext = os.path.splitext(file_path)[1].lower()
                    engine = 'xlrd' if ext == '.xls' else 'openpyxl'

                    dataTableDF = pd.read_excel(
                        file_path,
                        sheet_name='Data Table',
                        engine=engine,
                        keep_default_na=False
                    )

                    # Normalize column names
                    dataTableDF.columns = modify_df_column_names(dataTableDF.columns)

                    if 'timepoint' in dataTableDF.columns:
                        dataTableDF['timepoint'] = dataTableDF['timepoint'].astype(str)

                    # Build phenotype DataFrame by looking up clinical data
                    columns = ['phenotype', 'biospecimen_type', 'cor_id', 'timepoint',
                               'sample_identifier_type', 'annot_1', 'annot_2', 'annot_3']
                    phenotype_data = []

                    enid_col = 'enid' if 'enid' in dataTableDF.columns else 'ENID'
                    if enid_col not in dataTableDF.columns:
                        return (
                            "<span class='error-msg'>Could not find ENID column in data</span>",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )

                    for index, row in dataTableDF.iterrows():
                        study_id = row[enid_col]
                        clinical_data = svc.find_clinical_data_by_study_id(int(study_id))
                        if clinical_data:
                            timepoint = row.get('timepoint', '') if 'timepoint' in row else ''
                            phenotype_data.append({
                                'phenotype': clinical_data.phenotype,
                                'biospecimen_type': biospecimen_type,
                                'cor_id': clinical_data.cor_id,
                                'timepoint': timepoint,
                                'sample_identifier_type': sample_identifier_type,
                                'annot_1': '',
                                'annot_2': '',
                                'annot_3': ''
                            })

                    if not phenotype_data:
                        return (
                            "<span class='warning-msg'>No matching clinical data found for study IDs</span>",
                            gr.update(visible=False),
                            gr.update(visible=False)
                        )

                    df = pd.DataFrame(phenotype_data)

                    # Generate phenotype export using service function
                    rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(
                        df,
                        document_name.replace(' ', '_')
                    )

                    # Generate filenames with timestamp
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                    safe_name = unique_assay_name.replace(' ', '_').replace('/', '_')

                    temp_dir = tempfile.gettempdir()

                    phenotype_filename = f"{safe_name}_phenotype_{timestamp}.tsv"
                    phenotype_path = os.path.join(temp_dir, phenotype_filename)
                    rti_phenotype_DF.to_csv(phenotype_path, sep="\t")

                    # Generate assay data export
                    # Identify metadata columns vs data columns
                    # Data columns are everything after the standard metadata columns
                    known_metadata = ['enid', 'timepoint', 'annot_1', 'annot_2', 'annot_3',
                                      'study_id', 'unique_id', 'data_file_name', 'pub_id',
                                      'cor_id', 'sample_identifier_type', 'analysisid']

                    dataLabelList = [col for col in dataTableDF.columns
                                     if col.lower() not in known_metadata]

                    # Prepare dataTableDF for assay export (modify in place like original code)
                    assay_export_df = dataTableDF.copy()
                    assay_export_df['sample_identifier_type'] = sample_identifier_type

                    # Ensure annot columns exist
                    if 'annot_1' not in assay_export_df.columns:
                        assay_export_df['annot_1'] = ''
                    if 'annot_2' not in assay_export_df.columns:
                        assay_export_df['annot_2'] = ''
                    if 'annot_3' not in assay_export_df.columns:
                        assay_export_df['annot_3'] = ''

                    # Add cor_id from clinical data lookup
                    for idx, row in assay_export_df.iterrows():
                        study_id = row[enid_col]
                        clinical_data = svc.find_clinical_data_by_study_id(int(study_id))
                        if clinical_data:
                            assay_export_df.loc[idx, 'cor_id'] = clinical_data.cor_id
                        else:
                            assay_export_df.loc[idx, 'cor_id'] = ''

                    # Check for duplicate sample identifiers and warn/handle
                    if sample_identifier_type == 'ENID+Timepoint':
                        dup_check = assay_export_df.duplicated(subset=['cor_id', 'timepoint'], keep=False)
                    elif sample_identifier_type == 'ENID+Timepoint+Annot-1':
                        dup_check = assay_export_df.duplicated(subset=['cor_id', 'timepoint', 'annot_1'], keep=False)
                    else:
                        dup_check = assay_export_df.duplicated(subset=['cor_id'], keep=False)

                    if dup_check.any():
                        # Remove duplicates, keeping first occurrence
                        if sample_identifier_type == 'ENID+Timepoint':
                            assay_export_df = assay_export_df.drop_duplicates(subset=['cor_id', 'timepoint'], keep='first')
                        elif sample_identifier_type == 'ENID+Timepoint+Annot-1':
                            assay_export_df = assay_export_df.drop_duplicates(subset=['cor_id', 'timepoint', 'annot_1'], keep='first')
                        else:
                            assay_export_df = assay_export_df.drop_duplicates(subset=['cor_id'], keep='first')

                    # Call service function to generate assay data export
                    rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(
                        assay_export_df,
                        document_name,
                        dataLabelList
                    )
                    # Remove last row (often contains column headers after transpose)
                    if len(rtiDF_transposed) > 1:
                        rtiDF_transposed = rtiDF_transposed.iloc[:-1]

                    assay_filename = f"{safe_name}_assay_data_{timestamp}.tsv"
                    assay_path = os.path.join(temp_dir, assay_filename)
                    rtiDF_transposed.to_csv(assay_path, sep="\t", header=False)

                    return (
                        f"<span class='success-msg'>Generated RTI export for {unique_assay_name}: "
                        f"{len(rti_phenotype_DF)} phenotype records, {len(rtiDF_transposed)} assay data columns</span>",
                        gr.update(value=phenotype_path, visible=True),
                        gr.update(value=assay_path, visible=True)
                    )

                except Exception as e:
                    import traceback
                    return (
                        f"<span class='error-msg'>Error: {e}</span>",
                        gr.update(visible=False),
                        gr.update(visible=False)
                    )

            rti_export_btn.click(
                fn=generate_rti_export,
                inputs=[rti_config_file, current_user],
                outputs=[rti_status, rti_phenotype_download, rti_assay_download]
            )

    return {}


def get_bin_label(value, bin_ranges):
    """Get bin label for a value given bin ranges."""
    if pd.isna(value):
        return ''
    try:
        value = float(value)
        for i, (start, end) in enumerate(bin_ranges):
            if start <= value < end:
                return f"{start}-{end}"
        # If value is at the end of last range
        if bin_ranges and value == bin_ranges[-1][1]:
            return f"{bin_ranges[-1][0]}-{bin_ranges[-1][1]}"
    except (ValueError, TypeError):
        pass
    return ''
