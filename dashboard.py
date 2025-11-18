import streamlit as st
import requests
import json 
import uuid 
import streamlit.components.v1 as components

st.set_page_config(page_title="AI Workflow Dashboard", page_icon="🤖", layout="wide")
FASTAPI_URL = "http://127.0.0.1:8000"

# --- Custom CSS & JS for Scrolling ---
st.markdown("""
    <style>
        .main .block-container { padding-bottom: 100px; }
    </style>
""", unsafe_allow_html=True)

def scroll_to_bottom():
    js = """
    <script>
        var body = window.parent.document.querySelector(".main");
        body.scrollTop = body.scrollHeight;
    </script>
    """
    components.html(js, height=0)

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []

# --- SIDEBAR: Document Ingestion ---
with st.sidebar:
    st.header("📂 Document Ingestion")
    st.info("Upload a document to update the knowledge base.")
    
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Ingest Document", type="primary", use_container_width=True):
            with st.spinner("Ingesting..."):
                try:
                    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    res = requests.post(f"{FASTAPI_URL}/upload-document/", files=files)
                    if res.ok: 
                        st.success("Document Ingested! Previous data cleared.")
                    else: 
                        st.error(res.text)
                except Exception as e: 
                    st.error(str(e))

# --- MAIN CHAT INTERFACE ---
st.title("🤖 AI Multi-Agent Workflow")

# Display chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["type"]):
        
        # Check for Email Draft Content
        is_email_draft = False
        email_draft = {}

        if message["type"] == "assistant":
            try:
                potential_draft = json.loads(message["content"])
                if isinstance(potential_draft, dict) and "to" in potential_draft:
                    is_email_draft = True
                    email_draft = potential_draft
            except (json.JSONDecodeError, TypeError):
                pass

        if is_email_draft:
            st.subheader("🤖 AI-Drafted Email")
            with st.form(key=f"email_form_{i}"):
                to_email = st.text_input("To:", email_draft.get("to", ""))
                subject = st.text_input("Subject:", email_draft.get("subject", ""))
                body = st.text_area("Body:", email_draft.get("body", ""), height=250)
                
                if st.form_submit_button("Approve and Send Email", type="primary"):
                    with st.spinner("Sending email..."):
                        try:
                            send_res = requests.post(
                                f"{FASTAPI_URL}/send-email/",
                                json={"to": to_email, "subject": subject, "body": body}
                            )
                            if send_res.ok:
                                st.success(f"Email sent! ID: {send_res.json().get('message_id')}")
                            else:
                                st.error(f"Error: {send_res.text}")
                        except Exception as e:
                            st.error(f"Connection error: {e}")
        else:
            st.markdown(message["content"])

# Chat Input
prompt = st.chat_input("Ask the AI anything...")

if prompt:
    st.session_state.messages.append({"type": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        with st.spinner("🤖 Agents are working..."):
            try:
                response = requests.post(
                    f"{FASTAPI_URL}/chat/", 
                    json={"query": prompt, "session_id": st.session_state.session_id}
                )
                print("Response : ", response.json())
                if response.ok:
                    data = response.json()
                    st.session_state.messages = data.get("chat_history", [])
                    st.rerun()
                else:
                    st.error(f"Error from backend: {response.text}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# Trigger Auto-Scroll
scroll_to_bottom()