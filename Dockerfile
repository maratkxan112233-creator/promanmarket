FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Mini App (ilova) web-serveri shu portda tinglaydi. Railway $PORT ni beradi
# (main.py da o'qiladi); bu EXPOSE — hujjat/lokal uchun.
EXPOSE 8080

CMD ["python", "-m", "app.main"]
