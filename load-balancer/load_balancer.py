import requests
from fastapi import FastAPI, Request, Form, Response, HTTPException
import uvicorn
import subprocess
import logging
import psutil
import time
from pathlib import Path
from threading import Lock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
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
        self.policy_switch_count = 0
        self.current_policy = "round_robin"
        self.response_time_history = {}
        self.lock = Lock()
        logging.info("Initializing LoadBalancer")
        self.get_gateway_ip()
        self.update_backends()

    def get_gateway_ip(self):
        global gateway_ip
        try:
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

    # Update the list of backends by querying the scaling controller
    def update_backends(self):
        global BACKENDS
        try:
            logging.info("Updating backends")

            result = requests.get(gateway_ip)
            if result.status_code != 200:
                logging.error(f"Failed to get container list: {result.text}")
                return

            containers = result.json().get("containers", [])
            BACKENDS = [f"http://{c}:8080/watermark" for c in containers]

            for backend in list(self.backend_request_count.keys()):
                if backend not in BACKENDS:
                    del self.backend_request_count[backend]

            for backend in BACKENDS:
                self.backend_request_count.setdefault(backend, 0)

            logging.info("Updated BACKENDS: %s", BACKENDS)
        except Exception as e:
            logging.error("Failed to update backends: %s", e)

    # Round robin algorithm
    def round_robin(self):
        with self.lock:
            backend = BACKENDS[self.index % len(BACKENDS)]
            self.index += 1
        return backend

    # Least response time + active connections
    def state_aware(self):
        self.update_backends()
        DEFAULT_LATENCY = 0.2
        metrics = []
        for backend in BACKENDS:
            latencies = self.response_time_history.get(backend, [DEFAULT_LATENCY])
            avg_latency = sum(latencies) / len(latencies)
            active_conn = self.backend_request_count.get(backend, 0)
            metrics.append((avg_latency + active_conn * 0.1, backend))

        metrics.sort()
        return metrics[0][1] if metrics else self.round_robin()

    def get_backend(self):
        if self.current_policy == "state_aware":
            return self.state_aware()
        return self.round_robin()

lb = LoadBalancer()

# Load balancer logic
@app.post("/route")
async def route(data: str = Form(...), file: str = Form(...)):
    filepath = "/app/data/" + file

    if not Path(filepath).is_file():
        logging.error("File does not exist: %s", file)
        raise HTTPException(status_code=400, detail="File not found")

    with Path(filepath).open("rb") as f:
        files = {'image': (file, f, "image/jpeg")}
        start_time = time.time()
        backend = lb.get_backend()
        lb.backend_request_count[backend] += 1
        try:
            response = requests.post(backend, data={"watermark-size": data}, files=files)
            latency = time.time() - start_time
            lb.response_time_history.setdefault(backend, []).append(latency)
            if len(lb.response_time_history[backend]) > 10:
                lb.response_time_history[backend].pop(0)
            if response.status_code != 200:
                lb.failed_requests += 1
            return Response(content=response.content, media_type="image/jpeg", status_code=response.status_code)
        except Exception as e:
            lb.dropped_requests += 1
            logging.error("Failed to forward request: %s", e)
            raise HTTPException(status_code=503, detail="Backend unavailable")
        finally:
            lb.backend_request_count[backend] -= 1

@app.get("/algo")
def get_algo():
    return {"policy": lb.current_policy}

@app.post("/change")
def change_algo(data: dict):
    algo = data.get('algorithm')
    if algo not in ['round_robin', 'state_aware']:
        raise HTTPException(status_code=400, detail="Invalid algorithm")
    lb.current_policy = algo
    return {"new_policy": lb.current_policy}

@app.get("/metrics")
def metrics():
    return {
        "policy": lb.current_policy,
        "total_requests": lb.total_requests,
        "failed_requests": lb.failed_requests,
        "dropped_requests": lb.dropped_requests,
        "backends": [
            {
                "url": backend,
                "avg_latency": sum(lb.response_time_history.get(backend, [0])) / max(1, len(lb.response_time_history.get(backend, []))),
                "active_connections": lb.backend_request_count.get(backend, 0),
            }
            for backend in BACKENDS
        ]
    }

if __name__ == "__main__":
    logging.info("Starting Load Balancer")
    uvicorn.run(app, host="0.0.0.0", port=8100)
