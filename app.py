import os, sqlite3, re, jwt
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    send_file, redirect, url_for, abort
)
from ics import Calendar, Event
from io import BytesIO

app = Flask(__name__)

# секрет для перевірки JWT, який підписує Supabase
JWT_SECRET = os.environ['SUPABASE_JWT_SECRET']
JWT_ALGORITHM = 'HS256'

def init_db():
    conn = sqlite3.connect('bookings.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings
                    (id INTEGER PRIMARY KEY, date TEXT, time TEXT,
                     name TEXT, email TEXT)''')
    conn.commit(); conn.close()

@app.before_first_request
def setup():
    init_db()

def get_current_user():
    auth = request.headers.get('Authorization', None)
    if not auth or not auth.startswith('Bearer '):
        return None
    token = auth.split(' ',1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return abort(401)
        return f(user, *args, **kwargs)
    return wrapper

@app.route('/')
def index():
    # передаємо ключі в шаблон
    return render_template('index.html',
        supabase_url=os.environ['SUPABASE_URL'],
        supabase_anon=os.environ['SUPABASE_ANON_KEY']
    )

@app.route('/api/bookings')
@login_required
def api_bookings(user):
    conn = sqlite3.connect('bookings.db'); c = conn.cursor()
    c.execute('SELECT date, time, name, email, id FROM bookings')
    rows = c.fetchall(); conn.close()
    evs = []
    for date, time, name, email, bid in rows:
        parts = re.split(r'[–-]', time)
        start, end = parts[0].strip(), parts[1].strip()
        evs.append({
          'id': bid,
          'title': name,
          'start': f"{date}T{start}",
          'end':   f"{date}T{end}",
          'color': email == user['email'] and 'blue' or 'gray',
          'extendedProps': {'email': email, 'time': time}
        })
    return jsonify(evs)

@app.route('/book', methods=['POST'])
@login_required
def book(user):
    data = request.get_json()
    date, time = data['date'], data['time']
    name, email = data['name'], user['email']
    # перевірка накладення
    new_s, new_e = [datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
                    for t in re.split(r'[–-]', time)]
    conn = sqlite3.connect('bookings.db'); c = conn.cursor()
    c.execute('SELECT time FROM bookings WHERE date=?', (date,))
    for (et,) in c.fetchall():
        es, ee = [datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
                  for t in re.split(r'[–-]', et)]
        if new_s < ee and new_e > es:
            conn.close(); return 'taken',400
    c.execute('INSERT INTO bookings(date,time,name,email) VALUES(?,?,?,?)',
              (date, time, name, email))
    conn.commit(); conn.close()
    return 'ok'

@app.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel(user, booking_id):
    conn = sqlite3.connect('bookings.db'); c = conn.cursor()
    c.execute('SELECT email FROM bookings WHERE id=?', (booking_id,))
    row = c.fetchone()
    if not row or row[0] != user['email']:
        conn.close(); return abort(403)
    c.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    conn.commit(); conn.close()
    return '',204

@app.route('/export_ics')
@login_required
def export_ics(user):
    date, time, name = request.args['date'], request.args['time'], request.args['name']
    parts = re.split(r'[–-]', time)
    start, end = parts[0].strip(), parts[1].strip()
    fmt = "%Y-%m-%d %H:%M"
    dt_s = datetime.strptime(f"{date} {start}", fmt)
    dt_e = datetime.strptime(f"{date} {end}",   fmt)
    cal = Calendar(); e=Event()
    e.name, e.begin, e.end = f"Альтанка — {name}", dt_s, dt_e
    buf=BytesIO(str(cal).encode()); buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name='booking.ics', mimetype='text/calendar')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
