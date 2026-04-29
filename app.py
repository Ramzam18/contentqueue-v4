"""
Content Queue - Production Backend
Handles authentication, user data, and Stripe subscriptions
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, create_refresh_token
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import stripe
import json

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///contentqueue.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_...')
STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID', 'price_...')  # $39/month Pro plan

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Subscription info
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    subscription_status = db.Column(db.String(20), default='trial')  # trial, active, canceled, past_due
    trial_ends_at = db.Column(db.DateTime)
    
    # SMS notification settings
    phone_number = db.Column(db.String(20))  # Format: +1XXXXXXXXXX
    sms_enabled = db.Column(db.Boolean, default=False)
    last_sms_sent = db.Column(db.DateTime)  # Prevent spam
    
    # Relationships
    schedule = db.relationship('Schedule', backref='user', uselist=False, cascade='all, delete-orphan')
    completed_tasks = db.relationship('CompletedTask', backref='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'subscription_status': self.subscription_status,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'created_at': self.created_at.isoformat()
        }

class Schedule(db.Model):
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # JSON fields
    weekly_tasks = db.Column(db.Text, default='{}')  # JSON string
    enabled_platforms = db.Column(db.Text, default='[]')  # JSON array
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_weekly_tasks(self):
        return json.loads(self.weekly_tasks) if self.weekly_tasks else {}
    
    def set_weekly_tasks(self, tasks):
        self.weekly_tasks = json.dumps(tasks)
    
    def get_enabled_platforms(self):
        return json.loads(self.enabled_platforms) if self.enabled_platforms else []
    
    def set_enabled_platforms(self, platforms):
        self.enabled_platforms = json.dumps(platforms)

class CompletedTask(db.Model):
    __tablename__ = 'completed_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    date_key = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    task_id = db.Column(db.String(100), nullable=False)  # monday_0, tuesday_1, etc.
    
    completed = db.Column(db.Boolean, default=False)
    missed = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date_key', 'task_id', name='unique_user_task'),
    )

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Create new user account with 14-day trial"""
    data = request.get_json()
    
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create user
    user = User(email=email)
    user.set_password(password)
    user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
    
    # Create empty schedule
    schedule = Schedule(user=user)
    schedule.set_weekly_tasks({})
    schedule.set_enabled_platforms([])
    
    db.session.add(user)
    db.session.add(schedule)
    db.session.commit()
    
    # Create tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login existing user"""
    data = request.get_json()
    
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200

@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = int(get_jwt_identity())
    access_token = create_access_token(identity=user_id)
    return jsonify({'access_token': access_token}), 200

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

# ============================================================================
# SCHEDULE ROUTES
# ============================================================================

@app.route('/api/schedule', methods=['GET'])
@jwt_required()
def get_schedule():
    """Get user's weekly schedule and settings"""
    user_id = int(get_jwt_identity())
    schedule = Schedule.query.filter_by(user_id=user_id).first()
    
    # Auto-create schedule if missing (for users created before /init-db)
    if not schedule:
        schedule = Schedule(user_id=user_id)
        schedule.set_weekly_tasks({})
        schedule.set_enabled_platforms([])
        db.session.add(schedule)
        db.session.commit()
    
    return jsonify({
        'weeklyTasks': schedule.get_weekly_tasks(),
        'enabledPlatforms': schedule.get_enabled_platforms()
    }), 200

@app.route('/api/schedule', methods=['POST'])
@jwt_required()
def update_schedule():
    """Update user's weekly schedule"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    schedule = Schedule.query.filter_by(user_id=user_id).first()
    
    if not schedule:
        schedule = Schedule(user_id=user_id)
        db.session.add(schedule)
    
    if 'weeklyTasks' in data:
        schedule.set_weekly_tasks(data['weeklyTasks'])
    
    if 'enabledPlatforms' in data:
        schedule.set_enabled_platforms(data['enabledPlatforms'])
    
    db.session.commit()
    
    return jsonify({'status': 'saved'}), 200

# ============================================================================
# COMPLETED TASKS ROUTES
# ============================================================================

@app.route('/api/tasks/completed', methods=['GET'])
@jwt_required()
def get_completed_tasks():
    """Get all completed tasks for user"""
    user_id = int(get_jwt_identity())
    
    # Get date range (last 30 days)
    start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    tasks = CompletedTask.query.filter(
        CompletedTask.user_id == user_id,
        CompletedTask.date_key >= start_date
    ).all()
    
    # Group by date
    result = {}
    for task in tasks:
        if task.date_key not in result:
            result[task.date_key] = {}
        
        result[task.date_key][task.task_id] = {
            'completed': task.completed,
            'missed': task.missed,
            'timestamp': task.timestamp.isoformat()
        }
    
    return jsonify({'completedTasks': result}), 200

@app.route('/api/tasks/complete', methods=['POST'])
@jwt_required()
def complete_task():
    """Mark task as completed or missed"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    date_key = data.get('date_key')
    task_id = data.get('task_id')
    completed = data.get('completed', True)
    missed = data.get('missed', False)
    
    if not date_key or not task_id:
        return jsonify({'error': 'date_key and task_id required'}), 400
    
    # Check if exists
    task = CompletedTask.query.filter_by(
        user_id=user_id,
        date_key=date_key,
        task_id=task_id
    ).first()
    
    if task:
        task.completed = completed
        task.missed = missed
        task.timestamp = datetime.utcnow()
    else:
        task = CompletedTask(
            user_id=user_id,
            date_key=date_key,
            task_id=task_id,
            completed=completed,
            missed=missed
        )
        db.session.add(task)
    
    db.session.commit()
    
    return jsonify({'status': 'saved'}), 200

