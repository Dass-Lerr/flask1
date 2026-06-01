from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(50), unique=True, nullable=False)
    password_hash   = db.Column(db.String(255), nullable=False)
    is_admin        = db.Column(db.Boolean, default=False, nullable=False)
    bio             = db.Column(db.Text, nullable=True)
    avatar_color    = db.Column(db.String(7), nullable=True)   # hex, e.g. #C4803A
    registered_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at   = db.Column(db.DateTime, nullable=True)


class HistoryEntry(db.Model):
    __tablename__ = 'history_entries'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), nullable=False)
    image_path    = db.Column(db.String(255), nullable=False)
    board_initial = db.Column(db.Text, nullable=False)
    board_solved  = db.Column(db.Text, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
