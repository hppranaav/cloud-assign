
FROM python:3.9-slim

WORKDIR /app

COPY load-balancer/load_balancer.py /app

RUN pip install --no-cache-dir uvicorn fastapi requests psutil python-multipart

EXPOSE 8100

CMD ["python3", "load_balancer.py"]
