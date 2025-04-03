FROM python:3.9-slim

WORKDIR /app

EXPOSE 8081

COPY materials-assignment1/function/requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY materials-assignment1/function/main.py /app

CMD ["functions-framework", "--target=watermark"]