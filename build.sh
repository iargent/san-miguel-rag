#!/bin/bash

set -e

echo "Cleaning previous build..."
rm -rf ./package
mkdir ./package

echo "Running indexer..."
python3 indexer.py

echo "Installing dependencies using Docker..."
docker run --rm \
    --entrypoint /bin/bash \
    -v "$(pwd)/package:/package" \
    amazon/aws-lambda-python:3.13 \
    -c "pip install \
        fastapi \
        uvicorn \
        anthropic \
        'voyageai==0.3.7' \
        faiss-cpu \
        numpy \
        mangum \
        python-dotenv \
        -t /package && chown -R $(id -u):$(id -g) /package"
        
echo "Copying app code..."
cp main.py package/
cp index.faiss package/
cp docs.json package/

echo "Building zip..."
cd package
zip -r ../deployment.zip . --quiet
cd ..

echo "Done. $(ls -lh deployment.zip | awk '{print $5}') deployment.zip ready."
