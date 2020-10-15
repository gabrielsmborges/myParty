# myParty
# Project created by : gabrielsmborges
# CS50 Final Project
# https://github.com/gabrielsmborges
# 2020


from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from functools import wraps
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from random import randint, choice
import string
import json
from dateutil.relativedelta import relativedelta


app = Flask(__name__)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///data.db")


def erasePastParties():
    """The program will erase every party 24h after it's determined date"""
    dayafter = datetime.now() + timedelta(days=1)
    codes = db.execute(
        'SELECT code FROM parties WHERE date_hour < ?',
        dayafter)
    for el in codes:
        # removing every bring element related to the party
        db.execute('DELETE FROM bring WHERE party_id = ?', el['code'])
        # removing every guest invited to the party
        db.execute('DELETE FROM guests WHERE party_code = ?', el['code'])
        # removing party from party table
        db.execute('DELETE FROM parties WHERE code = ?', el['code'])
        # removing every requirement element related to the party
        db.execute('DELETE FROM requirements WHERE party_code = ?', el['code'])


def login_required(func):
    """Some routes need the user login"""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return func(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def index():
    """ Every time someone logs in the server will look for past parties in order to delete them """
    erasePastParties()
    return redirect('/home')


@app.route('/register', methods=["GET", "POST"])
def register():
    """Registering a new user"""
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
        rows = db.execute(
            "SELECT username FROM users WHERE username = ?",
            username)
        if len(rows) != 0:
            flash('Username taken')
            return redirect('/register')
        db.execute(
            "INSERT INTO users (username, name, last_names, birth, hash) VALUES (?, ?, ?, ?, ?);",
            username,
            name,
            last_name,
            birthday,
            generate_password_hash(password))
        flash("Registered !")
        return redirect('/')


@app.route('/login', methods=["GET", "POST"])
def logger():
    """Login the user in"""
    session.clear()

    if request.method == "GET":
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        data = db.execute(
            'SELECT username, hash FROM users WHERE username = ?',
            username)
        if len(data) != 1 or not check_password_hash(
                data[0]["hash"], password):
            flash("ERROR")
            return redirect('/')
        session["user_id"] = db.execute(
            'SELECT id FROM users WHERE username = ?',
            username)[0]["id"]
        flash('Logged In')
        return redirect('/home')


@app.route('/home')
@login_required
def home():
    """Passing the invitations and parties data in order to create some tabnles in the homescreen"""
    names = db.execute(
        'SELECT name, last_names FROM users WHERE id = ?',
        session["user_id"])[0]
    parties = db.execute(
        'SELECT * FROM parties WHERE host_id = ?',
        session['user_id'])
    invitations = db.execute(
        'SELECT * FROM guests WHERE guest_id = ?',
        session['user_id'])
    return render_template(
        'home.html',
        name=f"{names['name']} {names['last_names']}",
        parties=parties,
        len_parties=len(parties),
        invitations=invitations,
        len_invitations=len(invitations),
        db=db)


@app.route('/create', methods=["GET", "POST"])
@login_required
def create():
    """Creating a new party"""
    if request.method == "GET":
        return render_template('create.html')
    else:
        party_name = request.form.get('party_name')
        address = request.form.get('address')
        date = request.form.get('date')
        time = request.form.get('time')
        # Transforming public into Bool
        public = request.form.get('public')
        if public == 'on':
            public = True
        else:
            public = False
        # transforming adult into Bool
        adult = request.form.get('eighteen')
        if adult == 'on':
            adult = True
        else:
            adult = False
        reqList = request.form.get('requirements-list')
        if reqList != "":
            reqList = json.loads(reqList)
        # transforming amount value into float because html returns numeric
        # string
        for el in reqList:
            el['amount'] = float(el['amount'])

        # formatting date into python format
        formatted_date = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

        # Verifying if there is no other pary with the same code
        def validHash():
            val = ''.join([choice(string.digits) for n in range(9)])
            data = db.execute('SELECT name FROM parties WHERE code = ?', val)
            if len(data) != 0:
                validHash()
            else:
                return val

        # Affecting a valid code into has_val variable
        hash_val = validHash()

        # Inserting party data into DB (NO reqirements)
        db.execute(
            'INSERT INTO parties (code, host_id, name, date_hour, address ,public, adult) VALUES (?, ?, ?, ?, ?, ?, ?)',
            hash_val,
            session["user_id"],
            party_name,
            formatted_date,
            address,
            public,
            adult)
        # Inserting party requirements into parties table
        for el in reqList:
            if el['type'] == "money":
                db.execute(
                    'INSERT INTO requirements (party_code, requirement_name, amount, money) VALUES (?, ?, ?, ?)',
                    hash_val,
                    "money",
                    el['amount'],
                    True)
            else:
                db.execute(
                    'INSERT INTO requirements (party_code, requirement_name, amount, money) VALUES (?, ?, ?, ?)',
                    hash_val,
                    el['name'],
                    el['amount'],
                    False)
        return redirect('/')


@app.route('/myparties')
@login_required
def myparties():
    """Showing all the parties created by the user"""
    parties = db.execute(
        'SELECT * FROM parties WHERE host_id = ? ORDER BY date_hour DESC',
        session['user_id'])
    return render_template(
        'myparties.html',
        parties=parties,
        db=db,
        datetime=datetime)


@app.route('/invite', methods=["GET", "POST"])
@login_required
def invite():
    """Invite someone to a party created by the user"""
    if request.method == "GET":
        return redirect('/')
    else:
        party_code = request.form.get('party-code')
        return render_template('invite.html', code=party_code)


@app.route('/inviteuser', methods=['GET', 'POST'])
@login_required
def inviteuser():
    """ Inviting a guest to the user party """
    if request.method == "GET":
        return redirect('/myparties')
    else:
        code = request.form.get('code')
        party_data = db.execute('SELECT * FROM parties WHERE code = ?', code)
        username = request.form.get('username')
        guest_data = db.execute(
            'SELECT * FROM users WHERE username = ?', username)
        #User is not found
        if len(guest_data) < 1:
            return "User not found"
        # If the username corresponds to the organizer of the party
        if guest_data[0]['id'] == session['user_id']:
            return "You cannot invite yourself"

        guest_birth = datetime.strptime(
            guest_data[0]['birth'], "%Y-%m-%d %H:%M:%S")
        guest_age = relativedelta(datetime.now(), guest_birth).years

        # If the user tries to invite a -18 person to a adult party
        if party_data[0]['adult'] and guest_age < 18:
            return f"{username} can't be invited because your party is for adult only."
        db.execute(
            'INSERT INTO guests (party_code, guest_id, confirmed) VALUES (?, ?, ?)',
            code,
            guest_data[0]['id'],
            False)
        flash(f"{username} invited!")
        return redirect('/myparties')


@app.route('/invitations')
@login_required
def invitations():
    """ Displaying all the invitations that the user have """
    invitations = db.execute(
        'SELECT * FROM guests WHERE guest_id = ?',
        session['user_id'])
    return render_template('invitations.html', invitations=invitations, db=db)


@app.route('/logout')
@login_required
def logout():
    """ Clearing the session and returning the / route in order to logout"""
    session.clear()
    return redirect('/')


@app.route('/accept_invitation', methods=['GET', 'POST'])
@login_required
def accept_invitation():
    """ Accept or not a party invitaion """
    if request.method == "GET":
        return redirect('/')
    else:
        action = request.form.get('action')
        if action == "accept":
            element = request.form.get('element')
            party_code = request.form.get('party_code')
            db.execute(
                'UPDATE guests SET confirmed = ? WHERE guest_id = ?',
                True,
                session['user_id'])
            db.execute(
                'INSERT INTO bring (guest_id, party_id, element) VALUES (?, ?, ?)',
                session['user_id'],
                party_code,
                element)
            flash(
                f"Confirmed in {db.execute('SELECT name FROM parties WHERE code = ?' , party_code)[0]['name']}!")
            return redirect('/invitations')
        else:
            party_code = request.form.get('party_code')
            db.execute(
                'DELETE FROM guests WHERE guest_id = ? AND party_code = ?',
                session['user_id'],
                party_code)
            flash(
                f"Removed from {db.execute('SELECT name FROM parties WHERE code = ?' , party_code)[0]['name']}!")
            return redirect('/invitations')


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """ Searching parties by their code """
    if request.method == "GET":
        return render_template('search.html')
    else:
        code = request.form.get('party_code')
        party_query = db.execute(
            'SELECT * FROM parties WHERE code = ? AND public = ?',
            code,
            True)[0]
        if len(party_query) == 0:
            flash('Party not found or not public.')
            return redirect('/search')
        else:
            return render_template('search.html', data=party_query, db=db)


@app.route('/publicparticipate', methods=['GET', 'POST'])
@login_required
def publicparticipate():
    """ User request to participate in a public party """
    if request.method == "GET":
        return('/search')
    else:
        # If someone how's not an dult wants to got to an adult party
        birth = datetime.strptime(
            db.execute(
                'SELECT birth FROM users WHERE id = ?',
                session['user_id'])[0]['birth'],
            "%Y-%m-%d %H:%M:%S")
        age = relativedelta(datetime.now(), birth).years
        data = json.loads(request.form.get('data').replace("'", '"'))
        if data['adult'] and age < 18:
            flash('This party is only for 18+ persons, you can not participate :(')
            return redirect('/search')
        bring = request.form.get('bring')
        db.execute(
            'INSERT INTO guests (party_code, guest_id, confirmed) VALUES (?, ?, ?)',
            data['code'],
            session['user_id'],
            True)
        db.execute(
            'INSERT INTO bring (guest_id, party_id, element) VALUES (?, ?, ?)',
            session['user_id'],
            data['code'],
            bring)
        flash('Participation confirmed!')
        return redirect('/')

# Cancel a party
@app.route('/cancelparty', methods=["GET", "POST"])
@login_required
def cancelparty():
    if request.method == "GET":
        return redirect('/myparties')
    else:
        party_code = request.form.get('party_code')
        # Removing everything that is related to the party that will be deleted
        flash(f'{db.execute("SELECT name FROM parties WHERE code = ?", party_code)[0]["name"]} deleted!')
        # Removing elements from bring table related to party
        db.execute('DELETE FROM bring WHERE party_id = ?', party_code)
        # Removing guests from the party
        db.execute('DELETE FROM guests WHERE party_code = ?', party_code)
        # Removing party from parties table
        db.execute('DELETE FROM parties WHERE code = ?', party_code)
        # Removing every requirement from requirements table that is related to party
        db.execute('DELETE FROM requirements WHERE party_code = ?', party_code)
        return redirect('/')

# 404 Handler
@app.errorhandler(404)
def invalid_route(e):
    return render_template('404.html')