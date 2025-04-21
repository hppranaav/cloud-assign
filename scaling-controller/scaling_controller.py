import subprocess
import threading
import time
import os
import logging
from datetime import datetime
import subprocess
from fastapi import FastAPI, HTTPException, APIRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='container_api.log'
)
logger = logging.getLogger(__name__)

app = FastAPI()
# At the top of your file or inside __main__
# os.environ["CONTAINER_HOST"] = "unix:///run/podman/podman.sock"

NETWORK_NAME = "mynet"
WEBAPP_IMAGE = "webapp"
MIN_CONTAINERS = 1
MAX_CONTAINERS = 5
current_algorithm = "sliding_window"
cpu_history = []
window_size = 5
scale_up_threshold = 75
scale_down_threshold = 30
lock = threading.Lock()

# Utility functions
def get_running_containers():
    result = subprocess.run(["podman", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
    containers = [c for c in result.stdout.strip().split('\n') if c.startswith("webapp")]
    return containers

def container_stats():
    result = subprocess.run(
        ["podman", "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}}"],
        capture_output=True,
        text=True
    )
    stats = {}
    logger.info(f"Found results:\n{result.stdout}")
    for line in result.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) != 2:
            continue  # Skip malformed lines
        name, cpu = parts
        if name.startswith("webapp"):
            try:
                stats[name] = float(cpu.replace('%', ''))
            except ValueError:
                logger.warning(f"Could not parse CPU for {name}: '{cpu}'")
    return stats


def container_stats_old():
    result = subprocess.run(["podman", "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}}"], capture_output=True, text=True)
    stats = {}
    logger.info(f"Found results:{result}")
    for line in result.stdout.strip().split('\n'):
        name, cpu = line.split()
        if name.startswith("webapp"):
            stats[name] = float(cpu.replace('%', ''))
    return stats

def start_container():
    containers = get_running_containers()
    new_id = max([int(c.replace('webapp', '')) for c in containers] + [0]) + 1
    new_name = f"webapp{new_id}"
    subprocess.run([
        "podman", "run", "-d", "--name", new_name,
        "--network", NETWORK_NAME,
        "-v", "/materials-assignment1/function/data/watermarks:/app/data:z",
        WEBAPP_IMAGE
    ], check=True)
    return new_name

def stop_container(name):
    subprocess.run(["podman", "stop", name], check=True)
    subprocess.run(["podman", "rm", name], check=True)

# Scaling Algorithms
def sliding_window_decision():
    global cpu_history
    stats = container_stats()
    avg_cpu = sum(stats.values()) / len(stats) if stats else 0

    cpu_history.append(avg_cpu)
    if len(cpu_history) > window_size:
        cpu_history.pop(0)

    avg_window_cpu = sum(cpu_history) / len(cpu_history)

    containers = get_running_containers()
    if avg_window_cpu > scale_up_threshold and len(containers) < MAX_CONTAINERS:
        start_container()
    elif avg_window_cpu < scale_down_threshold and len(containers) > MIN_CONTAINERS:
        stop_container(containers[-1])

def regression_decision():
    stats = container_stats()
    avg_cpu = sum(stats.values()) / len(stats) if stats else 0

    containers = get_running_containers()
    desired_containers = int(avg_cpu / 50) + 1

    if desired_containers > len(containers) and len(containers) < MAX_CONTAINERS:
        start_container()
    elif desired_containers < len(containers) and len(containers) > MIN_CONTAINERS:
        stop_container(containers[-1])

# Background autoscaling loop
def autoscale_loop():
    while True:
        with lock:
            if current_algorithm == "sliding_window":
                sliding_window_decision()
            elif current_algorithm == "regression":
                regression_decision()
        time.sleep(5)

threading.Thread(target=autoscale_loop, daemon=True).start()

# API endpoints
# @app.get("/containers")
# def list_containers():
#     return {"containers": get_running_containers()}
@app.get("/containers")
def list_containers():
    """List all webapp containers with Podman."""
    try:
        logger.info("Attempting to list containers...")
        
        # Execute Podman command
        result = subprocess.run(
            ["podman", "ps", "--format", "{{.Names}}"],
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Filter and log results
        containers = [c for c in result.stdout.strip().split('\n') if c.startswith("webapp")]
        logger.info(f"Found {len(containers)} webapp containers: {containers}")
        
        return {"containers": containers}
        
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Podman command failed!\n"
            f"Command: {e.cmd}\n"
            f"Exit Code: {e.returncode}\n"
            f"Error Output: {e.stderr.strip()}"
        )
        return {"error": e.stderr}, 500
        
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
        return {"error": "Internal server error" + str(e)}, 500


@app.post("/scale")
def scale_manual(action: str, count: int = 1):
    if action not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Invalid scale action")
    with lock:
        containers = get_running_containers()
        if action == "up":
            for _ in range(min(count, MAX_CONTAINERS - len(containers))):
                start_container()
        else:
            for _ in range(min(count, len(containers) - MIN_CONTAINERS)):
                stop_container(containers.pop())
    return {"status": "success", "action": action, "total_containers": len(get_running_containers())}

@app.get("/status")
def get_status():
    return {
        "algorithm": current_algorithm,
        "container_count": len(get_running_containers())
    }

@app.post("/algorithm")
def set_algorithm(algo: dict):
    global current_algorithm
    new_algo = algo.get("algorithm")
    if new_algo not in ["regression", "sliding_window"]:
        raise HTTPException(status_code=400, detail="Invalid algorithm name")
    current_algorithm = new_algo
    return {"current_algorithm": current_algorithm}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
