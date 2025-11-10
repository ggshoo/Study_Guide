#!/bin/bash

# Quick run script for RAG Study Assistant

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please create one with your OPENAI_API_KEY"
    exit 1
fi

# Run the app
echo "🚀 Starting AI Study Assistant..."
streamlit run app_enhanced.py