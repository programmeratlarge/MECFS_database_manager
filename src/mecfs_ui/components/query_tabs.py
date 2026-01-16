import gradio as gr
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import services.data_service as svc
import set_up_globals


def create_query_tabs(current_user: gr.State):
    """Create query/view functionality tabs."""

    with gr.Tabs():
        # View Clinical Data
        with gr.TabItem("Clinical Data"):
            gr.Markdown("### View Clinical/Demographic Records")
            gr.Markdown("Browse all clinical data records in the database.")

            clinical_refresh_btn = gr.Button("Refresh Data", variant="secondary")
            clinical_count = gr.HTML(value="")
            clinical_table = gr.Dataframe(
                label="Clinical Records",
                interactive=False,
                wrap=True
            )

            def load_clinical_data():
                try:
                    clinical_data_list = svc.find_clinical_data()

                    if not clinical_data_list:
                        return "<span class='warning-msg'>No clinical data found</span>", pd.DataFrame()

                    # Build simplified dataframe for display
                    data = []
                    for c in clinical_data_list:
                        phenotype_label = 'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'
                        data.append({
                            'Study ID': c.study_id,
                            'COR ID': c.cor_id,
                            'Phenotype': phenotype_label,
                            'Sex': c.sex,
                            'Age': c.age,
                            'Site': c.site,
                            'BMI': round(c.bmi, 1) if c.bmi else None,
                            'Duration': c.mecfs_duration if hasattr(c, 'mecfs_duration') else None
                        })

                    df = pd.DataFrame(data)
                    return f"<span class='success-msg'>Found {len(df)} records</span>", df

                except Exception as e:
                    return f"<span class='error-msg'>Error: {e}</span>", pd.DataFrame()

            clinical_refresh_btn.click(
                fn=load_clinical_data,
                inputs=[],
                outputs=[clinical_count, clinical_table]
            )

        # View Biospecimen Data
        with gr.TabItem("Biospecimen Data"):
            gr.Markdown("### View Biospecimen Records by Study ID")
            gr.Markdown("Search for biospecimen records associated with a specific patient.")

            with gr.Row():
                study_id_input = gr.Number(
                    label="Study ID",
                    precision=0,
                    minimum=1
                )
                biospecimen_search_btn = gr.Button("Search", variant="primary")

            biospecimen_status = gr.HTML(value="")
            biospecimen_table = gr.Dataframe(
                label="Biospecimen Records",
                interactive=False,
                visible=False
            )

            def search_biospecimens(study_id):
                if not study_id:
                    return "<span class='error-msg'>Please enter a Study ID</span>", gr.update(visible=False)

                try:
                    study_id = int(study_id)
                    biospecimen_list = svc.find_biospecimen_data_by_study_id(study_id)

                    if not biospecimen_list:
                        return (
                            f"<span class='warning-msg'>No biospecimens found for Study ID {study_id}</span>",
                            gr.update(visible=False)
                        )

                    # Build dataframe
                    data = []
                    for idx, b in enumerate(biospecimen_list):
                        # Check if biospecimen has tube info
                        if hasattr(b, 'biospecimen_tube_info') and b.biospecimen_tube_info:
                            for tube in b.biospecimen_tube_info:
                                date_str = None
                                if hasattr(tube, 'date_received') and tube.date_received:
                                    date_str = tube.date_received.strftime('%Y-%m-%d')
                                data.append({
                                    '#': idx + 1,
                                    'Specimen ID': b.specimen_id,
                                    'CPET Day': b.cpet_day if hasattr(b, 'cpet_day') else None,
                                    'Pre/Post': b.pre_post_cpet if hasattr(b, 'pre_post_cpet') else None,
                                    'Type': b.specimen_type if hasattr(b, 'specimen_type') else None,
                                    'Tube #': tube.tube_number if hasattr(tube, 'tube_number') else None,
                                    'Freezer ID': tube.freezer_id if hasattr(tube, 'freezer_id') else None,
                                    'Date Received': date_str
                                })
                        else:
                            data.append({
                                '#': idx + 1,
                                'Specimen ID': b.specimen_id,
                                'CPET Day': b.cpet_day if hasattr(b, 'cpet_day') else None,
                                'Pre/Post': b.pre_post_cpet if hasattr(b, 'pre_post_cpet') else None,
                                'Type': b.specimen_type if hasattr(b, 'specimen_type') else None,
                                'Tube #': None,
                                'Freezer ID': None,
                                'Date Received': None
                            })

                    df = pd.DataFrame(data)
                    return (
                        f"<span class='success-msg'>Found {len(biospecimen_list)} biospecimens "
                        f"({len(data)} tubes) for Study ID {study_id}</span>",
                        gr.update(value=df, visible=True)
                    )

                except Exception as e:
                    return f"<span class='error-msg'>Error: {e}</span>", gr.update(visible=False)

            biospecimen_search_btn.click(
                fn=search_biospecimens,
                inputs=[study_id_input],
                outputs=[biospecimen_status, biospecimen_table]
            )

        # View Assay Data
        with gr.TabItem("Assay Data"):
            gr.Markdown("### View Available Assay Types")
            gr.Markdown("Browse assay types stored in the database.")

            assay_refresh_btn = gr.Button("Refresh Assay List", variant="secondary")
            assay_status = gr.HTML(value="")
            assay_list = gr.Dataframe(
                label="Available Assays",
                interactive=False,
                visible=False
            )

            def load_assay_types():
                try:
                    unique_assays = svc.find_unique_assay_names()

                    if not unique_assays:
                        return "<span class='warning-msg'>No assay data found</span>", gr.update(visible=False)

                    data = []
                    for idx, assay_name in enumerate(unique_assays):
                        data.append({
                            '#': idx + 1,
                            'Assay Name': assay_name
                        })

                    df = pd.DataFrame(data)
                    return (
                        f"<span class='success-msg'>Found {len(unique_assays)} assay types</span>",
                        gr.update(value=df, visible=True)
                    )

                except Exception as e:
                    return f"<span class='error-msg'>Error: {e}</span>", gr.update(visible=False)

            assay_refresh_btn.click(
                fn=load_assay_types,
                inputs=[],
                outputs=[assay_status, assay_list]
            )

    return {}
