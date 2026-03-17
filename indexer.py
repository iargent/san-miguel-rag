import os
import voyageai
import chromadb
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "san_miguel"
VOYAGE_MODEL = "voyage-3-lite"

voyage_client = voyageai.Client()
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)


def load_documents(docs_dir):
    documents = []
    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                documents.append({"id": filename, "text": text, "filename": filename})
    print(f"Loaded {len(documents)} documents")
    return documents


def embed_documents(documents):
    texts = [doc["text"] for doc in documents]
    result = voyage_client.embed(texts, model=VOYAGE_MODEL, input_type="document")
    print(f"Embedded {len(result.embeddings)} documents")
    return result.embeddings


def store_documents(documents, embeddings):
    # Delete existing collection if it exists so we start fresh
    existing = [c.name for c in chroma_client.list_collections()]
    if COLLECTION_NAME in existing:
        chroma_client.delete_collection(COLLECTION_NAME)
        print("Deleted existing collection")
    collection = chroma_client.create_collection(COLLECTION_NAME)
    collection.add(
        ids=[doc["id"] for doc in documents],
        documents=[doc["text"] for doc in documents],
        embeddings=embeddings,
        metadatas=[{"filename": doc["filename"]} for doc in documents],
    )
    print(f"Stored {len(documents)} documents in ChromaDB")


if __name__ == "__main__":
    documents = load_documents(DOCS_DIR)
    embeddings = embed_documents(documents)
    store_documents(documents, embeddings)
    print("Indexing complete")
