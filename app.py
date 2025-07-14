import os
from flask import Flask
from flask_migrate import Migrate
from models import db, Admin
from werkzeug.security import generate_password_hash
from utils.bot_loader import register_bots
from blueprints import all_blueprints

BASE_DIR = os.getenv('BOT_MANAGER_HOME', os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'python_scripts')
os.makedirs(SCRIPTS_DIR, exist_ok=True)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'change-this'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'botmanager.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    Migrate(app, db)
    for bp in all_blueprints:
        app.register_blueprint(bp)
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
        register_bots(app, SCRIPTS_DIR)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
