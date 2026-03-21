#!/bin/bash

# calls build.sh and handles the AWS upload (the main deployment command)

set -e

./build.sh

echo "Uploading to S3..."
aws s3 cp deployment.zip s3://cv-optimiser-iain-argent/san-miguel-rag/deployment.zip \
    --region eu-west-1

echo "Updating Lambda..."
aws lambda update-function-code \
    --function-name san-miguel-rag \
    --s3-bucket cv-optimiser-iain-argent \
    --s3-key san-miguel-rag/deployment.zip \
    --region eu-west-1
    
echo "Deployment complete."

