from cs50 import SQL
from datetime import datetime, timedelta
db = SQL('sqlite:///data.db')

dayafter = datetime.now() + timedelta(days=1)


codes = db.execute('SELECT code FROM parties WHERE date_hour < ?', datetime.now())
for i in codes:
    db.execute('DELETE FROM bring WHERE party_id = ?', i['code'])
    db.execute('DELETE FROM guests WHERE party_code = ?', i['code'])
    db.execute('DELETE FROM parties WHERE code = ?', i['code'])
    db.execute('DELETE FROM requirements WHERE party_code = ?', i['code'])