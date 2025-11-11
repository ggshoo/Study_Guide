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

# Persistent file tracking
USER_FILES_DIR = "user_files"
os.makedirs(USER_FILES_DIR, exist_ok=True)

def get_user_files_path(user_id):
    """Get path to user's persistent file list."""
    return os.path.join(USER_FILES_DIR, f"{user_id}_files.json")

def load_user_files(user_id):
    """Load user's processed files from disk."""
    file_path = get_user_files_path(user_id)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []

def save_user_files(user_id, files):
    """Save user's processed files to disk."""
    file_path = get_user_files_path(user_id)
    with open(file_path, 'w') as f:
        json.dump(files, f, indent=2)

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
def get_assistant(user_id, _version=3):  # Increment version to force cache refresh
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

def format_priority_slides(question_slides_map):
    """Format priority slides grouped by file and slide, showing which questions each slide addresses."""
    # Reorganize data: file -> slide_num -> {questions: [], content: str}
    slide_info = {}
    
    for q_num, slides_by_file in question_slides_map.items():
        for filename, slides in slides_by_file.items():
            if filename not in slide_info:
                slide_info[filename] = {}
            
            for slide in slides:
                slide_num = slide['slide_number']
                if slide_num not in slide_info[filename]:
                    slide_info[filename][slide_num] = {
                        'questions': [],
                        'content': slide.get('content', '')
                    }
                slide_info[filename][slide_num]['questions'].append(q_num)
    
    # Format output
    output = "### 🎯 Priority Slides to Review\n\n"
    
    for filename in sorted(slide_info.keys()):
        output += f"**{filename}**\n"
        sorted_slides = sorted(slide_info[filename].items())
        
        for slide_num, info in sorted_slides:
            questions = sorted(info['questions'])
            q_list = ', '.join(map(str, questions))
            
            # Extract a brief topic from the slide content (first 60 chars or first sentence)
            content = info['content'].strip()
            # Try to get first sentence or first line
            topic = content.split('.')[0] if '.' in content[:100] else content[:60]
            topic = topic.strip().replace('\n', ' ')[:60]
            if len(content) > 60:
                topic += "..."
            
            output += f"  - **Slide {slide_num}**: {topic} *Test Qs: {q_list}*\n"
        
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
    
    # Load user's previously processed files
    if not st.session_state.processed_files:
        st.session_state.processed_files = load_user_files(st.session_state.user_id)
    
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
                            if file.name not in st.session_state.processed_files:
                                st.session_state.processed_files.append(file.name)
                            st.success(f"✓ {file.name}")
                        progress_bar.progress((i + 1) / len(pptx_files))
                    save_user_files(st.session_state.user_id, st.session_state.processed_files)
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
                    save_user_files(st.session_state.user_id, st.session_state.processed_files)
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
    st.write("""Upload your practice test (with your answers marked/written on it). 
    The app will automatically detect which questions you got wrong and match them to specific slides.""")
    
    # Upload practice test
    practice_test = st.file_uploader(
        "Upload Practice Test (PDF)",
        type=['pdf'],
        key="practice_test",
        help="Upload a PDF with your answers already marked/written on it"
    )
    
    # Fast mode toggle
    fast_mode = st.checkbox("⚡ Fast Mode (less detailed but quicker)", value=False)
    
    # Step 1: Extract and analyze test
    if practice_test:
        if st.button("� Analyze Test & Find Slides to Review", type="primary"):
            if not api_ready:
                st.error("Please provide an API key to enable analysis.")
            else:
                # Save practice test temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(practice_test.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    with st.spinner("📖 Extracting questions and answers from test..."):
                        questions_data = assistant.extract_questions_and_answers(tmp_path)
                    
                    questions = questions_data.get('questions', {})
                    correct_answers = questions_data.get('correct_answers', {})
                    user_answers = questions_data.get('user_answers', {})
                    
                    if not questions:
                        st.error("Could not extract questions from the test. Please make sure it's a readable PDF.")
                        os.unlink(tmp_path)
                    else:
                        st.success(f"✅ Extracted {len(questions)} questions from test")
                        
                        # Show what was found
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Questions Found", len(questions))
                        with col2:
                            st.metric("Answer Key Found", len(correct_answers) if correct_answers else "No")
                        with col3:
                            st.metric("Your Answers Found", len(user_answers) if user_answers else "No")
                        
                        # Determine wrong questions
                        wrong_questions = []
                        unanswered_questions = []
                        
                        if correct_answers and user_answers:
                            # Both answer key and user answers found - compare them
                            for q_num_str in questions.keys():
                                if q_num_str in correct_answers and correct_answers[q_num_str]:
                                    if q_num_str in user_answers and user_answers[q_num_str]:
                                        # Compare answers
                                        if user_answers[q_num_str].upper() != correct_answers[q_num_str].upper():
                                            wrong_questions.append(int(q_num_str))
                                    else:
                                        # No user answer found - assume wrong
                                        unanswered_questions.append(int(q_num_str))
                            
                            total = len([q for q in questions.keys() if q in correct_answers and correct_answers[q]])
                            correct_count = total - len(wrong_questions) - len(unanswered_questions)
                            
                            st.markdown("---")
                            st.subheader("📊 Test Results")
                            
                            if wrong_questions or unanswered_questions:
                                score = (correct_count / total * 100) if total > 0 else 0
                                st.info(f"**Score:** {correct_count}/{total} ({score:.1f}%)")
                                
                                if wrong_questions:
                                    st.error(f"**Questions with wrong answers:** {', '.join(map(str, wrong_questions))}")
                                if unanswered_questions:
                                    st.warning(f"**Unanswered/unclear questions (assumed wrong):** {', '.join(map(str, unanswered_questions))}")
                                
                                # Combine wrong and unanswered for analysis
                                questions_to_review = sorted(wrong_questions + unanswered_questions)
                                
                            else:
                                st.success("🎉 Perfect score! You got all questions correct!")
                                st.balloons()
                                questions_to_review = []
                        
                        elif correct_answers and not user_answers:
                            # Only answer key found - assume all questions wrong/need review
                            st.warning("⚠️ Answer key found but no user answers detected. Analyzing all questions.")
                            questions_to_review = [int(q) for q in questions.keys() if q in correct_answers]
                        
                        elif user_answers and not correct_answers:
                            # Only user answers found - can't compare, analyze all
                            st.warning("⚠️ Your answers found but no answer key detected. Analyzing all questions.")
                            questions_to_review = [int(q) for q in questions.keys()]
                        
                        else:
                            # Neither found - analyze everything
                            st.warning("⚠️ Could not detect answers or answer key. Analyzing all questions.")
                            questions_to_review = [int(q) for q in questions.keys()]
                        
                        # Analyze questions
                        if questions_to_review:
                            st.markdown("---")
                            st.subheader("🔍 Finding Relevant Slides...")
                            
                            start_time = time.time()
                            
                            with st.spinner("Matching questions to slides in your class materials..."):
                                result = assistant.create_targeted_study_guide(
                                    tmp_path,
                                    questions_to_review,
                                    fast_mode=fast_mode
                                )
                            
                            elapsed = time.time() - start_time
                            
                            # Display results - SUMMARY FIRST
                            st.success(f"✅ Analysis complete in {elapsed:.1f} seconds!")
                            
                            st.markdown("---")
                            st.header("📖 Your Personalized Study Guide")
                            st.markdown(result.get('study_guide', 'No study guide generated'))
                            
                            st.markdown("---")
                            
                            # Show question-to-slide mapping - DETAILS AFTER
                            if 'question_slides_map' in result:
                                # Show priority slides first (grouped by slide)
                                st.markdown(format_priority_slides(result['question_slides_map']))
                                
                                # Show question-by-question breakdown in expander
                                with st.expander("📋 View by Question (which slides for each question)"):
                                    st.markdown(format_slide_recommendations(result['question_slides_map']))
                                
                                # Show detailed slide content by question
                                with st.expander("� View Detailed Slide Content"):
                                    for q_num, slides_by_file in result['question_slides_map'].items():
                                        st.subheader(f"Question {q_num}")
                                        for filename, slides in slides_by_file.items():
                                            st.markdown(f"**{filename}**")
                                            for slide in slides:
                                                st.markdown(f"**Slide {slide['slide_number']}:**")
                                                st.text(slide['content'][:400] + "..." if len(slide['content']) > 400 else slide['content'])
                                                st.markdown("---")
                            
                            # Show test analysis details at the very bottom
                            with st.expander("🔍 Detailed Test Analysis (Question-by-Question)"):
                                st.markdown(result.get('test_analysis', 'No analysis available'))
                        
                        # Cleanup
                        os.unlink(tmp_path)
                
                except Exception as e:
                    st.error(f"Error analyzing test: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

if __name__ == "__main__":
    main()