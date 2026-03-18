aws s3 cp deployment.zip s3://cv-optimiser-iain-argent/san-miguel-rag/deployment.zip \
    --region eu-west-1

aws lambda update-function-code \
    --function-name san-miguel-rag \
    --s3-bucket cv-optimiser-iain-argent \
    --s3-key san-miguel-rag/deployment.zip \
    --region eu-west-1