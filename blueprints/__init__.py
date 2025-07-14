from .admin_auth import bp as admin_auth_bp
from .dashboard import bp as dashboard_bp
from .bots import bp as bots_api_bp

all_blueprints = [admin_auth_bp, dashboard_bp, bots_api_bp]
