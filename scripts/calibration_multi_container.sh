#!/bin/bash

echo "Starting multi-container calibration tests..."

# Test with 1 to 3 containers
for num_containers in {1..3}; do
    echo "Starting $num_containers container(s)..."
    for i in $(seq 1 $num_containers); do
        podman run -d --name webapp$i --network mynet -v /materials-assignment1/function/data/watermarks:/app/data:z webapp
    done
    
    # Update load balancer backends dynamically
    backend_json=$(jq -nc --argjson containers "$(seq -f 'webapp%.0f' 1 $num_containers)" \
        '{"backends": [ $containers[] | \"http://\" + . + \":8080/watermark\" ]}')
    curl -X POST http://localhost:8100/update_backends \
        -H "Content-Type: application/json" \
        -d "$backend_json"

    # Perform load test
    users=$((num_containers * 30))
    locust -f ../load-generator/locustfile.py \
        --host=http://localhost:8100 \
        --users $users --spawn-rate 10 --run-time 1m --headless \
        --csv="multi_container_${num_containers}_containers"
    
    # Cleanup containers
    for i in $(seq 1 $num_containers); do
        podman stop webapp$i && podman rm webapp$i
    done
    sleep 5
done

echo "Multi-container calibration completed."
