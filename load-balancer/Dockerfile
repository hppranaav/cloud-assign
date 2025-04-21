# FROM python:3.9-slim

# WORKDIR /app

# COPY . .

# RUN pip install fastapi uvicorn requests

# CMD ["uvicorn", "load_balancer:app", "--host", "0.0.0.0", "--port", "8100"]

# OLD
FROM python:3.9-slim

WORKDIR /app

COPY load-balancer/load_balancer.py /app

RUN pip install --no-cache-dir uvicorn fastapi requests psutil python-multipart

EXPOSE 8100

CMD ["python3", "load_balancer.py"]
