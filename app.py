from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from functools import wraps
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from random import randint, choice
import string
import json


app = Flask(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///data.db")


def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return func(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def index():
    return redirect('/home')
    

@app.route('/register', methods = ["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template('register.html')
    else:
        name = request.form.get('name')
        last_name = request.form.get('last_name')
        birthday = datetime.strptime(request.form.get('birthday'), "%Y-%m-%d")
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Passwords don\'t match')
            return redirect('/register')
        rows = db.execute("SELECT username FROM users WHERE username = ?", username)
        if len(rows) != 0:
            flash('Username taken')
            return redirect('/register')
        db.execute("INSERT INTO users (username, name, last_names, birth, hash) VALUES (?, ?, ?, ?, ?);", username, name, last_name, birthday, generate_password_hash(password))
        flash("Registered !")
        return redirect('/')


@app.route('/login', methods=["GET", "POST"])
def logger():
    session.clear()

    if request.method == "GET":
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        data = db.execute('SELECT username, hash FROM users WHERE username = ?', username)
        if len(data) != 1 or not check_password_hash(data[0]["hash"], password):
            flash("ERROR")
            return redirect('/')
        session["user_id"] = db.execute('SELECT id FROM users WHERE username = ?', username)[0]["id"]
        flash('Logged In')
        return redirect('/home')


@app.route('/home')
@login_required
def home():
    names = db.execute('SELECT name, last_names FROM users WHERE id = ?', session["user_id"])[0]
    parties = db.execute('SELECT * FROM parties WHERE host_id = ?', session['user_id'])
    return render_template('home.html', name = f"{names['name']} {names['last_names']}", parties = parties, len_parties = len(parties))

@app.route('/create', methods=["GET", "POST"])
@login_required
def create():
    if request.method == "GET":
        return render_template('create.html')
    else:
        party_name = request.form.get('party_name')
        address = request.form.get('address')
        date = request.form.get('date')
        time = request.form.get('time')
        #Transforming public into Bool
        public = request.form.get('public')
        if public == 'on':
            public = True
        else:
            public = False
        #transforming adult into Bool
        adult = request.form.get('eighteen')
        if adult == 'on':
            adult = True
        else:
            adult = False
        reqList = json.loads(request.form.get('requirements-list'))
        #transforming amount value into float because html returns numeric string
        for el in reqList:
            el['amount'] = float(el['amount'])
        #formatting date into python format
        formatted_date = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        #Verifying if there is no other pary with the same code
        def validHash():
            val = ''.join([choice(string.digits) for n in range(9)])
            data = db.execute('SELECT name FROM parties WHERE code = ?', val)
            if len(data) != 0:
                validHash()
            else:
                return val
        #Affecting a valid code into has_val variable
        hash_val = validHash()

        #INserting paty data into DB (NO reqirements)
        db.execute('INSERT INTO parties (code, host_id, name, date_hour, public, adult) VALUES (?, ?, ?, ?, ?, ?)', hash_val, session["user_id"], party_name, formatted_date, public, adult)

        for el in reqList:
            if el['type'] == "money":
                db.execute('INSERT INTO requirements (party_code, requirement_name, amount, money) VALUES (?, ?, ?, ?)', hash_val, "money", el['amount'], True)
            else:
                db.execute('INSERT INTO requirements (party_code, requirement_name, amount, money) VALUES (?, ?, ?, ?)', hash_val, el['name'], el['amount'], False)
        return redirect('/')

@app.route('/myparties')
@login_required
def myparties():
    return render_template('myparties.html')

@app.route('/invite')
def invite():
    return render_template('invite.html')