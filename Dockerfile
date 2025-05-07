FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Додаємо цю стрічку, щоб Render побачив порт
EXPOSE 5000

CMD ["python", "app.py"]
