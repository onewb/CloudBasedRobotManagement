FROM python:3.10-slim

ENV PYTHONWARNINGS="ignore::FutureWarning"

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "app.py"]