FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY tiktok_proxy.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python3", "tiktok_proxy.py"]
