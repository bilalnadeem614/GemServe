# db/vector_store.py

import chromadb
from chromadb.config import Settings
from utils.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL
import ollama

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
    """Add document chunks to ChromaDB with embeddings from Ollama"""
    collection = get_or_create_collection(session_id)
    
    # Generate embeddings using Ollama
    embeddings = []
    print(f"🔄 Generating embeddings for {len(chunks)} chunks...")
    
    for i, chunk in enumerate(chunks):
        try:
            embedding_response = ollama.embeddings(
                model=EMBEDDING_MODEL,
                prompt=chunk
            )
            embeddings.append(embedding_response['embedding'])
            print(f"Generated embedding {i+1}/{len(chunks)}", end='\r')
        except Exception as e:
            print(f"\n❌ Error generating embedding for chunk {i}: {e}")
            return False
    
    print()  # New line after progress
    
    # Prepare data
    ids = [f"file_{file_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{
        "file_id": file_id,
        "filename": filename,
        "chunk_index": i,
        "session_id": session_id
    } for i in range(len(chunks))]
    
    # Add to collection with pre-generated embeddings
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
        ids=ids
    )
    
    print(f"✅ Added {len(chunks)} chunks from {filename} to session {session_id}")
    return True

def query_relevant_chunks(session_id, query_text, n_results=8):
    """Query relevant document chunks for a session"""
    collection_name = f"session_{session_id}"
    
    try:
        collection = chroma_client.get_collection(collection_name)
        
        # Generate query embedding using Ollama
        query_embedding_response = ollama.embeddings(
            model=EMBEDDING_MODEL,
            prompt=query_text
        )
        query_embedding = query_embedding_response['embedding']
        
        # Query with pre-generated embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return results
    except Exception as e:
        print(f"⚠️ Error querying collection for session {session_id}: {e}")
        return None

def delete_session_collection(session_id):
    """Delete ChromaDB collection for a session"""
    collection_name = f"session_{session_id}"
    
    try:
        chroma_client.delete_collection(collection_name)
        print(f"✅ Deleted collection: {collection_name}")
    except:
        print(f"⚠️ Collection {collection_name} not found")