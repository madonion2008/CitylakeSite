from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from ics import Calendar, Event
from datetime import datetime
import re
from io import BytesIO

app = Flask(__name__)

# Ініціалізація бази даних
def init_db():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY,
            date TEXT,
            time TEXT,
            name TEXT,
            contact TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/bookings')
def get_bookings():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('SELECT date, time FROM bookings')
    rows = c.fetchall()
    conn.close()
    events = [
        {
            'title': 'Зайнято',
            'start': f"{row[0]}T{row[1].split('–')[0]}",
            'end':   f"{row[0]}T{row[1].split('–')[1]}",
            'allDay': False
        }
        for row in rows
    ]
    return jsonify(events)

@app.route('/book', methods=['POST'])
def book():
    data    = request.get_json() or request.form
    date    = data.get('date')
    time    = data.get('time')  # "15:00–18:00" або "15:00-18:00"
    name    = data.get('name')
    contact = data.get('contact')

    conn = sqlite3.connect('bookings.db')
    c    = conn.cursor()
    # Перевірка конфлікту
    c.execute('SELECT COUNT(*) FROM bookings WHERE date=? AND time=?', (date, time))
    if c.fetchone()[0] > 0:
        conn.close()
        return 'taken', 400

    # Запис бронювання
    c.execute(
        'INSERT INTO bookings(date, time, name, contact) VALUES (?, ?, ?, ?)',
        (date, time, name, contact)
    )
    conn.commit()
    conn.close()
    return 'ok'

@app.route('/export_ics')
def export_ics():
    date    = request.args.get('date')
    time    = request.args.get('time')
    name    = request.args.get('name')
    contact = request.args.get('contact')

    # Розбиваємо час за дефісом чи en-dash
    parts = re.split(r'[–-]', time)
    if len(parts) < 2:
        return 'Invalid time format', 400
    start_time, end_time = parts[0].strip(), parts[1].strip()

    # Генерація ICS з правильними datetime
    cal      = Calendar()
    e        = Event()
    e.name   = f"Альтанка в City Lake — {name}"
    fmt      = "%Y-%m-%d %H:%M"
    dt_start = datetime.strptime(f"{date} {start_time}", fmt)
    dt_end   = datetime.strptime(f"{date} {end_time}",   fmt)
    e.begin  = dt_start
    e.end    = dt_end
    cal.events.add(e)

    buf = BytesIO(str(cal).encode('utf-8'))
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name='booking.ics',
        mimetype='text/calendar'
    )

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
