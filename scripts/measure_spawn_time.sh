#!/bin/bash

echo "Measuring container spawn time..."

times=()

# Measure spawn time for 5 containers
for i in {1..5}; do
    start=$(date +%s.%N)
    podman run -d --name webapp_test --network mynet -v /materials-assignment1/function/data/watermarks:/app/data:z webapp
    
    # Wait for container to become responsive
    until curl -sf http://$(podman inspect -f '{{.NetworkSettings.IPAddress}}' webapp_test):8080; do sleep 0.1; done
    end=$(date +%s.%N)
    
    duration=$(echo "$end - $start" | bc)
    echo "Spawn $i took $duration seconds"
    times+=($duration)
    
    podman stop webapp_test && podman rm webapp_test
done

# Calculate average spawn time
total=0
for t in "${times[@]}"; do total=$(echo "$total + $t" | bc); done
average=$(echo "scale=2; $total / ${#times[@]}" | bc)

echo "Average container spawn time: $average seconds"
