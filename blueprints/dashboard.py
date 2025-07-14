from flask import Blueprint, render_template, session, redirect, url_for, request

bp = Blueprint('dashboard', __name__, url_prefix='/admin')

@bp.before_request
def require_login():
    if 'admin_id' not in session and request.endpoint != 'admin_auth.login':
        return redirect(url_for('admin_auth.login'))

@bp.route('/')
def index():
    return render_template('admin/dashboard.html')

@bp.route('/bots', methods=['GET', 'POST'])
def bots_page():
    from models import Bot
    from blueprints.bots import upload_bot
    if request.method == 'POST':
        return upload_bot()
    bots = Bot.query.all()
    return render_template('admin/bots.html', bots=bots)
