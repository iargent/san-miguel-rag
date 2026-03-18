import os
import json
import faiss
import numpy as np
import voyageai
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = "docs"
INDEX_FILE = "index.faiss"
DOCS_FILE = "docs.json"
VOYAGE_MODEL = "voyage-3-lite"

voyage_client = voyageai.Client()


def load_documents(docs_dir):
    documents = []
    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                documents.append({"id": filename, "text": text})
    print(f"Loaded {len(documents)} documents")
    return documents


def embed_documents(documents):
    texts = [doc["text"] for doc in documents]
    result = voyage_client.embed(texts, model=VOYAGE_MODEL, input_type="document")
    print(f"Embedded {len(result.embeddings)} documents")
    return result.embeddings


def build_index(documents, embeddings):
    vectors = np.array(embeddings, dtype=np.float32)
    dimension = vectors.shape[1]

    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    faiss.write_index(index, INDEX_FILE)
    print(f"Saved FAISS index to {INDEX_FILE}")

    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump([doc["text"] for doc in documents], f, ensure_ascii=False)
    print(f"Saved documents to {DOCS_FILE}")


if __name__ == "__main__":
    documents = load_documents(DOCS_DIR)
    embeddings = embed_documents(documents)
    build_index(documents, embeddings)
    print("Indexing complete")
