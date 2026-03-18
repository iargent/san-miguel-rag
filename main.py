import os
import anthropic
import voyageai
import chromadb

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
from pydantic import BaseModel

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION_NAME = "san_miguel"
VOYAGE_MODEL = "voyage-3-lite"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
N_RESULTS = 3

anthropic_client = anthropic.Anthropic()
voyage_client = voyageai.Client()


@asynccontextmanager
async def lifespan(app):
    global collection
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma_client.get_collection(COLLECTION_NAME)
    print(f"Loaded collection with {collection.count()} documents")
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
    query_embedding = result.embeddings[0]

    results = collection.query(query_embeddings=[query_embedding], n_results=N_RESULTS)
    return results["documents"][0]


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
