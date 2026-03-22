# Standard library
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Third-party
import anthropic
import boto3
import faiss
import httpx
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

load_dotenv()

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)

S3_BUCKET = os.getenv("INDEX_BUCKET", "")
INDEX_FILE = os.getenv("INDEX_FILE", "index.faiss")
DOCS_FILE = os.getenv("DOCS_FILE", "docs.json")
TMP_INDEX = "/tmp/index.faiss"
TMP_DOCS = "/tmp/docs.json"
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = "voyage-3-lite"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
N_RESULTS = 3

anthropic_client = anthropic.Anthropic()
faiss_index = None
documents = None
query_table = None


# get the user's ip and not the one from CloudFront
def get_real_ip(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host


limiter = Limiter(key_func=get_real_ip)


def embed(texts, input_type="document"):
    response = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {VOYAGE_API_KEY}"},
        json={"model": VOYAGE_MODEL, "input": texts, "input_type": input_type},
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]


def log_query(question, answer, source_count, ip_address):
    if query_table is None:
        return
    try:
        query_table.put_item(
            Item={
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "question": question,
                "answer_preview": answer[:200],
                "source_count": source_count,
                "ip_address": ip_address,
            }
        )
    except Exception as e:
        logger.error(f"Failed to log query: {e}")


@asynccontextmanager
async def lifespan(app):
    global faiss_index, documents, query_table
    if S3_BUCKET:
        # Production: download from S3
        print(f"Downloading index files from S3 bucket: {S3_BUCKET}")
        s3 = boto3.client("s3")
        s3.download_file(S3_BUCKET, INDEX_FILE, TMP_INDEX)
        s3.download_file(S3_BUCKET, DOCS_FILE, TMP_DOCS)
        index_path = TMP_INDEX
        docs_path = TMP_DOCS
        query_table = boto3.resource("dynamodb", region_name="eu-west-1").Table(
            "san-miguel-rag-queries"
        )
    else:
        # Local development — skip DynamoDB
        print(
            "No S3_BUCKET set, running in local development mode with local index files"
        )
        index_path = INDEX_FILE
        docs_path = DOCS_FILE

    faiss_index = faiss.read_index(index_path)
    with open(docs_path, encoding="utf-8") as f:
        documents = json.load(f)
    print(f"Loaded FAISS index with {faiss_index.ntotal} vectors")
    yield


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please wait a moment before trying again."
        },
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

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
    embeddings = embed([question], input_type="query")
    query_vector = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(query_vector)
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
@limiter.limit("10/minute")
def ask(body: AskRequest, request: Request):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    context_docs = retrieve(body.question)
    if not context_docs:
        raise HTTPException(status_code=500, detail="Could not retrieve context")

    prompt = build_prompt(question=body.question, context_docs=context_docs)
    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text

    log_query(
        question=body.question,
        answer=answer,
        source_count=len(context_docs),
        ip_address=get_real_ip(request),
    )

    return {"answer": answer, "sources": [doc[:100] + "..." for doc in context_docs]}


handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
