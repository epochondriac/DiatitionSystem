"""Main Flask application API routing and server initializations."""

import os
import bcrypt
from flask import Flask
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

from models import db

# Import Blueprints
from routes.products import products_bp
from routes.meals import meals_bp
from routes.categories import categories_bp
from routes.sensitivities import sensitivities_bp
from routes.textures import textures_bp
from routes.diets import diets_bp
from routes.system import system_bp
from routes.auth import auth_bp
from routes.users import users_bp

from security import init_security

app = Flask(__name__)
init_security(app)

# The Connection String: Tells SQLAlchemy exactly where the Docker DB is
# Format: postgresql://username:password@host:port/database_name
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://admin:secretpassword@localhost:5432/hospital_system'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Connect the database to this Flask app
db.init_app(app)

# Register Blueprints
app.register_blueprint(products_bp)
app.register_blueprint(meals_bp)
app.register_blueprint(categories_bp)
app.register_blueprint(sensitivities_bp)
app.register_blueprint(textures_bp)
app.register_blueprint(diets_bp)
app.register_blueprint(system_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)

# Create the tables when the server starts
with app.app_context():
    # First, ensure the pgvector extension is activated in the database
    db.session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    db.session.commit()
    # Then, create all tables based on models.py
    db.create_all()
    print("Database tables created successfully!")

    # Apply any column-level migrations that db.create_all() won't handle
    migrations = [
        'ALTER TABLE food_items ADD COLUMN IF NOT EXISTS texture_id INTEGER REFERENCES textures(id)',
        'ALTER TABLE meals ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id)',
        'ALTER TABLE meals ADD COLUMN IF NOT EXISTS is_global BOOLEAN NOT NULL DEFAULT TRUE',
    ]
    for sql in migrations:
        db.session.execute(text(sql))
    db.session.commit()

    # Seed a default admin user if the users table is empty
    from models import User
    if User.query.count() == 0:
        admin = User(
            username='admin',
            password_hash=bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode(),
            role='admin',
            must_change_password=True,
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created (username: admin, password: admin).")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
