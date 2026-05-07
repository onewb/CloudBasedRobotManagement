#!/bin/bash

echo "🔻 Scaling down robot-worker to 0..."
kubectl scale deployment robot-worker --replicas=0

echo "🧹 Clearing Firestore robots collection..."
python3 -c "
from google.cloud import firestore
db = firestore.Client(project='cloud-based-robot-management')
docs = db.collection('robots').stream()
for doc in docs:
    print(f'  Deleted: {doc.id}')
    doc.reference.delete()
print('✅ Firestore cleared.')
"

echo "✅ Scale down complete."