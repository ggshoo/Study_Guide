import streamlit as st
import os
import tempfile
import PyPDF2
from pathlib import Path
from ai_study_assistant_new import AIStudyAssistant
import uuid
import hashlib
import openai
import json

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []

############################
# Authentication & API Key #
############################

# User database file
USERS_FILE = "users.json"

def load_users():
    """Load users from JSON file."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def create_user(username: str, password: str) -> tuple[bool, str]:
    """Create a new user account.
    Returns (success: bool, message: str)"""
    if not username or not password:
        return False, "Username and password cannot be empty."
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    
    users = load_users()
    
    if username in users:
        return False, "Username already exists."
    
    # Hash the password
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    users[username] = {
        "password_hash": pwd_hash,
        "created_at": str(uuid.uuid4())  # Use as timestamp placeholder
    }
    
    save_users(users)
    return True, "Account created successfully!"

def verify_credentials(username: str, password: str) -> bool:
    """Verify username/password against stored users.
    Returns True if credentials match; False otherwise."""
    users = load_users()
    
    if username not in users:
        return False
    
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    return users[username]["password_hash"] == pwd_hash

def auth_gate():
    """Sidebar authentication gate. Sets st.session_state.authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "current_username" not in st.session_state:
        st.session_state.current_username = None

    if st.session_state.authenticated:
        return True

    with st.sidebar.expander("🔐 Authentication", expanded=True):
        auth_mode = st.radio("Select mode:", ["Login", "Create Account"])
        
        username = st.text_input("Username", key="auth_username")
        password = st.text_input("Password", type="password", key="auth_password")
        
        if auth_mode == "Login":
            if st.button("Login"):
                if verify_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.current_username = username
                    # Use username as user_id for persistent storage
                    st.session_state.user_id = hashlib.sha256(username.encode()).hexdigest()[:8]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        else:  # Create Account
            if st.button("Create Account"):
                success, message = create_user(username, password)
                if success:
                    st.success(message)
                    st.info("You can now login with your new account.")
                else:
                    st.error(message)
    
    return False

def ensure_api_key():
    """Allow user to input API key; fallback to environment variable.
    Returns True if an API key is set, else False."""
    if "api_key" not in st.session_state:
        st.session_state.api_key = None

    with st.sidebar.expander("🔑 OpenAI API Key", expanded=False):
        entered = st.text_input("Enter API key", type="password", placeholder="sk-...")
        if entered:
            st.session_state.api_key = entered.strip()
        # Feedback
        if st.session_state.api_key:
            st.success("API key set for this session.")
        elif os.getenv("OPENAI_API_KEY"):
            st.info("Using server environment OPENAI_API_KEY.")
        else:
            st.warning("No API key provided yet; AI features disabled.")

    final_key = st.session_state.api_key or os.getenv("OPENAI_API_KEY")
    if not final_key:
        return False
    openai.api_key = final_key
    return True

# Initialize the AI Study Assistant with user-specific collection
@st.cache_resource
def get_assistant(user_id):
    return AIStudyAssistant(persist_directory=f"db_{user_id}")

def process_uploaded_pdf(uploaded_file, assistant):
    """Process an uploaded PDF file and add to vector database."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Extract text from PDF
        with open(tmp_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = ""
            for page_num, page in enumerate(pdf_reader.pages):
                text_content += f"\n\nPage {page_num + 1}\n{'-'*20}\n"
                text_content += page.extract_text()
        
        # Save to temporary text file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as txt_file:
            txt_file.write(f"Content from {uploaded_file.name}\n{'='*50}\n\n")
            txt_file.write(text_content)
            txt_path = txt_file.name
        
        # Process with assistant
        assistant.process_transcription(txt_path)
        
        # Cleanup
        os.unlink(tmp_path)
        os.unlink(txt_path)
        
        return True
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return False

def main():
    st.title("AI Study Assistant 🎓")
    st.write("""Upload your own PDFs or use pre-loaded content to study more effectively.
    Ask questions, generate quizzes, create study guides, and visualize concept relationships!""")

    # Auth first
    if not auth_gate():
        st.stop()

    # API key requirement for model features
    api_ready = ensure_api_key()

    assistant = get_assistant(st.session_state.user_id)
    
    # Sidebar for file management and tools
    with st.sidebar:
        st.header("📚 Manage Content")
        
        # File upload section
        with st.expander("Upload PDFs", expanded=False):
            uploaded_files = st.file_uploader(
                "Upload your PDF files",
                type=['pdf'],
                accept_multiple_files=True,
                help="Upload lecture notes, textbooks, or any study material"
            )
            
            if uploaded_files:
                if st.button("Process Uploaded Files"):
                    progress_bar = st.progress(0)
                    for i, file in enumerate(uploaded_files):
                        st.write(f"Processing {file.name}...")
                        if process_uploaded_pdf(file, assistant):
                            st.session_state.processed_files.append(file.name)
                            st.success(f"✓ {file.name}")
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    st.success("All files processed!")
        
        # Show processed files
        if st.session_state.processed_files:
            st.write("**Processed Files:**")
            for filename in st.session_state.processed_files:
                st.write(f"- {filename}")
        
        st.markdown("---")
        st.header("🛠️ Study Tools")
        tool = st.radio(
            "Choose a tool:",
            ["Ask Questions", "Generate Quiz", "Create Study Guide", "Concept Map"]
        )
        
        st.markdown("---")
        # User info and logout
        if st.session_state.current_username:
            st.write(f"**User:** {st.session_state.current_username}")
        st.write(f"**Session ID:** `{st.session_state.user_id}`")
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.current_username = None
            st.rerun()
        
    if tool == "Ask Questions":
        st.header("Ask Questions About Course Content")
        query = st.text_input("Enter your question:")
        
        if query:
            with st.spinner("Searching and generating response..."):
                if not api_ready:
                    st.error("Provide an API key to enable AI responses.")
                else:
                    result = assistant.query_knowledge_base(query)
                    st.write("### Answer:")
                    st.write(result['answer'])
                    with st.expander("View source content"):
                        for chunk, metadata in zip(result['source_chunks'], result['metadata']):
                            st.text(f"Source: {metadata['source']}")
                            st.text(f"Chunk {metadata['chunk_id']}:")
                            st.text(chunk)
                            st.markdown("---")
                
    elif tool == "Generate Quiz":
        st.header("Generate Practice Quiz")
        topic = st.text_input("Enter the topic for the quiz:")
        
        if topic:
            with st.spinner("Generating quiz..."):
                if not api_ready:
                    st.error("Provide an API key to enable quiz generation.")
                else:
                    quiz = assistant.generate_quiz(topic)
                    st.markdown(quiz)
                
    elif tool == "Create Study Guide":
        st.header("Create Focused Study Guide")
        topic = st.text_input("Enter the topic for the study guide:")
        
        if topic:
            with st.spinner("Creating study guide..."):
                if not api_ready:
                    st.error("Provide an API key to enable study guide creation.")
                else:
                    guide = assistant.create_study_guide(topic)
                    st.markdown(guide)
                
    elif tool == "Concept Map":
        st.header("Generate Concept Map")
        topic = st.text_input("Enter the topic to map:")
        
        if topic:
            with st.spinner("Generating concept map..."):
                if not api_ready:
                    st.error("Provide an API key to enable concept map generation.")
                else:
                    concept_map = assistant.concept_map(topic)
                    st.code(concept_map)

if __name__ == "__main__":
    main()