"""
ME/CFS Database Manager - Gradio Web UI

Main application entry point for the Gradio-based web interface.
"""

import gradio as gr
import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import data.mongo_setup as mongo_setup
import set_up_globals
import infrastructure.state as state
import services.data_service as svc

from src.mecfs_ui.components.auth import create_auth_component, handle_login, get_user_choices
from src.mecfs_ui.components.import_tabs import create_import_tabs
from src.mecfs_ui.components.export_tabs import create_export_tabs
from src.mecfs_ui.components.query_tabs import create_query_tabs


def build_app() -> gr.Blocks:
    """Build and return the Gradio application."""

    # Initialize MongoDB connection
    mongo_setup.global_init(set_up_globals.database_name)

    with gr.Blocks(
        title="ME/CFS Database Manager",
        theme=gr.themes.Soft(),
        css="""
        .success-msg { color: #22c55e; font-weight: bold; }
        .error-msg { color: #ef4444; font-weight: bold; }
        .warning-msg { color: #f59e0b; font-weight: bold; }
        .gradio-container { max-width: 1200px; margin: auto; }
        """
    ) as app:

        # Header
        gr.Markdown("# ME/CFS Database Manager")
        gr.Markdown(
            f"**Version:** {set_up_globals.MECFSVersion} | "
            f"**Database:** {set_up_globals.database_name}"
        )

        # State for current user
        current_user = gr.State(value=None)

        # Authentication Section
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### User Login")
                user_dropdown = gr.Dropdown(
                    choices=get_user_choices(),
                    label="Select User",
                    info="Choose your user account to continue"
                )
                login_btn = gr.Button("Login", variant="primary")
                auth_status = gr.HTML(value="")

        # Main functionality tabs (hidden until logged in)
        with gr.Tabs(visible=False) as main_tabs:

            # Import Tab
            with gr.TabItem("Import Data", id="import"):
                create_import_tabs(current_user)

            # Export Tab
            with gr.TabItem("Export Data", id="export"):
                create_export_tabs(current_user)

            # Query Tab
            with gr.TabItem("View Data", id="query"):
                create_query_tabs(current_user)

        # Login handler
        login_btn.click(
            fn=handle_login,
            inputs=[user_dropdown],
            outputs=[current_user, auth_status, main_tabs]
        )

        # Footer
        gr.Markdown("---")
        gr.Markdown(
            "*ME/CFS Database Manager - Genomics Innovation Hub, Cornell University*"
        )

    return app


def main():
    """Main entry point for the application."""
    app = build_app()

    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", "7861"))

    print(f"\n{'='*60}")
    print(f"ME/CFS Database Manager - Gradio Web UI")
    print(f"{'='*60}")
    print(f"Version: {set_up_globals.MECFSVersion}")
    print(f"Database: {set_up_globals.database_name}")
    print(f"Starting server on port {port}...")
    print(f"{'='*60}\n")

    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False
    )


if __name__ == "__main__":
    main()