# ============================================================================
# STRIPE ROUTES
# ============================================================================

@app.route('/api/stripe/create-checkout-session', methods=['POST'])
@jwt_required()
def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    try:
        # Create or retrieve customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email)
            user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'app?success=true',
            cancel_url=request.host_url + 'app?canceled=true',
        )
        
        return jsonify({'checkout_url': session.url}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    # Handle subscription events
    if event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        user = User.query.filter_by(stripe_customer_id=subscription['customer']).first()
        if user:
            user.stripe_subscription_id = subscription['id']
            user.subscription_status = 'active'
            db.session.commit()
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        user = User.query.filter_by(stripe_subscription_id=subscription['id']).first()
        if user:
            user.subscription_status = 'canceled'
            db.session.commit()
    
    return jsonify({'status': 'success'}), 200

@app.route('/api/stripe/portal', methods=['POST'])
@jwt_required()
def create_portal_session():
    """Create Stripe billing portal session"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.stripe_customer_id:
        return jsonify({'error': 'No subscription found'}), 400
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=request.host_url + 'app',
        )
        
        return jsonify({'portal_url': session.url}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ============================================================================
# STATIC FILE SERVING
# ============================================================================

@app.route('/')
def serve_landing():
    """Serve landing page"""
    return send_file('static/landing.html')


@app.route('/login')
def serve_login():
    """Serve login/signup page"""
    return send_file('static/login.html')

@app.route('/app')
@app.route('/app/')
def serve_app():
    """Serve main app (requires auth)"""
    return send_file('static/app.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '4.0'}), 200

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
        print("Database initialized!")

# Initialize DB on Railway/Gunicorn startup too
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5555, debug=False)

@app.route('/init-db')
def init_database():
    """Initialize database tables - call this once after deployment"""
    try:
        db.create_all()
        return jsonify({'status': 'success', 'message': 'Database tables created!'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# SMS NOTIFICATION ENDPOINTS
# ============================================================================

from sms_service import sms_service

@app.route('/api/user/phone', methods=['POST'])
@jwt_required()
def update_phone():
    """Update user phone number and SMS preferences"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    data = request.json
    phone = data.get('phone_number', '').strip()
    sms_enabled = data.get('sms_enabled', False)
    
    # Validate phone format (basic)
    if phone and not phone.startswith('+'):
        return jsonify({'error': 'Phone must start with + (e.g., +1...)'}), 400
    
    user.phone_number = phone if phone else None
    user.sms_enabled = sms_enabled and bool(phone)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Phone settings updated',
        'phone_number': user.phone_number,
        'sms_enabled': user.sms_enabled
    })

@app.route('/api/user/phone', methods=['GET'])
@jwt_required()
def get_phone():
    """Get user phone settings"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    return jsonify({
        'phone_number': user.phone_number,
        'sms_enabled': user.sms_enabled
    })

@app.route('/api/sms/test', methods=['POST'])
@jwt_required()
def test_sms():
    """Send test SMS to verify setup"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user.phone_number:
        return jsonify({'error': 'No phone number configured'}), 400
    
    success = sms_service.send_sms(
        user.phone_number,
        "🎉 Content Queue SMS notifications are working! You'll get reminders for upcoming posts."
    )
    
    if success:
        return jsonify({'message': 'Test SMS sent!'})
    else:
        return jsonify({'error': 'Failed to send SMS'}), 500

