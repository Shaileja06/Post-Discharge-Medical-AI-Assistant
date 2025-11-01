import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import uuid
from config import settings
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize sentence transformer
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # ChromaDB batch size limit
        self.max_batch_size = 5000  # Safe limit
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence-transformers"""
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            batch_size=32  # Embedding batch size
        )
        return embeddings.tolist()
    
    def add_documents(self, chunks: List[str], metadata: Dict = None):
        """Add document chunks to vector store with automatic batching"""
        if not chunks:
            return
        
        total_chunks = len(chunks)
        logger.info(f"Adding {total_chunks} chunks to vector store")
        
        # Process in batches
        for i in range(0, total_chunks, self.max_batch_size):
            batch_chunks = chunks[i:i + self.max_batch_size]
            batch_num = i // self.max_batch_size + 1
            total_batches = (total_chunks + self.max_batch_size - 1) // self.max_batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")
            
            # Generate embeddings for this batch
            embeddings = self._embed_texts(batch_chunks)
            
            # Generate IDs for this batch
            ids = [str(uuid.uuid4()) for _ in batch_chunks]
            
            # Prepare metadata for this batch
            metadatas = [
                {
                    **(metadata or {}), 
                    "chunk_index": i + idx,
                    "batch": batch_num
                } 
                for idx in range(len(batch_chunks))
            ]
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=batch_chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ Batch {batch_num}/{total_batches} added successfully")
        
        logger.info(f"✅ All {total_chunks} chunks added to vector store")
    
    def search(self, query: str, n_results: int = 5) -> Dict:
        """Search for similar documents"""
        query_embedding = self._embed_texts([query])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }
    
    def reset(self):
        """Clear all documents"""
        self.client.reset()
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Vector store reset complete")