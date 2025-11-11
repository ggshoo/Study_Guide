import streamlit as st
import os
import tempfile
import PyPDF2
from pathlib import Path
from ai_study_assistant_new import AIStudyAssistant
import uuid
import json
from datetime import datetime
import threading
import time

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'processed_slides' not in st.session_state:
    st.session_state.processed_slides = {}

# Initialize the AI Study Assistant with user-specific collection
@st.cache_resource
def get_assistant(user_id):
    return AIStudyAssistant(persist_directory=f"db_{user_id}")

def process_uploaded_pdf(uploaded_file, assistant):
    """Process an uploaded PDF file and add to vector database; preserve original filename in metadata."""
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
        # Process with assistant, including original upload name
        assistant.process_transcription(txt_path, original_filename=uploaded_file.name)
        # Cleanup
        os.unlink(tmp_path)
        os.unlink(txt_path)
        return True
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return False

def process_uploaded_pptx(uploaded_file, assistant):
    """Process an uploaded PowerPoint file and add to vector database, preserving original filename."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        assistant.process_pptx(tmp_path, original_filename=uploaded_file.name)
        os.unlink(tmp_path)
        return True
    except Exception as e:
        st.error(f"Error processing PowerPoint: {str(e)}")
        return False

def format_slide_recommendations(slides_by_file):
    """Format slide recommendations for display."""
    output = "### 📊 Slides to Review\n\n"
    
    for filename, slides in slides_by_file.items():
        output += f"**{filename}**\n"
        slide_numbers = [slide['slide_number'] for slide in slides]
        output += f"- Slides: {', '.join(map(str, slide_numbers))}\n\n"
    
    return output

def main():
    st.title("AI Study Assistant 🎓")
    st.write("""Upload PowerPoint slides and practice tests to get personalized study recommendations!""")
    
    assistant = get_assistant(st.session_state.user_id)
    
    # Sidebar for file management and tools
    with st.sidebar:
        st.header("📚 Manage Content")
        # Saved analyses
        with st.expander("💾 Saved Analyses", expanded=False):
            save_dir = Path("saved_results")
            save_dir.mkdir(parents=True, exist_ok=True)
            files = sorted(save_dir.glob("*.json"), reverse=True)
            if files:
                sel = st.selectbox("Load a previous analysis", [f.name for f in files])
                if st.button("Load Selected"):
                    try:
                        data = json.loads(Path(save_dir/sel).read_text(encoding="utf-8"))
                        st.session_state["pta_result"] = data.get("result")
                        st.session_state["pta_test_name"] = data.get("test_name", sel)
                        st.success("Loaded saved analysis.")
                    except Exception as e:
                        st.error(f"Failed to load: {e}")
            else:
                st.caption("No saved analyses yet.")
        
        # PowerPoint upload section
        with st.expander("Upload PowerPoint Slides", expanded=False):
            pptx_files = st.file_uploader(
                "Upload your lecture slides (.pptx)",
                type=['pptx'],
                accept_multiple_files=True,
                help="Upload PowerPoint lecture slides",
                key="pptx_uploader"
            )
            
            if pptx_files:
                if st.button("Process PowerPoint Files"):
                    progress_bar = st.progress(0)
                    for i, file in enumerate(pptx_files):
                        st.write(f"Processing {file.name}...")
                        if process_uploaded_pptx(file, assistant):
                            if 'pptx' not in st.session_state.processed_slides:
                                st.session_state.processed_slides['pptx'] = []
                            st.session_state.processed_slides['pptx'].append(file.name)
                            st.success(f"✓ {file.name}")
                        progress_bar.progress((i + 1) / len(pptx_files))
                    st.success("All PowerPoint files processed!")
        
        # PDF upload section
        with st.expander("Upload Other PDFs", expanded=False):
            pdf_files = st.file_uploader(
                "Upload PDF files (notes, textbooks, etc.)",
                type=['pdf'],
                accept_multiple_files=True,
                help="Upload additional study materials",
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
        if st.session_state.processed_slides.get('pptx'):
            st.write("**📊 Processed Slides:**")
            for filename in st.session_state.processed_slides['pptx']:
                st.write(f"- {filename}")
        
        if st.session_state.processed_files:
            st.write("**📄 Processed PDFs:**")
            for filename in st.session_state.processed_files:
                st.write(f"- {filename}")
        
        st.markdown("---")
        st.header("🛠️ Study Tools")
        tool = st.radio(
            "Choose a tool:",
            [
                "🎯 Practice Test Analyzer",
                "❓ Ask Questions",
                "📝 Generate Quiz",
                "📚 Create Study Guide",
                "🗺️ Concept Map"
            ]
        )
        
        st.markdown("---")
        st.write(f"**Session ID:** `{st.session_state.user_id}`")
    
    # Main content area
    if tool == "🎯 Practice Test Analyzer":
        st.header("🎯 Practice Test Analyzer")
        st.write("""Upload your practice test (PDF or PowerPoint) and specify which questions you got wrong or want to review. 
        The app will analyze the test, find relevant slides, and create a personalized study guide.""")
        
        # Upload practice test
        practice_test = st.file_uploader(
            "Upload Practice Test (PDF or PPTX)",
            type=['pdf', 'pptx'],
            key="practice_test"
        )
        
        # Input for flagged questions
        flagged_input = st.text_input(
            "Question numbers to review (comma-separated, e.g., 1,3,5,7)",
            help="Enter the question numbers you got wrong or want to focus on"
        )
        
        if practice_test and st.button("Analyze Test & Generate Study Guide"):
            # Parse flagged questions
            flagged_questions = None
            if flagged_input.strip():
                try:
                    flagged_questions = [int(q.strip()) for q in flagged_input.split(',')]
                except:
                    st.warning("Could not parse question numbers. Analyzing all questions.")
            
            # Save practice test temporarily with matching extension
            ext = os.path.splitext(practice_test.name)[1].lower()
            if ext not in [".pdf", ".pptx"]:
                st.error("Unsupported file type. Please upload a PDF or PPTX.")
                return
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(practice_test.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Estimate time before starting
                est_seconds = 20.0
                if ext == ".pdf":
                    try:
                        pages = len(PyPDF2.PdfReader(tmp_path).pages)
                        est_seconds = 20.0 + pages * 0.5
                    except Exception:
                        pass
                elif ext == ".pptx":
                    try:
                        # Lazy import to avoid dependency error if not installed
                        from pptx import Presentation  # type: ignore
                        slides = len(Presentation(tmp_path).slides)
                        est_seconds = 20.0 + slides * 0.2
                    except Exception:
                        pass

                eta_minutes = max(1, int(round(est_seconds / 60.0)))
                st.info(f"Estimated time: ~{eta_minutes} minute(s). You can switch tabs and come back.")

                # Run analysis in a background thread, show live elapsed timer
                result_holder = {"result": None, "error": None}
                def _run():
                    try:
                        result_holder["result"] = assistant.create_targeted_study_guide(tmp_path, flagged_questions)
                    except Exception as e:
                        result_holder["error"] = str(e)

                t0 = time.perf_counter()
                th = threading.Thread(target=_run, daemon=True)
                th.start()

                timer_placeholder = st.empty()
                status_placeholder = st.empty()
                while th.is_alive():
                    elapsed = time.perf_counter() - t0
                    mm = int(elapsed // 60)
                    ss = int(elapsed % 60)
                    timer_placeholder.info(f"Elapsed: {mm:02d}:{ss:02d}")
                    time.sleep(0.5)
                th.join()

                total = time.perf_counter() - t0
                mm = int(total // 60)
                ss = int(total % 60)

                if result_holder["error"]:
                    raise RuntimeError(result_holder["error"]) 

                result = result_holder["result"]
                status_placeholder.success(f"✅ Analysis complete in {mm}m {ss}s")

                # Persist result in session so it survives navigation
                st.session_state["pta_result"] = result
                st.session_state["pta_test_name"] = practice_test.name
                # Save to disk for persistence across restarts
                try:
                    save_dir = Path("saved_results")
                    save_dir.mkdir(parents=True, exist_ok=True)
                    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    sid = st.session_state.user_id
                    out = {
                        "test_name": practice_test.name,
                        "timestamp": stamp,
                        "session_id": sid,
                        "duration_seconds": int(total),
                        "estimate_minutes": eta_minutes,
                        "result": result,
                    }
                    out_path = save_dir / f"pta_{stamp}_{sid}.json"
                    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as e:
                    st.warning(f"Could not save analysis: {e}")
                
                # Display results
                st.success("✅ Analysis complete!")
                
                # Show slide recommendations
                st.markdown(format_slide_recommendations(result['slides_to_review']))
                
                # Show detailed slide content
                with st.expander("📋 View Slide Details"):
                    for filename, slides in result['slides_to_review'].items():
                        st.subheader(filename)
                        for slide in slides:
                            st.markdown(f"**Slide {slide['slide_number']}:**")
                            st.text(slide['content'][:300] + "...")
                            st.markdown("---")
                
                # Show test analysis
                with st.expander("🔍 Test Analysis"):
                    st.markdown(result['test_analysis'])
                
                # Show study guide
                st.markdown("---")
                st.header("📖 Your Personalized Study Guide")
                st.markdown(result['study_guide'])
                
                # Cleanup
                os.unlink(tmp_path)
                
            except Exception as e:
                st.error(f"Error analyzing test: {str(e)}")
                os.unlink(tmp_path)

        # If there is a previous analysis saved in session, offer to show it
        if not practice_test and st.session_state.get("pta_result"):
            st.info(f"Showing last analysis for: {st.session_state.get('pta_test_name','(unknown)')}")
            result = st.session_state["pta_result"]
            st.markdown(format_slide_recommendations(result['slides_to_review']))
            with st.expander("📋 View Slide Details"):
                for filename, slides in result['slides_to_review'].items():
                    st.subheader(filename)
                    for slide in slides:
                        st.markdown(f"**Slide {slide['slide_number']}:**")
                        st.text(slide['content'][:300] + "...")
                        st.markdown("---")
            with st.expander("🔍 Test Analysis"):
                st.markdown(result['test_analysis'])
            st.markdown("---")
            st.header("📖 Your Personalized Study Guide")
            st.markdown(result['study_guide'])

            # Download buttons
            st.download_button(
                label="Download Study Guide (Markdown)",
                data=result['study_guide'],
                file_name="study_guide.md",
                mime="text/markdown",
            )
        
    elif tool == "❓ Ask Questions":
        st.header("Ask Questions About Course Content")
        query = st.text_input("Enter your question:")
        
        if query:
            with st.spinner("Searching and generating response..."):
                result = assistant.query_knowledge_base(query)
                
                st.write("### Answer:")
                st.write(result['answer'])
                
                with st.expander("View source content"):
                    for chunk, metadata in zip(result['source_chunks'], result['metadata']):
                        display_name = metadata.get('filename') or Path(metadata.get('source','Unknown')).name
                        st.text(f"Source: {display_name}")
                        if 'slide_number' in metadata:
                            st.text(f"Slide {metadata['slide_number']}:")
                        st.text(chunk[:300] + "...")
                        st.markdown("---")
                
    elif tool == "📝 Generate Quiz":
        st.header("Generate Practice Quiz")
        topic = st.text_input("Enter the topic for the quiz:")
        
        if topic:
            with st.spinner("Generating quiz..."):
                quiz = assistant.generate_quiz(topic)
                st.markdown(quiz)
                
    elif tool == "📚 Create Study Guide":
        st.header("Create Focused Study Guide")
        topic = st.text_input("Enter the topic for the study guide:")
        
        if topic:
            with st.spinner("Creating study guide..."):
                guide = assistant.create_study_guide(topic)
                st.markdown(guide)
                
    elif tool == "🗺️ Concept Map":
        st.header("Generate Concept Map")
        topic = st.text_input("Enter the topic to map:")
        
        if topic:
            with st.spinner("Generating concept map..."):
                concept_map = assistant.concept_map(topic)
                st.code(concept_map)

if __name__ == "__main__":
    main()
