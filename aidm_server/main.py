# server.py

import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# Update imports to use aidm_server package
from aidm_server.database import db, init_db
from aidm_server.blueprints.campaigns import campaigns_bp
from aidm_server.blueprints.worlds import worlds_bp
from aidm_server.blueprints.players import players_bp
from aidm_server.blueprints.sessions import sessions_bp
from aidm_server.blueprints.socketio_events import register_socketio_events
from aidm_server.blueprints.admin import configure_admin

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or "my_dev_secret"

    init_db(app)

    # Register blueprints with /api prefix
    app.register_blueprint(campaigns_bp, url_prefix='/api/campaigns')
    app.register_blueprint(worlds_bp, url_prefix='/api/worlds')
    app.register_blueprint(players_bp, url_prefix='/api/players')
    app.register_blueprint(sessions_bp, url_prefix='/api/sessions')

    # Flask-Admin setup
    configure_admin(app, db)

    return app

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")
register_socketio_events(socketio)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Running directly via Python
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)