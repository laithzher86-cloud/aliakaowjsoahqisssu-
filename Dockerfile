FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHROME_BIN=/usr/bin/chromium
ENV OPENBLAS_NUM_THREADS=1
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_MAIN_FREE=1
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
