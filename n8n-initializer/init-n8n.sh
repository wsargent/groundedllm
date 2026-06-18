#!/bin/bash

echo "Waiting for n8n to be ready..."

# Wait for n8n container to be running and responsive
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES - Testing n8n connectivity..."
    
    # Test if we can reach n8n's web interface
    if curl -f -s http://grounded_n8n:5678 > /dev/null 2>&1; then
        echo "n8n is responding, waiting a bit more for full initialization..."
        sleep 10
        break
    fi
    
    echo "n8n not ready yet, waiting..."
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "n8n failed to start within expected time"
    exit 1
fi

echo "n8n is ready, creating admin user via API..."

# Create admin user via n8n API
RESPONSE=$(curl -s -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "email": "admin@example.com",
        "password": "YourSecurePassword123!",
        "firstName": "Admin",
        "lastName": "User"
    }' \
    http://grounded_n8n:5678/rest/owner/setup)

HTTP_CODE=$(echo "$RESPONSE" | tail -c 4)
BODY=$(echo "$RESPONSE" | sed '$s/...$//')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "Admin user created successfully!"
elif [ "$HTTP_CODE" = "400" ]; then
    echo "Admin user may already exist or setup already completed"
else
    echo "Failed to create admin user. HTTP Code: $HTTP_CODE"
    echo "Response: $BODY"
fi

echo "n8n initialization complete"