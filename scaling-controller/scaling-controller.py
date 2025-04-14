from fastapi import FastAPI
from fastapi.responses import JSONResponse
import subprocess
import json
import uvicorn

app = FastAPI()

def get_podman_metrics():
    try:
        # Get stats in JSON format
        result = subprocess.run(
            ["podman", "stats", "--no-stream", "--format", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(result.stdout)
        stats = json.loads(result.stdout)
        print(stats)
        metrics = []

        for container in stats:
            metrics.append({
                "id": container.get("id"),
                "name": container.get("name"),
                "status": container.get("Status"),
                "cpu_percent": container.get("cpu_percent"),
                "mem_usage": container.get("mem_usage"),
                "mem_percent": container.get("mem_percent")
            })
        return metrics
    except subprocess.CalledProcessError as e:
        return {"error": "Failed to get container stats", "details": e.stderr}
    except json.JSONDecodeError:
        return {"error": "Failed to parse container stats"}

@app.get("/metrics")
def read_metrics():
    data = get_podman_metrics()
    return JSONResponse(content=data)

# Get list of containers with webapp as name
@app.get("/containers")
def list_containers():
    try:
        result = subprocess.run(
            ["podman", "ps", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        containers = [c for c in result.stdout.strip().splitlines() if "webapp" in c]
        return JSONResponse(content={"containers": containers})
    except subprocess.CalledProcessError as e:
        return JSONResponse(content={"error": "Failed to get container list", "details": e.stderr})

if __name__ == "__main__":
    uvicorn.run("scaling-controller:app", host="0.0.0.0", port=8300, reload=True)
