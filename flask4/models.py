from extensions import db

from datetime import datetime

from flask_login import UserMixin

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


class User(db.Model, UserMixin):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    first_name = db.Column(db.String(30))

    last_name = db.Column(db.String(30))

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    last_access = db.Column(db.DateTime)

    is_deleted = db.Column(
        db.Boolean,
        default=False
    )

    news = db.relationship(
        'News',
        backref='author',
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Category(db.Model):

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    is_deleted = db.Column(
        db.Boolean,
        default=False
    )

    news = db.relationship(
        'News',
        backref='category',
        lazy='dynamic'
    )


class Tag(db.Model):

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    is_deleted = db.Column(
        db.Boolean,
        default=False
    )


news_tags = db.Table(
    "news_tags",

    db.Column(
        "news_id",
        db.Integer,
        db.ForeignKey("news.id"),
        primary_key=True
    ),

    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("tags.id"),
        primary_key=True
    )
)


class News(db.Model):

    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    created = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated = db.Column(
        db.DateTime,
        onupdate=datetime.utcnow
    )

    is_private = db.Column(
        db.Boolean,
        default=False
    )

    is_deleted = db.Column(
        db.Boolean,
        default=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False
    )

    tags = db.relationship(
        "Tag",
        secondary=news_tags,
        backref=db.backref(
            "news",
            lazy="dynamic"
        )
    )