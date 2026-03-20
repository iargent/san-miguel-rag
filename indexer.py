import os
import json
import time
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
BATCH_SIZE = 50
BATCH_DELAY = 2  # seconds between batches


def embed(texts, input_type="document"):
    response = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {VOYAGE_API_KEY}"},
        json={"model": VOYAGE_MODEL, "input": texts, "input_type": input_type},
        timeout=30.0,
    )
    if response.status_code == 429:
        print(f"429 headers: {dict(response.headers)}")
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def embed_in_batches(texts):
    all_embeddings = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        print(
            f"  Embedding batch {batch_num}/{total_batches} ({len(batch)} documents)..."
        )
        try:
            embeddings = embed(batch, input_type="document")
            all_embeddings.extend(embeddings)
            if i + BATCH_SIZE < len(texts):
                time.sleep(BATCH_DELAY)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"  Rate limited on batch {batch_num}, waiting 60 seconds...")
                time.sleep(60)
                # Retry the same batch
                embeddings = embed(batch, input_type="document")
                all_embeddings.extend(embeddings)
            else:
                raise
    return all_embeddings


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
    print(f"Embedding {len(documents)} documents in batches of {BATCH_SIZE}...")
    embeddings = embed_in_batches([doc["text"] for doc in documents])
    print(f"Embedded {len(embeddings)} documents")
    build_index(documents, embeddings)
    print("Indexing complete")
