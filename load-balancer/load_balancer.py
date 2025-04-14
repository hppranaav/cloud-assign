import requests
from fastapi import FastAPI, Request, Form, Response
import uvicorn
import subprocess
import logging
import psutil
import time
from pathlib import Path

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
gateway_ip = ""

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
        self.response_time_history = {}
        logging.info("Initializing LoadBalancer")
        self.get_gateway_ip()
        self.update_backends()

    def get_gateway_ip(self):
        global gateway_ip
        try:
            # Make use of the /proc/net/route file to find the gateway IP as we use python:slim base image
            # and it doesn't have ip command
            # This is a workaround to get the gateway IP address
            # in a containerized environment
            with open('/proc/net/route', 'r') as f:
                for line in f.readlines():
                    fields = line.strip().split('\t')
                    if fields[1] == '00000000':
                        gateway_ip = fields[2]
                        gateway_ip = '.'.join([str(int(gateway_ip[i:i+2], 16)) for i in range(6, -2, -2)])
                        gateway_ip = f"http://{gateway_ip}:8300/containers"
                        logging.info(f"Gateway IP: {gateway_ip}")
                        break
        except Exception as e:
            logging.error(f"Failed to get gateway IP: {e}")

    def update_backends(self):
        global BACKENDS
        try:
            logging.info("Updating backends")

            result = requests.get(gateway_ip)
            if result.status_code != 200:
                logging.error(f"Failed to get container list: {result.text}")
                return

            containers = result.json().get("containers", [])
            if not containers:
                logging.warning("No containers found")
                return
            
            BACKENDS = [f"http://{c}:8080/watermark" for c in containers]
            
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
        DEFAULT_LATENCY = 0.2
        metrics = []
        for backend in BACKENDS:
            try:
                latencies = self.response_time_history.get(backend)
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                else:
                    avg_latency = DEFAULT_LATENCY
                    
                logging.warning("No latency data yet for %s", backend)
                                active_conn = self.backend_request_count.get(backend, 0)
                metrics.append({
                    "backend": backend,
                    "avg_latency": avg_latency,
                    "connections": active_conn
                })
                logging.info("Backend %s: avg_latency=%.4fs, active_conn=%d", backend, avg_latency, active_conn)
            except Exception as e:
                logging.error("Error processing backend %s: %s", backend, e)
                continue
        
        if not metrics:
            logging.error("No latency history for any backend")
        return None

        selected = sorted(metrics, key=lambda x: (x["avg_latency"], x["connections"]))[0]
        logging.info("Selected backend (real-response latency-aware): %s", selected["backend"])
        return selected["backend"]

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
        if self.total_requests > 0:
            return (self.failed_requests / self.total_requests) * 100
        return 0
    
    def get_all_container_stats(self):
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
                    container_stats[f"https://{container_name}:8080"] = (float(cpu_usage), mem_usage)
                    logging.info(f"Container {container_name}: CPU={cpu_usage}%, MEM={mem_usage}")
                else:
                    logging.warning(f"Failed to get stats for container {container_name}: {stats_result.stderr}")
                    container_stats[container_name] = (None, None)

            return container_stats

        except Exception as e:
            logging.error(f"Error retrieving container stats: {e}")
            return None
                

lb = LoadBalancer()

@app.post("/route")
async def load_balancer(data: str = Form(None), file: str = Form(None), output: str = Form(None)):
    try:

        if not data or not file:
            logging.error("Missing required fields: data or file")
            return {"error": "Both 'data' and 'file' are required"}, 400

        filepath = "/app/data/" + file
        datadict={'watermark-size': data}

        if not Path(filepath).is_file():
            logging.error("File does not exist: %s", file)
            return {"error": "File not found"}, 400
        logging.info("File exists: %s", filepath) # Remove this log when submitting
        filedict = {"image": Path(filepath).open("rb")}
        
        start_time = time.time()
        backend = lb.get_backend(lb.current_policy)
        if not backend:
            lb.increment_dropped_requests()
            return {"error": "No available backends"}, 503
        logging.info("Selected backend: %s", backend) # Remove this log when submitting

        lb.backend_request_count[backend] += 1
        response = requests.post(backend, data=datadict, files=filedict)
        latency = time.time() - start_time

        if response.status_code == 200:
            logging.info("Request forwarded successfully")
            lb.response_time_history.setdefault(backend, [])
            lb.response_time_history[backend].append(latency)

            MAX_SAMPLES = 10
            if len(lb.response_time_history[backend]) > MAX_SAMPLES:
                lb.response_time_history[backend].pop(0)
            
            # Kept to check validity of end user response - remove when submitting
            # if output:
            #     output_path = "/app/data/" + output
            #     with open(output_path, "wb") as fh:
            #         fh.write(response.content)
        
        # logging.info("Forwarded request to backend: %s", backend)
        # logging.info("Total requests handled: %d", lb.total_requests)
        # logging.info("Requests sent to backends: %s", lb.backend_request_count)
        
        return Response(content=response.content, media_type="application/octet-stream", status_code=response.status_code)
    finally:
        lb.backend_request_count[backend] -= 1
    except Exception as e:
        # lb.increment_failed_requests()
        # lb.increment_dropped_requests()
        logging.error("Failed to forward request: %s", e)
        return {"error": "Failed to forward request"}, 500


@app.get("/algo")
async def get_algo():
    logging.info("Fetching current rounting protocol")
    return {"policy": lb.current_policy}, 200

@app.get("/change")
async def change_algo():
    logging.info("Changing routing policy")
    try:
        if lb.current_policy == "round_robin":
            lb.current_policy = "state_aware"
        else:
            lb.current_policy = "round_robin"
        return {"policy": lb.current_policy}, 200
    except Exception as e:
        logging.error("Unable to change routing policy: %s", e)
        return {"error": "failed to change policy"}, 500


if __name__ == "__main__":
    logging.info("Starting Load Balancer")
    uvicorn.run(app, host="0.0.0.0", port=8100)
