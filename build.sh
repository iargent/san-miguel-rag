#!/bin/bash

# packages and deploys the Lambda function (run when code changes)

set -e

echo "Cleaning previous build..."
rm -rf ./package ./layer
mkdir ./package ./layer

echo "Installing layer dependencies using Docker..."
docker run --rm \
    --entrypoint /bin/bash \
    -v "$(pwd)/layer:/layer" \
    amazon/aws-lambda-python:3.13 \
    -c "pip install \
        faiss-cpu \
        numpy \
        -t /layer/python && chown -R $(id -u):$(id -g) /layer"

echo "Installing function dependencies using Docker..."
docker run --rm \
    --entrypoint /bin/bash \
    -v "$(pwd)/package:/package" \
    amazon/aws-lambda-python:3.13 \
    -c "pip install \
        fastapi \
        uvicorn \
        anthropic \
        httpx \
        boto3 \
        mangum \
        python-dotenv \
        -t /package && \
        rm -rf /package/numpy \
        /package/numpy.libs \
        /package/faiss \
        /package/faiss_cpu.libs \
        /package/numpy-*.dist-info \
        /package/faiss_cpu-*.dist-info && \
        chown -R $(id -u):$(id -g) /package"
        
echo "Copying app code and index files..."
cp main.py package/

echo "Building layer zip..."
cd layer
zip -r ../layer.zip . --quiet
cd ..

echo "Building function zip..."
cd package
zip -r ../deployment.zip . --quiet
cd ..

echo "Layer: $(ls -lh layer.zip | awk '{print $5}')"
echo "Function: $(ls -lh deployment.zip | awk '{print $5}')"
echo "Done."