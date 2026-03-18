import os
import json
import faiss
import numpy as np
import httpx
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = "docs"
INDEX_FILE = "index.faiss"
DOCS_FILE = "docs.json"
VOYAGE_MODEL = "voyage-3-lite"
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")


def embed(texts, input_type="document"):
    response = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {VOYAGE_API_KEY}"},
        json={"model": VOYAGE_MODEL, "input": texts, "input_type": input_type},
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


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
    embeddings = embed([doc["text"] for doc in documents], input_type="document")
    print(f"Embedded {len(embeddings)} documents")
    build_index(documents, embeddings)
    print("Indexing complete")
