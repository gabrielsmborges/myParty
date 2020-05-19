from cs50 import SQL

db = SQL("sqlite:///data.db")

te = db.execute('SELECT * FROM requirements')[0]['money']

print(te == True)