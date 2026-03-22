#!/bin/bash

# prints the 10 most recent questions with their timestamps

set -e

aws dynamodb scan \
    --table-name san-miguel-rag-queries \
    --region eu-west-1 \
    --output json \
    | python3 -c "
import json, sys
items = json.load(sys.stdin)['Items']
for item in sorted(items, key=lambda x: x['timestamp']['S'], reverse=True)[:10]:
    print(item['timestamp']['S'], '|', item['question']['S'])
"