from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sse import sse
from channel import channel
from flask import Blueprint
import sqlite3
from OpenSSL import SSL

from flask_socketio import SocketIO, send, emit , leave_room , join_room

app = Flask(__name__)

#app.secret_key = "super secret key"
app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'
app.config['SESSION_TYPE'] = 'filesystem'
app.debug = False
app.config["REDIS_URL"] = "redis://localhost"
#from .main import main as main_blueprint
#app.register_blueprint(main_blueprint)
app.register_blueprint(sse, url_prefix='/stream')
app.register_blueprint(channel, url_prefix='/channel')

socketio = SocketIO(app)
socketio.init_app(app)

@app.route('/')
def index():
    return render_template('form.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/process', methods=['POST'])
def process():
    if request.method == 'POST':
        con = sqlite3.connect("skype")
        try:
            username = request.form['username']
            password = request.form['password']

            if username and password:
                # with sqlite3.connect("skype") as con:
                cur = con.cursor()
                cur.execute("INSERT INTO users (username,password) VALUES(?,?)", (username, password))
                con.commit()
                return jsonify({'name': username})
            else:
                return jsonify({'error': 'Missing data!'})
        except:
            con.rollback()
        finally:
            con.close()


@app.route('/addcontact')
def addcontact():
    return render_template('addcontact.html')


@app.route('/loginProcess', methods=['POST'])
def loginProcess():
    if request.method == 'POST':
        con = sqlite3.connect("skype")
        username = request.form['username']
        password = request.form['password']

        if username and password:
            try:
                cur = con.cursor()
                cur.execute("SELECT username, password FROM users")
                users = cur.fetchall()
                user = [i for i in users if i[0] == username]
                if (len(user) > 0):
                    if (str(user[0][1]) == password):
                        session['username'] = username
                        return jsonify({'name': username})
                    else:
                        return jsonify({'error': 'username or password is incorrect!'})
                else:
                    return jsonify({'error': 'username or password is incorrect!'})
                # con.commit()
            except Exception as e:
                return jsonify({'error': 'something went wrong!'})
            finally:
                con.close()



@app.route('/addcontactprocess', methods=['POST'])
def addContactProcess():
    if request.method == 'POST':
        if 'username' in session:
            username = session['username']
            con = sqlite3.connect("skype")
            try:
                contact = request.form['contact']
                if contact:
                    cur = con.cursor()
                    cur.execute("SELECT id,username FROM users")
                    users = cur.fetchall()
                    thisusername = [i for i in users if i[1] == username]
                    thiscontact = [i for i in users if i[1] == contact]
                    myid = thisusername[0][0]
                    toid = thiscontact[0][0]
                    # print(myid)
                    # print(toid)
                    cur.execute("INSERT INTO contacts (fromContact,toContact) VALUES(?,?)", (myid, toid))
                    con.commit()
                    
                    return jsonify({'contact': contact})
                else:
                    return jsonify({'error': 'Missing data!'})
            except:
                print ("Except")
                con.rollback()

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/list')
def list():
    con = sqlite3.connect("skype")
    con.row_factory = sqlite3.Row

    cur = con.cursor()
    cur.execute("select id from users Where username= ? ", [session['username']])
    id = cur.fetchall()[0][0]
    cur.execute("select fromContact,toContact from contacts where fromContact= ?", [id])
    rows = cur.fetchall()
    idlist = [row[1] for row in rows]
    namelist = []
    for id in idlist:
        cur.execute("select username from users where id = ?", [id])
        namelist.append(cur.fetchall()[0][0])
    #print(id)
    #print(rows)
    # return "hello"
    # fetchet_rows = [row for row in rows if (row[0])]
    return render_template("list.html", rows=namelist , myname = session['username'])


@app.route("/wait/<Cid>")
def waitPage(Cid):
    print ("Wait")
    print (Cid)
    return render_template("wait.html", name=Cid)

@app.route("/join/<Cid>")
def joinPage(Cid):
    print ("Join")
    print (Cid)
    return render_template("join.html", name=Cid)



@app.route("/chat/<chatroomname>")
def chat(chatroomname):
    """Chat room. The user's name and room must be stored in
    the session."""
    print("Chat")
    name = session['username']
    #session['chatroomname'] = chatroomname
    session['chatroomname'] = chatroomname 
    room = session['chatroomname']
    #print(room)
   # print("HERE")
   # print(name)
    return render_template('websocket.html', name=name, room=room)

@socketio.on('connect', namespace='/chat')
def test_connect():
    print ("Connected")

@socketio.on('joined', namespace='/chat')
def joined(message):
    print("Joined")
    room = session['chatroomname']
    name = session['username']
    join_room(room)
    emit('status', {'msg': session['username'] + ' added'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    # print("Message is : ")
    # print (message)
    room = session['chatroomname']
    emit('message', {'msg': session['username'] + ':' + message['msg']}, room=room)

@socketio.on('left', namespace='/chat')
def left(message):
    print ("Left")
    room = session['chatroomname']
    leave_room(room)
    emit('status', {'msg': session['username'] + ' left.'}, room=room)


if __name__ == '__main__':
    #socketio.run(app)
    app.run(ssl_context='adhoc',host='0.0.0.0')
