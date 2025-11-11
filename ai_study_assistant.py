import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
import openai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIStudyAssistant:
    def __init__(self, persist_directory="db"):
        """Initialize the AI Study Assistant with a ChromaDB instance."""
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="lecture_content",
            metadata={"hnsw:space": "cosine"}
        )

        # Configure OpenAI API key if present in environment.
        # Note: Streamlit app can also set openai.api_key at runtime via user input.
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            openai.api_key = env_key

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        # Default model for generation (faster than full GPT-4)
        self.GEN_MODEL = os.getenv("GEN_MODEL", "gpt-4o-mini")

    def get_embeddings_batch(self, texts):
        """Batch embedding for efficiency (fewer network round-trips)."""
        resp = openai.Embedding.create(model="text-embedding-3-small", input=texts)
        # API returns embeddings in the same order as inputs
        return [item["embedding"] for item in resp["data"]]

    def get_embedding(self, text: str):
        """Call OpenAI Embeddings API directly and return the vector."""
        # Use text-embedding-3-small for cost-effectiveness; replace if you prefer another model
        resp = openai.Embedding.create(model="text-embedding-3-small", input=text)
        return resp["data"][0]["embedding"]

    def process_transcription(self, file_path):
        """Process a transcription file and add it to the vector database."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split content into chunks
        chunks = self.text_splitter.split_text(content)

        # Generate embeddings in batches and add to ChromaDB
        BATCH_SIZE = 24
        for start in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Processing chunks"):
            batch = chunks[start:start + BATCH_SIZE]
            embeddings = self.get_embeddings_batch(batch)
            ids = [f"{Path(file_path).stem}_{i}" for i in range(start, start + len(batch))]
            metadatas = [{"source": file_path, "chunk_id": i} for i in range(start, start + len(batch))]
            self.collection.add(
                documents=batch,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas,
            )

    def query_knowledge_base(self, query, n_results=3):
        """Query the knowledge base with a natural language question."""
        # Generate query embedding
        query_embedding = self.get_embedding(query)

        # Search for relevant chunks
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results
        )

        # Prepare context from results
        context = "\n\n".join(results["documents"][0])

        # Generate response using GPT
        response = openai.ChatCompletion.create(
            model=self.GEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI study assistant for the AI Applications class. 
                Use the provided context to answer questions accurately and helpfully. 
                If the context doesn't contain enough information to answer fully, acknowledge this and suggest what additional information might be needed.""",
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        return {
            "answer": response.choices[0].message["content"],
            "source_chunks": results["documents"][0],
            "metadata": results["metadatas"][0],
        }

    def generate_quiz(self, topic):
        """Generate a quiz based on the content in the knowledge base."""
        # First, retrieve relevant content about the topic
        query_embedding = self.get_embedding(topic)
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=5
        )

        context = "\n\n".join(results["documents"][0])

        # Generate quiz using GPT
        response = openai.ChatCompletion.create(
            model=self.GEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """Generate a quiz based on the provided content. 
                Create 3 questions of varying difficulty (easy, medium, hard).
                Each question should test understanding rather than mere recall.
                Include answers and explanations.""",
                },
                {"role": "user", "content": f"Content to base quiz on:\n{context}"},
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        return response.choices[0].message["content"]

    def create_study_guide(self, topic):
        """Create a focused study guide on a specific topic."""
        query_embedding = self.get_embedding(topic)
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=5
        )

        context = "\n\n".join(results["documents"][0])

        response = openai.ChatCompletion.create(
            model=self.GEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """Create a comprehensive study guide based on the provided content.
                Include:
                1. Key concepts and definitions
                2. Important relationships and connections
                3. Common misconceptions
                4. Practice problems or examples
                5. Summary of main points""",
                },
                {"role": "user", "content": f"Content to base study guide on:\n{context}"},
            ],
            temperature=0.5,
            max_tokens=1500,
        )

        return response.choices[0].message["content"]

    def concept_map(self, topic):
        """Generate a textual concept map showing relationships between ideas."""
        query_embedding = self.get_embedding(topic)
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=4
        )

        context = "\n\n".join(results["documents"][0])

        response = openai.ChatCompletion.create(
            model=self.GEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """Create a textual concept map showing relationships between key ideas.
                Use simple ASCII/Unicode characters to show connections.
                Format should be clear and readable in a monospace font.""",
                },
                {"role": "user", "content": f"Content to map:\n{context}"},
            ],
            temperature=0.4,
            max_tokens=1000,
        )

        return response.choices[0].message["content"]