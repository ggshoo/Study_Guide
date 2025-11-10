# AI Study Assistant - RAG Application

An intelligent study assistant powered by RAG (Retrieval-Augmented Generation) that helps students study more effectively by processing lecture materials and providing interactive study tools.

## Features

🎓 **Smart Question Answering** - Ask questions about your study materials in natural language  
📝 **Quiz Generation** - Create practice quizzes on any topic with varying difficulty  
📚 **Study Guide Creation** - Generate comprehensive study guides with key concepts  
🗺️ **Concept Mapping** - Visualize relationships between ideas  
📄 **PDF Upload** - Process your own PDFs (lecture notes, textbooks, etc.)  
👥 **Multi-User Support** - Each user gets their own isolated database  

## Quick Start

### Local Development

1. **Clone or copy this directory:**
   ```bash
   cd rag_study_assistant
   ```

2. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   Create a `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Run the app:**
   ```bash
   streamlit run app_enhanced.py
   ```

5. **Open your browser:**
   Visit http://localhost:8501

## Deployment

### Streamlit Cloud (Easiest)

1. Push this directory to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and select `app_enhanced.py`
4. Add your `OPENAI_API_KEY` in secrets
5. Deploy!

For detailed deployment instructions (Railway, Render, self-hosted), see [DEPLOYMENT.md](DEPLOYMENT.md)

## Usage

### Upload Your Materials
1. Click "Upload PDFs" in the sidebar
2. Select your PDF files (lecture notes, textbooks, etc.)
3. Click "Process Uploaded Files"
4. Wait for processing to complete

### Study Tools

**Ask Questions**
- Enter any question about your materials
- Get AI-powered answers with source citations

**Generate Quiz**
- Enter a topic
- Receive 3 questions (easy, medium, hard)
- Includes answers and explanations

**Create Study Guide**
- Enter a topic
- Get organized study materials with:
  - Key concepts and definitions
  - Important relationships
  - Common misconceptions
  - Practice problems

**Concept Map**
- Enter a topic
- Visualize how concepts relate to each other

## Architecture

```
┌─────────────┐
│   User UI   │ (Streamlit)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PDF Upload  │ → Extract text from PDFs
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Text Chunking│ → Split into manageable pieces
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Embeddings │ → Convert to vectors (OpenAI)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ChromaDB   │ → Vector database
└──────┬──────┘
       │
       ▼
┌─────────────┐
│RAG Pipeline │ → Retrieve + Generate (GPT-4)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Response   │ → Answer, Quiz, Guide, etc.
└─────────────┘
```

## File Structure

```
rag_study_assistant/
├── app_enhanced.py          # Main Streamlit application
├── ai_study_assistant.py    # RAG system core logic
├── requirements.txt         # Python dependencies
├── .env                     # API keys (don't commit!)
├── .streamlit/
│   └── config.toml         # Streamlit configuration
├── Procfile                # For Railway/Heroku deployment
├── README.md               # This file
├── DEPLOYMENT.md           # Detailed deployment guide
└── QUICK_START.md          # Quick deployment guide
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)

### Customization

Edit `app_enhanced.py` to:
- Change the UI theme (in `.streamlit/config.toml`)
- Modify chunk sizes for better performance
- Add authentication
- Customize system prompts
- Add more study tools

## Cost Estimates

### OpenAI API Usage
- Processing 10 PDFs (~100 pages): $1-2
- 50 Q&A queries: $2-5
- Monthly (1 active user): $10-30

### Deployment Costs
- Streamlit Cloud: Free tier available
- Railway: ~$5/month
- Render: Free tier (with limits)
- Self-hosted VPS: $5-20/month

## Security Notes

⚠️ **Important:**
- Never commit your `.env` file
- Monitor your OpenAI usage regularly
- Consider adding authentication for production
- Implement rate limiting for public deployments

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed security recommendations.

## Development

### Adding New Features

1. **New study tool:**
   - Add method to `ai_study_assistant.py`
   - Add UI section in `app_enhanced.py`

2. **New data source:**
   - Extend PDF processing in `ai_study_assistant.py`
   - Add file type support in `app_enhanced.py`

### Testing

```bash
# Test the assistant locally
python -c "from ai_study_assistant import AIStudyAssistant; a = AIStudyAssistant(); print('OK')"

# Run the app
streamlit run app_enhanced.py
```

## Troubleshooting

### "Can't find module X"
```bash
pip install -r requirements.txt
```

### "OpenAI API key not set"
Check your `.env` file has:
```
OPENAI_API_KEY=sk-...
```

### "PDF processing fails"
- Ensure PDF is text-based (not scanned image)
- Try smaller files first
- Check file isn't corrupted

### "Out of memory"
- Reduce chunk size in `ai_study_assistant.py`
- Process fewer PDFs at once
- Use smaller embedding model

## Contributing

This is a homework project, but feel free to:
1. Fork for your own use
2. Modify for your needs
3. Share improvements

## License

MIT License - feel free to use for personal or educational purposes.

## Acknowledgments

Built using:
- [Streamlit](https://streamlit.io) - Web framework
- [ChromaDB](https://www.trychroma.com) - Vector database
- [OpenAI](https://openai.com) - LLM and embeddings
- [LangChain](https://langchain.com) - Text processing utilities

## Support

For deployment help, see [QUICK_START.md](QUICK_START.md)  
For detailed deployment options, see [DEPLOYMENT.md](DEPLOYMENT.md)

## Version History

- v1.0 - Initial release with RAG functionality
- v1.1 - Added PDF upload and multi-user support
- v1.2 - Enhanced UI and deployment configurations