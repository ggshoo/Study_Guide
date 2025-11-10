#!/bin/bash

# Setup script for RAG Study Assistant

echo "🚀 Setting up RAG Study Assistant..."
echo ""

# Check if we're in the right directory
if [ ! -f "app_enhanced.py" ]; then
    echo "❌ Error: Please run this script from the rag_study_assistant directory"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found. Creating template..."
    echo "OPENAI_API_KEY=your_api_key_here" > .env
    echo ""
    echo "📝 Please edit .env and add your OpenAI API key"
    echo "   Get your key at: https://platform.openai.com/api-keys"
else
    echo "✅ .env file found"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the app:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Run: streamlit run app_enhanced.py"
echo ""
echo "Or simply run: ./run.sh"
echo ""