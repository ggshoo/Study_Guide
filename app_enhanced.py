import streamlit as st
import os
import tempfile
import PyPDF2
from pathlib import Path
from ai_study_assistant import AIStudyAssistant
import uuid

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []

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
        st.write(f"**Session ID:** `{st.session_state.user_id}`")
        
    if tool == "Ask Questions":
        st.header("Ask Questions About Course Content")
        query = st.text_input("Enter your question:")
        
        if query:
            with st.spinner("Searching and generating response..."):
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
                quiz = assistant.generate_quiz(topic)
                st.markdown(quiz)
                
    elif tool == "Create Study Guide":
        st.header("Create Focused Study Guide")
        topic = st.text_input("Enter the topic for the study guide:")
        
        if topic:
            with st.spinner("Creating study guide..."):
                guide = assistant.create_study_guide(topic)
                st.markdown(guide)
                
    elif tool == "Concept Map":
        st.header("Generate Concept Map")
        topic = st.text_input("Enter the topic to map:")
        
        if topic:
            with st.spinner("Generating concept map..."):
                concept_map = assistant.concept_map(topic)
                st.code(concept_map)

if __name__ == "__main__":
    main()