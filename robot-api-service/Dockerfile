FROM python:3.10-slim

WORKDIR /app

# Install dependencies FIRST (better caching + reliability)
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Then copy app
COPY . .

CMD ["python", "app.py"]