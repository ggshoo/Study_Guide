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
import time

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

def process_uploaded_pptx(uploaded_file, assistant):
    """Process an uploaded PowerPoint file and add to vector database."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Process with assistant, preserving original filename
        assistant.process_pptx(tmp_path, original_filename=uploaded_file.name)
        
        # Cleanup
        os.unlink(tmp_path)
        
        return True
    except Exception as e:
        st.error(f"Error processing PowerPoint: {str(e)}")
        return False

def format_slide_recommendations(question_slides_map):
    """Format slide recommendations grouped by question."""
    output = "### 📊 Questions & Slides to Review\n\n"
    
    for q_num, slides_by_file in question_slides_map.items():
        output += f"**Question {q_num}:**\n"
        for filename, slides in slides_by_file.items():
            slide_numbers = [slide['slide_number'] for slide in slides]
            output += f"  - **{filename}**: Slides {', '.join(map(str, slide_numbers))}\n"
        output += "\n"
    
    return output

def main():
    st.title("🎯 Practice Test Analyzer")
    st.write("""Upload your class materials (PowerPoint slides and PDF notes) and practice tests. 
    Mark which questions you got wrong, and the app will identify the exact slides you need to review!""")

    # Auth first
    if not auth_gate():
        st.stop()

    # API key requirement for model features
    api_ready = ensure_api_key()

    assistant = get_assistant(st.session_state.user_id)
    
    # Sidebar for file management
    with st.sidebar:
        st.header("📚 Upload Class Materials")
        
        # PowerPoint upload section
        with st.expander("Upload PowerPoint Slides", expanded=False):
            pptx_files = st.file_uploader(
                "Upload lecture slides (.pptx)",
                type=['pptx'],
                accept_multiple_files=True,
                help="Upload your class PowerPoint slides",
                key="pptx_uploader"
            )
            
            if pptx_files:
                if st.button("Process PowerPoint Files"):
                    progress_bar = st.progress(0)
                    for i, file in enumerate(pptx_files):
                        st.write(f"Processing {file.name}...")
                        if process_uploaded_pptx(file, assistant):
                            if 'pptx' not in st.session_state.processed_files:
                                st.session_state.processed_files.append(file.name)
                            st.success(f"✓ {file.name}")
                        progress_bar.progress((i + 1) / len(pptx_files))
                    st.success("All PowerPoint files processed!")
        
        # PDF upload section
        with st.expander("Upload PDF Notes", expanded=False):
            pdf_files = st.file_uploader(
                "Upload PDF files (notes, textbooks, etc.)",
                type=['pdf'],
                accept_multiple_files=True,
                help="Upload PDF class materials",
                key="pdf_uploader"
            )
            
            if pdf_files:
                if st.button("Process PDF Files"):
                    progress_bar = st.progress(0)
                    for i, file in enumerate(pdf_files):
                        st.write(f"Processing {file.name}...")
                        if process_uploaded_pdf(file, assistant):
                            st.session_state.processed_files.append(file.name)
                            st.success(f"✓ {file.name}")
                        progress_bar.progress((i + 1) / len(pdf_files))
                    st.success("All PDF files processed!")
        
        # Show processed files
        if st.session_state.processed_files:
            st.markdown("---")
            st.write("**📁 Processed Materials:**")
            for filename in st.session_state.processed_files:
                st.write(f"- {filename}")
        
        st.markdown("---")
        # User info and logout
        if st.session_state.current_username:
            st.write(f"**User:** {st.session_state.current_username}")
        st.write(f"**Session ID:** `{st.session_state.user_id}`")
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.current_username = None
            st.rerun()
    
    # Main content area - Practice Test Analyzer
    st.header("📝 Analyze Your Practice Test")
    st.write("""Upload your practice test and enter the question numbers you got wrong. 
    The app will match them to specific slides from your uploaded materials.""")
    
    # Upload practice test
    practice_test = st.file_uploader(
        "Upload Practice Test (PDF)",
        type=['pdf'],
        key="practice_test"
    )
    
    # Input for wrong questions
    flagged_input = st.text_input(
        "Question numbers you got wrong (comma-separated, e.g., 1,3,5,7)",
        help="Enter the question numbers you got wrong or want to focus on"
    )
    
    # Fast mode toggle
    fast_mode = st.checkbox("⚡ Fast Mode (less detailed but quicker)", value=False)
    
    if practice_test and flagged_input and st.button("🔍 Analyze Test & Find Slides to Review"):
        if not api_ready:
            st.error("Please provide an API key to enable analysis.")
        else:
            # Parse flagged questions
            flagged_questions = None
            if flagged_input.strip():
                try:
                    flagged_questions = [int(q.strip()) for q in flagged_input.split(',')]
                    st.info(f"Analyzing questions: {', '.join(map(str, flagged_questions))}")
                except:
                    st.error("Could not parse question numbers. Please use format: 1,3,5,7")
                    st.stop()
            
            # Save practice test temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(practice_test.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Progress tracking
                start_time = time.time()
                progress_placeholder = st.empty()
                timer_placeholder = st.empty()
                
                with st.spinner("Analyzing your practice test and matching to slides..."):
                    # Generate targeted study guide with fast mode
                    result = assistant.create_targeted_study_guide(
                        tmp_path, 
                        flagged_questions,
                        fast_mode=fast_mode
                    )
                
                elapsed = time.time() - start_time
                
                # Display results
                st.success(f"✅ Analysis complete in {elapsed:.1f} seconds!")
                
                # Show question-to-slide mapping
                if 'question_slides_map' in result:
                    st.markdown(format_slide_recommendations(result['question_slides_map']))
                    
                    # Show detailed slide content by question
                    with st.expander("📋 View Detailed Slide Content by Question"):
                        for q_num, slides_by_file in result['question_slides_map'].items():
                            st.subheader(f"Question {q_num}")
                            for filename, slides in slides_by_file.items():
                                st.markdown(f"**{filename}**")
                                for slide in slides:
                                    st.markdown(f"**Slide {slide['slide_number']}:**")
                                    st.text(slide['content'][:400] + "..." if len(slide['content']) > 400 else slide['content'])
                                    st.markdown("---")
                
                # Show test analysis
                with st.expander("🔍 Detailed Test Analysis"):
                    st.markdown(result.get('test_analysis', 'No analysis available'))
                
                # Show study guide
                st.markdown("---")
                st.header("📖 Your Personalized Study Guide")
                st.markdown(result.get('study_guide', 'No study guide generated'))
                
                # Cleanup
                os.unlink(tmp_path)
                
            except Exception as e:
                st.error(f"Error analyzing test: {str(e)}")
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

if __name__ == "__main__":
    main()