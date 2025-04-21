FROM python:3.9-slim

WORKDIR /app

EXPOSE 8080

RUN apt-get update && apt-get install -y curl net-tools && apt-get clean && rm -rf /var/lib/apt/lists/*


COPY materials-assignment1/function/requirements.txt /app

RUN mkdir -p /app/data/watermarks

COPY materials-assignment1/function/data/watermarks /app/data/watermarks
# COPY requirements.txt /app
# COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

COPY materials-assignment1/function/main.py /app

CMD ["functions-framework", "--target=watermark"]