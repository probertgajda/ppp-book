from flask_assets import Environment, Bundle
from flask import render_template, redirect, url_for, request, flash, g
import os.path, sqlite3, socket, struct, re
from app import app

def getDatabase():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connectToDatabase()
    return db

def connectToDatabase():
    return sqlite3.connect('book.db')

def queryDatabase(query, args=(), one=False):
    cur = getDatabase().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def initializeDatabase():
    with app.app_context():
        db = getDatabase()
        with app.open_resource('../schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def ip2long(ip):
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]

def checkIfEntryPossibleForIp(ip):
    result = queryDatabase("SELECT id FROM book WHERE createdAt > DATETIME('now', '-1 hour') AND ip = ?", [ip2long(ip)], True)
    return result == None

@app.before_request
def initialize():
    # Assets
    assets = Environment(app)
    js = Bundle(
        'vendor/jquery/jquery.min.js',
        'vendor/bootstrap/js/bootstrap.bundle.min.js',
        'vendor/jquery-easing/jquery.easing.min.js',
        'vendor/magnific-popup/jquery.magnific-popup.min.js',
        'js/jqBootstrapValidation.min.js',
        'js/contact_me.js',
        'js/freelancer.min.js',
        output='gen/packed.js')
    css = Bundle(
        'vendor/bootstrap/css/bootstrap.min.css',
        'vendor/font-awesome/css/font-awesome.min.css',
        'vendor/magnific-popup/magnific-popup.css',
        'css/freelancer.min.css',
        'css/custom.css',
        output='gen/packed.css')
    assets.register('js_all', js)
    assets.register('css_all', css)

    # Initialize database if necessary
    if not os.path.isfile('book.db'):
        initializeDatabase()


@app.teardown_appcontext
def teardown_context(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/', methods=["GET", "POST"])
@app.route('/index')
def index():
    data = []
    if request.method == 'POST':
        data = request.form
        EMAIL_REGEX = re.compile(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")
        if (len(data['name']) > 0 and len(data['email']) > 0 and len(data['message']) > 0 and EMAIL_REGEX.match(
                data['email'])):
            if checkIfEntryPossibleForIp(request.remote_addr):
                db = getDatabase()
                db.execute("INSERT INTO book (firstName, email, phone, content, ip) VALUES (?, ?, ?, ?, ?)",
                    [
                        data['name'],
                        data["email"],
                        data["phone"],
                        data["message"],
                        ip2long(request.remote_addr)
                    ]
                    )
                db.commit()
                flash(u'Wpis dodany', 'success')
                return redirect(url_for('list'))
            else:
                flash(u'Nie dodano wpisu. Z tego IP niedawno dodano wpis', 'danger')
        else:
            flash(u'Nie dodano wpisu. Popraw dane', 'danger')
    return render_template('index.html', data=data)

@app.route('/list')
def list():
    bookEntries = queryDatabase("SELECT * FROM book ORDER BY createdAt")
    return render_template('list.html', bookEntries=bookEntries)

@app.route('/contact')
def contact():
    return render_template('contact.html')
