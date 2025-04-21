#!/bin/bash

echo "Starting single-container saturation test..."

# Start a single webapp container
podman run -d --name webapp1 --network mynet -v /materials-assignment1/function/data/watermarks:/app/data:z webapp

# Run load test with increasing users (10, 20, 30...100)
for users in {10..100..10}; do
    echo "Testing with $users users..."
    locust -f ../load-generator/locustfile.py \
        --host=http://localhost:8080 \
        --users $users --spawn-rate 10 --run-time 1m --headless \
        --csv="single_container_${users}_users"
    sleep 5
done

# Stop and remove the container
podman stop webapp1 && podman rm webapp1

echo "Single-container calibration completed."
