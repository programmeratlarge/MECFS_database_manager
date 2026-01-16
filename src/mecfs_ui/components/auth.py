import gradio as gr
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import set_up_globals
import services.data_service as svc


def ensure_users_exist():
    """Ensure all configured users exist in the database."""
    for name, email in set_up_globals.users:
        if not svc.find_account_by_email(email):
            svc.create_account(name, email)


def get_user_choices():
    """Get list of user choices for dropdown."""
    ensure_users_exist()
    users = svc.get_users()
    return [f"{u.name} ({u.email})" for u in users]


def create_auth_component():
    """
    Create the user authentication dropdown and login button.

    Returns:
        Tuple of (user_dropdown, login_btn, auth_status)
    """
    with gr.Group():
        gr.Markdown("### User Login")
        user_dropdown = gr.Dropdown(
            choices=get_user_choices(),
            label="Select User",
            info="Choose your user account to continue"
        )
        login_btn = gr.Button("Login", variant="primary")
        auth_status = gr.HTML(value="")

    return user_dropdown, login_btn, auth_status


def handle_login(selected_user):
    """
    Handle user login.

    Args:
        selected_user: Selected user string in format "Name (email)"

    Returns:
        Tuple of (account, status_html, tabs_visible)
    """
    import infrastructure.state as state

    if not selected_user:
        return None, "<span class='error-msg'>Please select a user</span>", gr.update(visible=False)

    # Parse user selection (format: "Name (email)")
    try:
        email = selected_user.split("(")[-1].rstrip(")")
        account = svc.find_account_by_email(email)

        if account:
            state.active_account = account
            return (
                account,
                f"<span class='success-msg'>Logged in as {account.name}</span>",
                gr.update(visible=True)
            )
    except Exception as e:
        pass

    return None, "<span class='error-msg'>Login failed</span>", gr.update(visible=False)
