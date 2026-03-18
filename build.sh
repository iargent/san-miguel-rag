#!/bin/bash

set -e

echo "Cleaning previous build..."
rm -rf ./package
mkdir ./package

echo "Running indexer..."
python3 indexer.py

echo "Installing dependencies using Docker..."
docker run --rm \
    --entrypoint pip \
    -v "$(pwd)/package:/package" \
    amazon/aws-lambda-python:3.13 \
    install \
        fastapi \
        uvicorn \
        anthropic \
        "voyageai==0.3.7" \
        chromadb \
        mangum \
        python-dotenv \
        -t /package

echo "Copying app code..."
cp main.py package/
cp -r chroma_db package/

echo "Building zip..."
cd package
zip -r ../deployment.zip . --quiet
cd ..

echo "Done. $(ls -lh deployment.zip | awk '{print $5}') deployment.zip ready."
