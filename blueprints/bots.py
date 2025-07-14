import os
import shutil
from flask import Blueprint, request, jsonify, current_app
from models import db, Bot
from utils.zip_utils import secure_extract
from utils.bot_loader import register_bots

bp = Blueprint('bots', __name__, url_prefix='/api/admin/bots')

BASE_DIR = os.getenv('BOT_MANAGER_HOME', os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'python_scripts')
os.makedirs(SCRIPTS_DIR, exist_ok=True)

@bp.post('/')
def upload_bot():
    if 'zip' not in request.files or 'name' not in request.form:
        return jsonify({'error': 'zip and name required'}), 400
    file = request.files['zip']
    name = request.form['name']
    folder = ''.join(c for c in name if c.isalnum() or c in '-_').lower()
    dest_dir = os.path.join(SCRIPTS_DIR, folder)
    if os.path.exists(dest_dir):
        return jsonify({'error': 'Bot already exists'}), 400
    os.makedirs(dest_dir)
    zip_path = os.path.join(SCRIPTS_DIR, f'{folder}.zip')
    file.save(zip_path)
    try:
        secure_extract(zip_path, dest_dir)
    except Exception as e:
        shutil.rmtree(dest_dir)
        os.remove(zip_path)
        return jsonify({'error': str(e)}), 400
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    bot = Bot(name=name, folder=folder)
    db.session.add(bot)
    db.session.commit()
    register_bots(current_app, SCRIPTS_DIR)
    return jsonify({'id': bot.id, 'name': bot.name})

@bp.get('/')
def list_bots():
    bots = Bot.query.all()
    return jsonify([{'id': b.id, 'name': b.name, 'price': b.price, 'active': b.active} for b in bots])

@bp.delete('/<int:bot_id>')
def delete_bot(bot_id):
    bot = Bot.query.get_or_404(bot_id)
    folder_path = os.path.join(SCRIPTS_DIR, bot.folder)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    db.session.delete(bot)
    db.session.commit()
    register_bots(current_app, SCRIPTS_DIR)
    return jsonify({'status': 'deleted'})
