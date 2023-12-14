from flask import Flask, render_template, request, redirect, url_for, flash,session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, UserMixin, login_required, current_user
from flask_socketio import SocketIO, emit
from sqlalchemy import or_  


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)
app.config['SECRET_KEY'] = 'AJ94c36aUhnp5ACooY7X6kIc4qgVubLY'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def get_id(self):
        return str(self.sno)

from datetime import datetime

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.sno'))
    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Add this line for timestamp


ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

class Questions(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(250), nullable=False, unique=True)
    year = db.Column(db.Integer, nullable=True)
    topic = db.Column(db.String(300))

with app.app_context():
    db.create_all()



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_user_id():
    return session.get('user_id', None)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)

            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Incorrect username or password!')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. You are not an admin.')
        return redirect(url_for('home'))

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        year = request.form.get('year')
        topic = request.form.get('topic')

        new_question = Questions(question=question_text, year=year, topic=topic)
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!')

    return render_template('admin_dashboard.html')

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        target_word = request.form.get('target_word')
        search_results = Questions.query.filter(or_(Questions.question.ilike(f"%{target_word}%"),
                                                     Questions.topic.ilike(f"%{target_word}%"))).all()

        return render_template('home.html', search_results=search_results)

    return render_template('home.html', search_results=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('User already exists!')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

    return render_template('register.html')



@app.route('/messages')
@login_required
def messages():
    # Fetch all messages from the database
    messages = Message.query.all()
    return render_template('messages.html', messages=messages)

@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    if request.method == 'POST':
        message_content = request.form.get('message_content')

        if message_content:
            # Save the broadcast message to the database
            new_message = Message(content=message_content, user=current_user)
            db.session.add(new_message)
            db.session.commit()

            # Broadcast the message to all clients
            socketio.emit('broadcast_message', {
                'content': message_content,
                'sender_username': current_user.username,
                'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }, namespace='/', broadcast=True)

            flash('Message broadcasted successfully!')

    return render_template('broadcast.html')



@socketio.on('broadcast_message')
def handle_broadcast_message(data):
    user_id = get_user_id()

    if user_id:
        sender = User.query.get(user_id)
        content = data.get('content')

        if content:
            # Save the broadcast message to the database
            new_broadcast_message = Message(content=content, user=sender)
            db.session.add(new_broadcast_message)
            db.session.commit()

            # Broadcast the message to all connected clients
            socketio.emit('broadcast_message', {
                'content': content,
                'sender_username': sender.username,
                'timestamp': new_broadcast_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }, namespace='/', broadcast=True)

    if user_id:
        sender = User.query.get(user_id)
        content = data.get('content')

        if content:
            # Save the broadcast message to the database
            new_broadcast_message = Message(content=content, sender=sender, recipient_id=None)
            db.session.add(new_broadcast_message)
            db.session.commit()

            # Broadcast the message to all connected clients
            socketio.emit('broadcast_message', {
                'content': content,
                'sender_username': sender.username,
                'timestamp': new_broadcast_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }, namespace='/', broadcast=True)
    else:
        emit('error', {'message': 'Invalid user'}, namespace='/')




if __name__ == "__main__":
    socketio.run(app, port="1908", debug=True)
