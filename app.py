import sqlite3
import re
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

# ... інші імпорти та ініціалізація БД

@app.route('/book', methods=['POST'])
def book():
    data    = request.get_json() or request.form
    date    = data.get('date')    # "YYYY-MM-DD"
    time    = data.get('time')    # "HH:MM–HH:MM"
    name    = data.get('name')
    contact = data.get('contact')

    # Розбираємо новий інтервал
    parts = re.split(r'[–-]', time)
    new_start = datetime.strptime(f"{date} {parts[0].strip()}", "%Y-%m-%d %H:%M")
    new_end   = datetime.strptime(f"{date} {parts[1].strip()}", "%Y-%m-%d %H:%M")

    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()

    # Завантажуємо всі існуючі бронювання на цю дату
    c.execute('SELECT time FROM bookings WHERE date=?', (date,))
    for (existing_time,) in c.fetchall():
        ep = re.split(r'[–-]', existing_time)
        exist_start = datetime.strptime(f"{date} {ep[0].strip()}", "%Y-%m-%d %H:%M")
        exist_end   = datetime.strptime(f"{date} {ep[1].strip()}", "%Y-%m-%d %H:%M")
        # Перевіряємо перетин: new_start < exist_end і new_end > exist_start
        if new_start < exist_end and new_end > exist_start:
            conn.close()
            return 'taken', 400

    # Якщо конфліктів немає — додаємо бронювання
    c.execute(
        'INSERT INTO bookings(date, time, name, contact) VALUES(?,?,?,?)',
        (date, time, name, contact)
    )
    conn.commit()
    conn.close()
    return 'ok'
