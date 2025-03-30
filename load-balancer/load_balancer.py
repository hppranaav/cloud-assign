import requests
from fastapi import FastAPI, Request
import uvicorn
import subprocess
import logging
import psutil
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

app = FastAPI()

BACKENDS = []
CONTAINER_IMAGE = "webapp"

class LoadBalancer:
    def __init__(self):
        self.index = 0
        self.backend_request_count = {}
        self.total_requests = 0
        self.dropped_requests = 0
        self.failed_requests = 0
        self.latency_records = 0
        self.policy_switch_count = 0
        self.current_policy = "round_robin"
        logging.info("Initializing LoadBalancer")
        self.update_backends()

    def update_backends(self):
        global BACKENDS
        try:
            result = subprocess.run(["podman", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
            containers = [c for c in result.stdout.splitlines() if "webapp" in c]
            BACKENDS = [f"https://{c}:5000" for c in containers]
            
            for backend in list(self.backend_request_count.keys()):
                if backend not in BACKENDS:
                    del self.backend_request_count[backend]
            
            for backend in BACKENDS:
                if backend not in self.backend_request_count:
                    self.backend_request_count[backend] = 0
            
            logging.info("Updated BACKENDS: %s", BACKENDS)
        except Exception as e:
            logging.error("Failed to update backends: %s", e)

    def round_robin(self):
        if not BACKENDS:
            logging.warning("BACKENDS is empty, updating backends")
            self.update_backends()
        backend = BACKENDS[self.index]
        self.index = (self.index + 1) % len(BACKENDS)
        logging.info("Selected backend (round robin): %s", backend)
        return backend

    def state_aware(self):
        self.update_backends()
        metrics = {}
        for backend in BACKENDS:
            try:
                response = requests.get(f"{backend}/metrics", timeout=1)
                metrics[backend] = response.json().get("cpu_usage", 100)
                logging.info("Fetched metrics from %s: %s", backend, metrics[backend])
            except requests.exceptions.RequestException as e:
                metrics[backend] = 100
                logging.warning("Failed to fetch metrics from %s: %s", backend, e)
        selected_backend = min(metrics, key=metrics.get)
        logging.info("Selected backend (state aware): %s", selected_backend)
        return selected_backend

    def get_backend(self, policy="round_robin"):
        if policy != self.current_policy:
            self.policy_switch_count += 1
            self.current_policy = policy
            logging.info("Switched to load balancing policy: %s", policy)
        return self.state_aware() if policy == "state_aware" else self.round_robin()
    
    def increment_dropped_requests(self):
        self.dropped_requests += 1
        logging.warning(f"Request dropped. Total dropped requests: {self.dropped_requests}")

    def increment_failed_requests(self):
        self.failed_requests += 1
        logging.warning(f"Request failed. Total failed requests: {self.failed_requests}")

    def calculate_error_rate(self):
        if self.request_rate > 0:
            return (self.failed_requests / self.request_rate) * 100
        return 0
    
    def get_all_container_stats():
        try:
            result = subprocess.run(
                ["podman", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                logging.error(f"Failed to get container list: {result.stderr}")
                return None
            
            container_names = result.stdout.strip().splitlines()
            container_stats = {}

            for container_name in container_names:
                stats_result = subprocess.run(
                    ["podman", "stats", container_name, "--no-stream", "--format", "{{.CPUPerc}} {{.MemUsage}}"],
                    capture_output=True, text=True
                )

                if stats_result.returncode == 0:
                    stats = stats_result.stdout.strip().split()
                    cpu_usage = stats[0].replace('%', '')
                    mem_usage = stats[1]
                    container_stats[f"https://{container_name}:5000"] = (float(cpu_usage), mem_usage)
                    logging.info(f"Container {container_name}: CPU={cpu_usage}%, MEM={mem_usage}")
                else:
                    logging.warning(f"Failed to get stats for container {container_name}: {stats_result.stderr}")
                    container_stats[container_name] = (None, None)

            return container_stats

        except Exception as e:
            logging.error(f"Error retrieving container stats: {e}")
            return None
                

lb = LoadBalancer()

@app.get("/")
async def load_balancer(request: Request):
    policy = request.query_params.get("policy", "round_robin")
    logging.info("Received request with policy: %s", policy)
    try:
        start_time = time.time()
        backend = lb.get_backend(policy)
        response = requests.get(backend)
        latency = (time.time() - start_time) * 1000
        lb.latency_records.append(latency)
        if len(lb.latency_records) > 100:
            lb.latency_records.pop(0)
        
        lb.total_requests += 1
        lb.backend_request_count[backend] = lb.backend_request_count.get(backend, 0) + 1
        
        logging.info("Forwarded request to backend: %s", backend)
        logging.info("Total requests handled: %d", lb.total_requests)
        logging.info("Requests sent to backends: %s", lb.backend_request_count)
        
        return response.content
    except Exception as e:
        lb.increment_failed_requests()
        lb.increment_dropped_requests()
        logging.error("Failed to forward request: %s", e)
        return {"error": "Failed to forward request"}
    

@app.get("/metrics")
async def get_metrics(request: Request):
    logging.info("Fetching metrics for load balancer")
    backend_metrics = {}
    container_stats = lb.get_all_container_stats()
    for backend in BACKENDS:
        backend_metrics[backend] = {
            "requests": lb.backend_request_count.get(backend, 0),
            "status": "healthy",
            "cpu_usage": container_stats.get(backend,(None, None))[0],
            "memory_usage": container_stats.get(backend,(None, None))[1],
            "error_rate": lb.calculate_error_rate(),
        }
    
    metrics = {
        "total_requests": lb.total_requests,
        "active_connections": len(BACKENDS),
        "average_latency": sum(lb.latency_records) / len(lb.latency_records) if lb.latency_records else 0,
        "dropped_requests": lb.dropped_requests,
        "error_rate": lb.calculate_error_rate(),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "current_policy": lb.current_policy,
        "policy_switch_count": lb.policy_switch_count,
        "backend_metrics": backend_metrics,
    }
    
    logging.debug("Metrics data: %s", metrics)
    return metrics

if __name__ == "__main__":
    logging.info("Starting Load Balancer")
    uvicorn.run(app, host="0.0.0.0", port=8000)
