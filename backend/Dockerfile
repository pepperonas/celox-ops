FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    weasyprint \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Geschaeftszeitzone als Default (compose setzt sie zusaetzlich). tzdata ist
# explizit installiert, damit sie nicht nur als Nebenprodukt anderer Pakete
# vorhanden ist — ohne Zoneinfo faellt TZ still auf UTC zurueck.
ENV TZ=Europe/Berlin

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/invoices /data/assets

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
