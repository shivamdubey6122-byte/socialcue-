import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Native ChromaDB initialization
CHROMA_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'chroma_data'))
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    memory_collection = chroma_client.get_or_create_collection(name="native_memories")
except Exception as e:
    print(f"Native ChromaDB init failed: {e}")
    memory_collection = None

# Native LLM initialization (Assumes local Ollama or falls back to basic string matching)
try:
    llm = Ollama(model="mistral", base_url="http://localhost:11434", temperature=0.7)
except Exception as e:
    print(f"Native LLM init failed: {e}")
    llm = None

def generate_greeting_native(name: str, relation: str, context: str, emotion: str) -> str:
    """Generates a dynamic greeting using the native LLM."""
    if not llm:
        return f"{name} detected. Relation: {relation}. You seem {emotion}."

    prompt_template = """
    You are an AI assistant in a smart wearable device. You just detected someone the user knows.
    Provide a short, natural, single-sentence spoken greeting that the user will hear in their earpiece.
    
    Context about the person:
    - Name: {name}
    - Relation: {relation}
    - Recent context/memory: {context}
    - Current emotion: {emotion}

    Keep it concise, friendly, and under 15 words.
    
    Greeting:"""

    prompt = PromptTemplate(input_variables=["name", "relation", "context", "emotion"], template=prompt_template)
    chain = LLMChain(llm=llm, prompt=prompt)
    
    try:
        return chain.run({"name": name, "relation": relation, "context": context, "emotion": emotion}).strip().replace('"', '')
    except Exception as e:
        print(f"Native LLM Error: {e}")
        return f"Hello, {name}."

def store_native_memory(person_name: str, summary: str, topics: list):
    """Stores a conversational memory natively into ChromaDB."""
    if not memory_collection: return False
    
    import uuid
    doc_id = str(uuid.uuid4())
    metadata = {"person": person_name.lower(), "topics": ",".join(topics)}
    
    try:
        memory_collection.add(documents=[summary], metadatas=[metadata], ids=[doc_id])
        return True
    except Exception as e:
        print(f"Failed to insert into native ChromaDB: {e}")
        return False

def retrieve_native_memory(person_name: str, query: str = "", n_results: int = 1):
    """Semantically retrieves a conversational memory."""
    if not memory_collection: return []
    
    try:
        results = memory_collection.query(
            query_texts=[query] if query else [f"conversations with {person_name}"],
            n_results=n_results,
            where={"person": person_name.lower()}
        )
        if results and "documents" in results and len(results["documents"]) > 0:
            return results["documents"][0]
        return []
    except Exception as e:
        print(f"Native Query error: {e}")
        return []
