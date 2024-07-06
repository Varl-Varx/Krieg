from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
import stripe
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['STRIPE_SECRET_KEY'] = 'your_stripe_secret_key'
app.config['STRIPE_PUBLIC_KEY'] = 'your_stripe_public_key'

socketio = SocketIO(app)
db = SQLAlchemy(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
stripe.api_key = app.config['STRIPE_SECRET_KEY']

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    resources = db.Column(db.Integer, default=100)
    gold = db.Column(db.Integer, default=0)
    expansion_packs = db.Column(db.Integer, default=0)
    game_currency = db.Column(db.Integer, default=1000)

class Territory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resources = db.Column(db.Integer, default=100)
    military_strength = db.Column(db.Integer, default=50)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(email=data['email'], password=hashed_password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Login successful', 'user_id': user.id})
    return jsonify({'message': 'Login failed'})

@app.route('/buy_gold', methods=['POST'])
def buy_gold():
    data = request.get_json()
    user = User.query.get(data['user_id'])
    try:
        charge = stripe.PaymentIntent.create(
            amount=500,  # $5.00
            currency='usd',
            payment_method=data['payment_method_id'],
            confirmation_method='manual',
            confirm=True,
        )
        user.gold += 10  # Add 10 gold for $5.00
        db.session.commit()
        return jsonify({'message': 'Payment successful', 'gold': user.gold})
    except stripe.error.StripeError as e:
        return jsonify({'message': 'Payment failed', 'error': str(e)})

@app.route('/buy_expansion', methods=['POST'])
def buy_expansion():
    data = request.get_json()
    user = User.query.get(data['user_id'])
    try:
        charge = stripe.PaymentIntent.create(
            amount=1000,  # $10.00
            currency='usd',
            payment_method=data['payment_method_id'],
            confirmation_method='manual',
            confirm=True,
        )
        user.expansion_packs += 1  # Add 1 expansion pack for $10.00
        db.session.commit()
        return jsonify({'message': 'Payment successful', 'expansion_packs': user.expansion_packs})
    except stripe.error.StripeError as e:
        return jsonify({'message': 'Payment failed', 'error': str(e)})

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('message', {'msg': username + ' has entered the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('message', {'msg': username + ' has left the room.'}, room=room)

@socketio.on('attack')
def on_attack(data):
    attacker_id = data['attacker_id']
    defender_id = data['defender_id']
    territory_id = data['territory_id']
    territory = Territory.query.get(territory_id)
    attacker = User.query.get(attacker_id)
    defender = User.query.get(defender_id)
    if attacker and defender and territory:
        if territory.military_strength < attacker.military_strength:
            territory.owner_id = attacker_id
            territory.military_strength = attacker.military_strength - territory.military_strength
            db.session.commit()
            emit('territory_conquered', {'territory_id': territory_id, 'new_owner': attacker_id}, broadcast=True)
        else:
            emit('message', {'msg': 'Attack failed'}, room=data['room'])

@socketio.on('update_resources')
def update_resources(data):
    user = User.query.get(data['user_id'])
    user.resources += data['amount']
    db.session.commit()
    emit('resource_update', {'user_id': user.id, 'resources': user.resources}, broadcast=True)

if __name__ == '__main__':
    db.create_all()
    socketio.run(app, debug=True)
