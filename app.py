import os
import subprocess
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(32))

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'linkdrop.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')
RATE_LIMIT_SUBMISSIONS = int(os.getenv('RATE_LIMIT_SUBMISSIONS', 10))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 3600))
APP_PORT = int(os.getenv('PORT', 5000))


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_token = db.Column(db.String(64), nullable=False, index=True)
    url = db.Column(db.String(2048), nullable=False)
    note = db.Column(db.String(500), default='')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    download_log = db.Column(db.Text, default='')
    downloaded_at = db.Column(db.DateTime, nullable=True)
    download_path = db.Column(db.String(1024), default='')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db():
    with app.app_context():
        db.create_all()


def get_or_create_user():
    cookie_token = request.cookies.get('linkdrop_user')
    user = None
    
    if cookie_token:
        user = User.query.filter_by(token=cookie_token).first()
    
    if not user:
        new_token = str(uuid.uuid4())
        user = User(token=new_token)
        db.session.add(user)
        db.session.commit()
        return new_token, user.name
    
    return user.token, user.name


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


@app.route('/')
def index():
    return redirect(url_for('submit'))


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    user_token, user_name = get_or_create_user()
    response = None
    
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        note = request.form.get('note', '').strip()
        
        if not url:
            flash('URL is required.', 'error')
            links = Link.query.filter_by(user_token=user_token).order_by(Link.submitted_at.desc()).all()
            return render_template('submit.html', links=links, user_token=user_token, user_name=user_name)
        
        if not validate_url(url):
            flash('Invalid URL format.', 'error')
            links = Link.query.filter_by(user_token=user_token).order_by(Link.submitted_at.desc()).all()
            return render_template('submit.html', links=links, user_token=user_token, user_name=user_name)
        
        if len(url) > 2048:
            flash('URL is too long.', 'error')
            links = Link.query.filter_by(user_token=user_token).order_by(Link.submitted_at.desc()).all()
            return render_template('submit.html', links=links, user_token=user_token, user_name=user_name)
        
        link = Link(user_token=user_token, url=url, note=note[:500])
        db.session.add(link)
        db.session.commit()
        
        flash('Link submitted successfully!', 'success')
        
        response = make_response(redirect(url_for('submit')))
        response.set_cookie('linkdrop_user', user_token, max_age=60*60*24*365, httponly=True)
        return response
    
    links = Link.query.filter_by(user_token=user_token).order_by(Link.submitted_at.desc()).all()
    
    response = make_response(render_template('submit.html', links=links, user_token=user_token, user_name=user_name))
    response.set_cookie('linkdrop_user', user_token, max_age=60*60*24*365, httponly=True)
    return response


@app.route('/set_name', methods=['POST'])
def set_name():
    user_token, _ = get_or_create_user()
    name = request.form.get('name', '').strip()[:100]
    
    user = User.query.filter_by(token=user_token).first()
    if user:
        user.name = name
        db.session.commit()
    
    flash('Name updated!', 'success')
    
    response = make_response(redirect(url_for('submit')))
    response.set_cookie('linkdrop_user', user_token, max_age=60*60*24*365, httponly=True)
    return response


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin'))
        
        flash('Invalid credentials.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('submit'))


@app.route('/admin')
@login_required
def admin():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = Link.query
    
    if search:
        query = query.filter(
            (Link.url.contains(search)) | 
            (Link.note.contains(search))
        )
    
    if status_filter:
        query = query.filter(Link.status == status_filter)
    
    links = query.order_by(Link.submitted_at.desc()).all()
    
    stats = {
        'pending': Link.query.filter_by(status='pending').count(),
        'downloading': Link.query.filter_by(status='downloading').count(),
        'done': Link.query.filter_by(status='done').count(),
        'failed': Link.query.filter_by(status='failed').count(),
        'total': Link.query.count()
    }
    
    return render_template('admin.html', links=links, stats=stats, search=search, status_filter=status_filter)


@app.route('/admin/download/<int:link_id>', methods=['POST'])
@login_required
def download_link(link_id):
    link = Link.query.get_or_404(link_id)
    
    link.status = 'downloading'
    db.session.commit()
    
    try:
        result = subprocess.run(
            ['dl', link.url],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            link.status = 'done'
            link.download_log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        else:
            link.status = 'failed'
            link.download_log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        
        link.downloaded_at = datetime.utcnow()
        db.session.commit()
        
    except subprocess.TimeoutExpired:
        link.status = 'failed'
        link.download_log = 'Download timed out after 600 seconds.'
        db.session.commit()
        
    except Exception as e:
        link.status = 'failed'
        link.download_log = f'Error: {str(e)}'
        db.session.commit()
    
    flash(f'Download {link.status} for {link.url}', 'success' if link.status == 'done' else 'error')
    return redirect(url_for('admin'))


@app.route('/admin/mark_done/<int:link_id>', methods=['POST'])
@login_required
def mark_done(link_id):
    link = Link.query.get_or_404(link_id)
    link.status = 'done'
    link.downloaded_at = datetime.utcnow()
    link.download_log = 'Manually marked as done.'
    db.session.commit()
    
    flash('Link marked as done.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/retry/<int:link_id>', methods=['POST'])
@login_required
def retry_link(link_id):
    link = Link.query.get_or_404(link_id)
    link.status = 'pending'
    link.download_log = ''
    link.downloaded_at = None
    db.session.commit()
    
    flash('Link status reset to pending.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/delete/<int:link_id>', methods=['POST'])
@login_required
def delete_link(link_id):
    link = Link.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    
    flash('Link deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/set_path/<int:link_id>', methods=['POST'])
@login_required
def set_download_path(link_id):
    link = Link.query.get_or_404(link_id)
    path = request.form.get('download_path', '').strip()
    link.download_path = path
    db.session.commit()
    
    flash('Download path updated.', 'success')
    return redirect(url_for('admin'))


@app.route('/admin/log/<int:link_id>')
@login_required
def view_log(link_id):
    link = Link.query.get_or_404(link_id)
    return jsonify({'log': link.download_log or 'No log available.'})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=APP_PORT, debug=False)