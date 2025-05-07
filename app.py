
from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from ics import Calendar, Event
from io import BytesIO

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY, date TEXT, time TEXT, name TEXT, contact TEXT)''')
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
    events = [{'title': 'Зайнято',
               'start': f"{row[0]}T{row[1].split('–')[0]}",
               'end': f"{row[0]}T{row[1].split('–')[1]}"} 
              for row in rows]
    return jsonify(events)

@app.route('/book', methods=['POST'])
def book():
    data = request.get_json() or request.form
    date = data.get('date')
    time = data.get('time')
    name = data.get('name')
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
    date = request.args.get('date')
    time = request.args.get('time')
    name = request.args.get('name')
    contact = request.args.get('contact')
    cal = Calendar()
    e = Event()
    e.name = f"Альтанка в City Lake - {name}"
    start_time = time.split('–')[0]
    end_time = time.split('–')[1]
    e.begin = f"{date} {start_time}"
    e.end = f"{date} {end_time}"
    cal.events.add(e)
    buf = BytesIO(str(cal).encode('utf-8'))
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='booking.ics', mimetype='text/calendar')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
