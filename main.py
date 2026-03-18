import os
import json
import faiss
import numpy as np
import anthropic
import voyageai
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
from pydantic import BaseModel

load_dotenv()

INDEX_FILE = os.getenv("INDEX_FILE", "index.faiss")
DOCS_FILE = os.getenv("DOCS_FILE", "docs.json")
VOYAGE_MODEL = "voyage-3-lite"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
N_RESULTS = 3

anthropic_client = anthropic.Anthropic()
voyage_client = voyageai.Client()
faiss_index = None
documents = None


@asynccontextmanager
async def lifespan(app):
    global faiss_index, documents
    faiss_index = faiss.read_index(INDEX_FILE)
    with open(DOCS_FILE, encoding="utf-8") as f:
        documents = json.load(f)
    print(f"Loaded FAISS index with {faiss_index.ntotal} vectors")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


class AskRequest(BaseModel):
    question: str


def retrieve(question):
    result = voyage_client.embed([question], model=VOYAGE_MODEL, input_type="query")
    query_vector = np.array(result.embeddings, dtype=np.float32)
    faiss.normalizeL2(query_vector)
    _, indices = faiss_index.search(query_vector, N_RESULTS)
    return [documents[i] for i in indices[0] if i < len(documents)]


def build_prompt(question, context_docs):
    context = "\n\n---\n\n".join(context_docs)
    return f"""You are a helpful local information assistant for San Miguel de Salinas, 
a small town in the Alicante province of Spain.

You have been given extracts from the official town hall website to help answer 
the user's question. Answer based on the provided context. If the context does 
not contain enough information to answer the question, say so honestly rather 
than inventing details.

Always respond in the same language the question was asked in. The context will 
be in Spanish but you should translate relevant information into the user's language.
Context:
{context}
Question:
{question}"""


@app.post("/ask")
def ask(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    context_docs = retrieve(request.question)
    if not context_docs:
        raise HTTPException(status_code=500, detail="Could not retrieve context")
    prompt = build_prompt(request.question, context_docs)
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.content[0].text,
        "sources": [doc[:100] + "..." for doc in context_docs],
    }


handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
