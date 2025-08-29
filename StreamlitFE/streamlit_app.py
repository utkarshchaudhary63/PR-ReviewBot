import streamlit as st
import requests

openai_key = st.secrets["OPENAI_KEY"]

st.set_page_config(page_title="🤖 AI GitHub PR Reviewer", layout="centered")

st.title("🤖 AI GitHub PR Reviewer")

# --- Login Section ---
st.subheader("🔑 GitHub Login")

g_token = st.text_input("Enter GitHub Read-only Classic Token", type="password", help="Generate a token with read-only repo access in GitHub settings.")
repo = st.text_input("Enter Repository (e.g., owner/repo)", help="Format: owner/repository-name")
pr_number = st.number_input("Enter PR Number", min_value=1, step=1)

if st.button("Review PR"):
    if not repo.strip() or not pr_number or not g_token.strip():
        st.error("Please enter the repository, PR number, and your GitHub token.")
    else:
        with st.spinner("Fetching review from AI..."):
            try:
                response = requests.post("https://pr-reviewbot.onrender.com/review", json={
                    "repo": repo.strip(),
                    "git_token": g_token.strip(),
                    "pr_number": pr_number,
                    "openai_key": openai_key
                }, timeout=15)

                if response.status_code == 200:
                    review = response.json().get("review", "No review found.")
                    st.subheader("AI Review Comments:")
                    st.markdown(f"<div style='background-color:#f0f2f6;padding:10px;border-radius:5px;'>{review}</div>", unsafe_allow_html=True)
                else:
                    st.error(f"Failed to fetch review. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                st.error(f"Error while connecting to the backend: {e}")

# Optional footer with instructions or tips
st.markdown(
    """
    ---
    <small>Ensure your token has the necessary permissions to access the repository. This tool only reads your PR data and does not store your token.</small>
    """,
    unsafe_allow_html=True
)
