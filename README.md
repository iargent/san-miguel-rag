# San Miguel de Salinas — Local Information Assistant

A multilingual AI-powered assistant that allows residents and visitors to ask questions about San Miguel de Salinas, a small town in the Alicante province of Spain. The assistant answers in the same language the question is asked — English, Spanish, or French — drawing on content from the official town hall website.

## Live Demo

Hosted on AWS S3: [https://salinasjournal.com](https://salinasjournal.com)

## Example

**Question (English):** When is the next tapas run?

**Answer:** The next Ruta de la Tapa is scheduled for Sunday, March 22, 2026. Participants can enjoy a tapa plus a drink for €3.50 at 13 participating bars and restaurants. There will be live music throughout the day and a free bus service to help you get between venues.

## How It Works

This project uses a Retrieval-Augmented Generation (RAG) pipeline:

1. **Indexing** — Town hall blog posts are embedded using the Voyage AI API and stored in a FAISS vector index
2. **Retrieval** — When a question is asked, it is embedded and the most semantically similar documents are retrieved from the index
3. **Generation** — The retrieved documents are passed to Claude (Anthropic) as context, along with an instruction to respond in the user's language

This approach grounds the AI's responses in real, up-to-date local information rather than relying on general training data.

## Architecture

```
Browser → S3 (static HTML/JS frontend)
Browser → API Gateway → Lambda (FastAPI + Mangum) → Voyage AI (embeddings)
                                                    → Anthropic Claude (generation)
                                                    → FAISS index (bundled in Lambda package)
```

## Tech Stack

| Component | Technology |
|---|---|
| Backend framework | FastAPI (Python) |
| LLM | Anthropic Claude (claude-haiku) |
| Embeddings | Voyage AI (voyage-3-lite) via REST API |
| Vector search | FAISS |
| Rate limiting | SlowAPI |
| Serverless runtime | AWS Lambda (Python 3.13) |
| API layer | AWS API Gateway (HTTP API) |
| Frontend hosting | AWS S3 (static website) |
| Build environment | Docker (amazon/aws-lambda-python:3.13) |
| Infrastructure as Code | Terraform |

## Project Structure

```
san-miguel-rag/
  docs/               # Source documents (plain text, one file per post)
  static/
    index.html        # Frontend — single page, no framework
  terraform/          # Infrastructure as Code
    main.tf
    s3.tf
    iam.tf
    lambda.tf
    api_gateway.tf
    variables.tf
    outputs.tf
  indexer.py          # Builds the FAISS vector index from docs/
  main.py             # FastAPI application
  build.sh            # Builds deployment.zip using Docker
  deploy.sh           # Uploads and deploys to AWS Lambda
  requirements.txt
  .gitignore
```

## Local Development

### Prerequisites

- Python 3.13
- Docker
- AWS CLI configured with appropriate credentials
- Anthropic API key
- Voyage AI API key

### Setup

```bash
git clone https://github.com/your-username/san-miguel-rag
cd san-miguel-rag
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```
ANTHROPIC_API_KEY=your-key-here
VOYAGE_API_KEY=your-key-here
```

### Run the indexer

```bash
python3 indexer.py
```

### Run locally

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)

## Deployment

### First-time setup

Create AWS infrastructure using Terraform:

```bash
cd terraform
terraform init
terraform apply
```

### Deploy

```bash
./deploy.sh
```

This script runs the indexer, packages the application using Docker, uploads to S3, and updates the Lambda function.

### Adding new documents

1. Add `.txt` files to the `docs/` folder
2. Run `./deploy.sh`

The indexer runs automatically as part of the deployment pipeline.

## Design Decisions

**Why FAISS instead of a managed vector database?**
For a corpus of ~30 documents, a managed vector database like Pinecone would be unnecessary overhead. FAISS runs in-memory and is bundled directly into the Lambda deployment package, keeping the architecture simple and the running cost near zero.

**Why direct HTTP calls instead of the Voyage AI SDK?**
The voyageai Python SDK pulls in a large dependency tree including langchain, pillow, tokenizers, and ffmpeg — none of which are needed for text embedding. Replacing the SDK with a direct httpx call reduced the deployment package from ~170MB to ~27MB.

**Why Lambda layers?**
FAISS and numpy together exceed 150MB unzipped. Splitting them into a Lambda layer keeps the function package small while staying within Lambda's limits.

**Cost**
At low traffic, this application runs for effectively nothing. Lambda, API Gateway, and S3 all have generous free tiers that comfortably cover personal or community-scale usage.

## Limitations

- Documents must be added manually as `.txt` files — there is no automated scraper yet
- The knowledge base reflects the documents available at the time of the last deployment

## Roadmap

- [ ] Automated scraper to fetch new town hall posts on a schedule
- [ ] Separate indexer Lambda triggered weekly by EventBridge
- [✓] FAISS index stored in S3 and loaded at Lambda startup (removes need to redeploy for new content)
- [ ] Facebook Messenger bot integration
- [ ] Support for additional sources (local newspaper, community notices)
