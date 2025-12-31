# db/vector_store.py

import chromadb
from chromadb.config import Settings
from utils.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE
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

def add_document_chunks(session_id, file_id, filename, chunks, progress_callback=None):
    """
    Add document chunks to ChromaDB with batched embedding generation
    
    Args:
        session_id: Chat session ID
        file_id: File ID
        filename: Filename
        chunks: List of text chunks
        progress_callback: Optional callback function(current, total) for progress updates
    
    Returns:
        Boolean indicating success
    """
    collection = get_or_create_collection(session_id)
    
    total_chunks = len(chunks)
    embeddings = []
    failed_chunks = []
    
    print(f"🔄 Generating embeddings for {total_chunks} chunks (batch size: {EMBEDDING_BATCH_SIZE})...")
    
    # Process chunks in batches to reduce API calls
    for batch_start in range(0, total_chunks, EMBEDDING_BATCH_SIZE):
        batch_end = min(batch_start + EMBEDDING_BATCH_SIZE, total_chunks)
        batch = chunks[batch_start:batch_end]
        batch_num = batch_start // EMBEDDING_BATCH_SIZE + 1
        total_batches = (total_chunks + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
        
        try:
            print(f"Processing batch {batch_num}/{total_batches} ({batch_start}-{batch_end}/{total_chunks} chunks)")
            
            # Generate embeddings for this batch
            for i, chunk in enumerate(batch):
                chunk_index = batch_start + i
                try:
                    embedding_response = ollama.embeddings(
                        model=EMBEDDING_MODEL,
                        prompt=chunk
                    )
                    embeddings.append(embedding_response['embedding'])
                    
                    # Call progress callback
                    if progress_callback:
                        progress_callback(chunk_index + 1, total_chunks)
                    
                except Exception as e:
                    print(f"❌ Error generating embedding for chunk {chunk_index}: {e}")
                    failed_chunks.append(chunk_index)
                    embeddings.append(None)  # Placeholder for failed chunks
        
        except Exception as e:
            print(f"❌ Error processing batch {batch_num}: {e}")
            return False
    
    # Check if all embeddings failed
    if len([e for e in embeddings if e is not None]) == 0:
        print("❌ All embeddings failed")
        return False
    
    # Log warning if some chunks failed
    if failed_chunks:
        print(f"⚠️ {len(failed_chunks)} chunks failed embedding generation: {failed_chunks}")
    
    # Prepare data for all chunks (including failed ones)
    ids = []
    metadatas = []
    valid_chunks = []
    valid_embeddings = []
    
    for i in range(total_chunks):
        if embeddings[i] is not None:  # Only include successful embeddings
            ids.append(f"file_{file_id}_chunk_{i}")
            metadatas.append({
                "file_id": file_id,
                "filename": filename,
                "chunk_index": i,
                "session_id": session_id
            })
            valid_chunks.append(chunks[i])
            valid_embeddings.append(embeddings[i])
    
    if not valid_chunks:
        print("❌ No valid chunks to add to collection")
        return False
    
    # Add to collection with pre-generated embeddings
    try:
        collection.add(
            documents=valid_chunks,
            metadatas=metadatas,
            embeddings=valid_embeddings,
            ids=ids
        )
        
        print(f"✅ Added {len(valid_chunks)} chunks from {filename} to session {session_id}")
        if failed_chunks:
            print(f"⚠️ {len(failed_chunks)} chunks failed to process")
        return True
    
    except Exception as e:
        print(f"❌ Error adding chunks to collection: {e}")
        return False

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