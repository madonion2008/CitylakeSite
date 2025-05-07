import os
import sqlite3
import re
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from ics import Calendar, Event
from datetime import datetime
from io import BytesIO

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY, date TEXT, time TEXT, name TEXT, contact TEXT)''')
    conn.commit()
    conn.close()

@app.before_first_request
def initialize():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/bookings')
def get_bookings():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    # вибираємо всі поля
    c.execute('SELECT date, time, name, contact FROM bookings')
    rows = c.fetchall()
    conn.close()

    events = []
    for date, time, name, contact in rows:
        # розбиваємо час на start/end
        parts = re.split(r'[–-]', time)
        start = parts[0].strip()
        end   = parts[1].strip() if len(parts) >= 2 else start

        events.append({
            'title': name,                  # ім'я показуємо як заголовок події
            'start': f"{date}T{start}",
            'end':   f"{date}T{end}",
            'color': 'green',               # фон події
            'extendedProps': {
                'contact': contact,
                'time': time
            }
        })

    return jsonify(events)

@app.route('/book', methods=['POST'])
def book():
    data = request.get_json() or request.form
    date    = data.get('date')
    time    = data.get('time')
    name    = data.get('name')
    contact = data.get('contact')

    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM bookings WHERE date=? AND time=?', (date, time))
    if c.fetchone()[0] > 0:
        conn.close()
        return 'taken', 400

    c.execute('INSERT INTO bookings(date, time, name, contact) VALUES(?,?,?,?)',
              (date, time, name, contact))
    conn.commit()
    conn.close()
    return 'ok'

@app.route('/export_ics')
def export_ics():
    date    = request.args.get('date')
    time    = request.args.get('time')
    name    = request.args.get('name')
    parts   = re.split(r'[–-]', time)
    if len(parts) < 2:
        return 'Invalid time format', 400
    start, end = parts[0].strip(), parts[1].strip()
    fmt = "%Y-%m-%d %H:%M"
    dt_start = datetime.strptime(f"{date} {start}", fmt)
    dt_end   = datetime.strptime(f"{date} {end}",   fmt)

    cal = Calendar()
    e   = Event()
    e.name  = f"Альтанка в City Lake — {name}"
    e.begin = dt_start
    e.end   = dt_end
    cal.events.add(e)

    buf = BytesIO(str(cal).encode('utf-8'))
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name='booking.ics',
                     mimetype='text/calendar')

@app.route('/my_bookings', methods=['GET','POST'])
def my_bookings():
    bookings = None
    contact = None
    if request.method == 'POST':
        contact = request.form.get('contact')
        conn = sqlite3.connect('bookings.db')
        c = conn.cursor()
        c.execute('SELECT id, date, time, name FROM bookings WHERE contact=?', (contact,))
        bookings = c.fetchall()
        conn.close()
    return render_template('my_bookings.html', bookings=bookings, contact=contact)

@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
