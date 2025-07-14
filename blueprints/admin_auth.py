from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Admin

bp = Blueprint('admin_auth', __name__, url_prefix='/admin')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form if request.content_type.startswith('application/x-www-form-urlencoded') else request.json
        username = data.get('username')
        password = data.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            if request.is_json:
                return jsonify({'status': 'success'})
            return redirect(url_for('dashboard.index'))
        if request.is_json:
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
        return render_template('admin/login.html', error='Invalid credentials')
    return render_template('admin/login.html')

@bp.route('/logout', methods=['POST'])
def logout():
    session.pop('admin_id', None)
    if request.is_json:
        return jsonify({'status': 'success'})
    return redirect(url_for('admin_auth.login'))
