from flask_sqlalchemy import SQLAlchemy

from flask_login import UserMixin
import datetime
from sqlalchemy import MetaData

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)

db = SQLAlchemy(metadata=metadata)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    book = db.relationship("Copy", backref="issue", lazy=True)
    admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50))  # [Admin, Teacher, Student, Librarian]


class Students(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    student_number = db.Column(db.String(255), unique=True)


class LendingRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lent_to = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, default=None
    )
    lent_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, default=None
    )
    lending_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    return_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    return_status = db.Column(db.Boolean, default=False)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)
    author = db.Column(db.String(255))
    description = db.Column(db.Text)
    copies = db.relationship(
        "Copy", backref="book", lazy=True, cascade="all,delete"
    )
    total_copy = db.Column(db.Integer)
    issued_copy = db.Column(db.Integer)
    present_copy = db.Column(db.Integer)


class Copy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_added = db.Column(db.DateTime())
    issued_by = db.Column(
        db.Integer, db.ForeignKey("user.id"),  default=None
    )
    date_issued = db.Column(db.DateTime(), default=None)
    date_return = db.Column(db.DateTime(), default=None)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"))
