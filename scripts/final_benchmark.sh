#!/bin/bash

echo "Starting final benchmarking experiment..."

# Ensure load balancer and scaling controller are running
echo "Make sure your load balancer and scaling controller services are active."

# Define load pattern (user load increasing then decreasing)
user_load=(10 20 40 60 80 100 80 60 40 20 10)
duration=60 # seconds per step

for users in "${user_load[@]}"; do
    echo "Running load test with $users users..."
    locust -f ../load-generator/locustfile.py \
        --host=http://localhost:8100 \
        --users $users --spawn-rate 20 --run-time ${duration}s --headless \
        --csv="final_benchmark_${users}_users"
    sleep 10
done

echo "Final benchmark completed."
