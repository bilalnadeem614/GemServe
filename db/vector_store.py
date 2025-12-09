# db/vector_store.py
import chromadb
from chromadb.config import Settings
from utils.config import CHROMA_PERSIST_DIR

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIR,
    settings=Settings(anonymized_telemetry=False)
)

def get_or_create_collection(session_id):
    """Get or create a ChromaDB collection for a session"""
    collection_name = f"session_{session_id}"
    
    try:
        collection = chroma_client.get_collection(collection_name)
        print(f"✅ Loaded existing collection: {collection_name}")
    except:
        collection = chroma_client.create_collection(
            name=collection_name,
            metadata={"session_id": session_id}
        )
        print(f"✅ Created new collection: {collection_name}")
    
    return collection

def add_document_chunks(session_id, file_id, filename, chunks):
    """Add document chunks to ChromaDB with embeddings"""
    collection = get_or_create_collection(session_id)
    
    # Prepare data
    ids = [f"file_{file_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{
        "file_id": file_id,
        "filename": filename,
        "chunk_index": i,
        "session_id": session_id
    } for i in range(len(chunks))]
    
    # Add to collection (ChromaDB auto-generates embeddings)
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"✅ Added {len(chunks)} chunks from {filename} to session {session_id}")

def query_relevant_chunks(session_id, query_text, n_results=8):
    """Query relevant document chunks for a session"""
    collection_name = f"session_{session_id}"
    
    try:
        collection = chroma_client.get_collection(collection_name)
        
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        return results
    except:
        print(f"⚠️ No collection found for session {session_id}")
        return None

def delete_session_collection(session_id):
    """Delete ChromaDB collection for a session"""
    collection_name = f"session_{session_id}"
    
    try:
        chroma_client.delete_collection(collection_name)
        print(f"✅ Deleted collection: {collection_name}")
    except:
        print(f"⚠️ Collection {collection_name} not found")