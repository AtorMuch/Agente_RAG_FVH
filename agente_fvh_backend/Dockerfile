FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Los PDFs del manual FAO deben quedar en /app/knowledge_base/
# (ah472s00.pdf, ah472s01.pdf, ah472s02.pdf, ah472s03.pdf)

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
