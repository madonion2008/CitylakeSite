 from flask import Flask, render_template, request, jsonify, send_file
 import sqlite3
-from ics import Calendar, Event
+from ics import Calendar, Event
 from io import BytesIO

 @app.route('/export_ics')
 def export_ics():
-    date    = request.args.get('date')
-    time    = request.args.get('time')
-    name    = request.args.get('name')
-    contact = request.args.get('contact')
+    date    = request.args.get('date')
+    time    = request.args.get('time')  # може містити "15:00-18:00" або "15:00–18:00"
+    name    = request.args.get('name')
+    contact = request.args.get('contact')

+    # розбиваємо за будь-яким роздільником дефіс/en dash
+    import re
+    parts = re.split(r'[–-]', time)
+    if len(parts) >= 2:
+        start_time = parts[0].strip()
+        end_time   = parts[1].strip()
+    else:
+        # якщо формат несподіваний — повернути помилку
+        return 'Invalid time format', 400

     cal = Calendar()
     e   = Event()
     e.name = f"Альтанка в City Lake - {name}"
-    start_time = time.split('–')[0]
-    end_time   = time.split('–')[1]
     e.begin = f"{date} {start_time}"
     e.end   = f"{date} {end_time}"
     cal.events.add(e)
     buf = BytesIO(str(cal).encode('utf-8'))
     buf.seek(0)
     return send_file(buf,
                      as_attachment=True,
                      download_name='booking.ics',
                      mimetype='text/calendar')
