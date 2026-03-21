#!/bin/bash
set -e

echo "Running indexer..."
python3 indexer.py

echo "Uploading index files to S3..."
aws s3 cp index.faiss s3://san-miguel-rag-index-iain-argent/index.faiss \
    --region eu-west-1
aws s3 cp docs.json s3://san-miguel-rag-index-iain-argent/docs.json \
    --region eu-west-1

echo "Index uploaded successfully."
echo "Changes will take effect on the next Lambda cold start."