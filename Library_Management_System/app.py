"""
Routes and views for the flask application.
"""

from datetime import datetime, timedelta
from functools import wraps

from flask import flash, redirect, render_template, request, url_for
from flask.blueprints import Blueprint
from flask.views import MethodView
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import *

"""
The flask application package.
"""

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

login_manager = LoginManager(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=300)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300
app.config['ASSIGNMENT_FOLDER'] = "static/assignment"
app.config['SECRET_KEY'] = 'LibraryManagerSecreteMessage'
app.config['UPLOAD_FOLDER'] = 'static/ProjectFiles'
migrate = Migrate(app, db)
db.init_app(app)


def datetimeformat(value, date_format='%A %Y-%m-%d  %H:%M'):
    """Format a datetime object as a string."""
    return value.strftime(date_format)


app.jinja_env.filters['datetimeformat'] = datetimeformat


def requires_admin(f):
    """Checks if user has admin access"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.admin:
            return f(*args, **kwargs)
        return unauthorized()

    return wrapped


@login_manager.user_loader
def load_user(user_id: int):
    return User.query.get(user_id)


@app.route("/admin/register")
def register_admin():
    flash("You are now admin")
    user = current_user
    user.admin = True
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/", methods=["GET"])
def index():
    """Home Page"""
    db.create_all()
    books = Book.query.all()

    if books:
        return render_template("index.html", year=datetime.datetime.now().year, books=books)
    flash("No books are in library!")
    return render_template("index.html", year=datetime.datetime.now().year)


class LoginView(MethodView):
    def get(self):
        return render_template("login.html", year=datetime.datetime.now().year)

    def post(self):
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if request.args.get("next"):
                return redirect(request.args.get("next"))

            return redirect(url_for("dashboard"))
        flash("Invalid Credentials!")
        return redirect(url_for("login"))


class RegisterView(MethodView):
    def get(self):
        return render_template("register.html", year=datetime.datetime.now().year)

    def post(self):
        name = request.form.get("name")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"), method="sha256")
        if User.query.filter_by(email=email).first():
            flash("User already exists!")
            return redirect(url_for("register"))
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        if request.args.get("next"):
            return redirect(request.args.get("next"))
        return redirect(url_for("dashboard"))


class AdminView(MethodView):
    def get(self):
        return render_template("admin.html", year=datetime.datetime.now().year)

    def post(self):
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email, admin=True).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            if request.args.get("next"):
                return redirect(request.args.get("next"))
            return redirect(url_for("dashboard"))
        flash("Invalid Credentials!")
        return redirect(url_for("admin"))


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    copies = db.session.query(Book).join(Copy).filter(Copy.issued_by == current_user.id).all()
    if copies:
        if current_user.admin:
            return redirect(url_for("admin_dashboard"))
        return render_template("dashboard.html", year=datetime.datetime.now().year, books=copies)

    flash("You don't have books issued!")
    return render_template("dashboard.html", year=datetime.datetime.now().year)


@app.route("/admin/dashboard", methods=["GET"])
@login_required
@requires_admin
def admin_dashboard():
    books = Book.query.all()
    if books:
        return render_template(
            "admin_dashboard.html", books=books, year=datetime.datetime.now().year
        )
    flash("No books are there in library!")
    return render_template("admin_dashboard.html", year=datetime.datetime.now().year)


class AddBookView(MethodView):
    def get(self):
        return render_template("add_book.html", year=datetime.datetime.now().year)

    def post(self):
        name = request.form.get("name")
        author = request.form.get("author")
        description = request.form.get("description")
        number = int(request.form.get("number"))
        book = Book.query.filter_by(name=name).first()
        if book:
            flash("Book already exists!")
            return redirect(url_for("add_book"))
        book = Book(
            name=name,
            author=author,
            description=description,
            total_copy=number,
            present_copy=number,
            issued_copy=0,
        )

        for _ in range(number):
            copy = Copy(date_added=datetime.datetime.now())
            book.copies.append(copy)
            db.session.add(book)
        db.session.commit()
        flash("Book added successfully!")
        return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
@login_required
@requires_admin
def admin_logout():
    return redirect(url_for("index"))


class IssueBookView(MethodView):
    def get(self):
        books = Book.query.filter(Book.present_copy > 0).all()
        if books:
            return render_template(
                "issue.html", books=Book.query.all(), year=datetime.datetime.now().year
            )
        flash("No books are currently available!")
        return render_template(
            "issue.html", year=datetime.datetime.now().year, books=Book.query.all()
        )

    def post(self):
        book_id = request.form.get("book", type=int)
        book = Copy.query.filter_by(book_id=book_id, issued_by=None).first()
        book_info = Book.query.get(book_id)
        book.issued_by = current_user.id
        book_info.issued_copy += 1
        book_info.present_copy -= 1
        book.date_issued = datetime.datetime.now()
        book.date_return = datetime.datetime.now() + timedelta(days=1)
        db.session.commit()
        flash("Book issued successfully!")
        return redirect(url_for("dashboard"))


class ReturnBookView(MethodView):
    def get(self):
        copies = db.session.query(Book).join(Copy).filter(Copy.issued_by == current_user.id).all()
        if copies:
            return render_template(
                "return.html", books=copies, year=datetime.datetime.now().year
            )

        flash("You don't have any books issued!")
        return render_template(
            "return.html", year=datetime.datetime.now().year, books=Book.query.all()
        )

    def post(self):
        book_id = request.form.get("book", type=int)
        print(book_id)
        book = Copy.query.filter_by(
            book_id=book_id, issued_by=current_user.id
        ).first()
        book_info=Book.query.get(book_id)
        book.issued_by = None
        book.date_issued = None
        book.date_return = None
        book_info.issued_copy -= 1
        book_info.present_copy += 1
        db.session.commit()
        flash("Book returned successfully!")
        return redirect(url_for("dashboard"))


class RemoveBookView(MethodView):
    def get(self):
        books = Book.query.filter_by(issued_copy=0).all()
        if books:
            return render_template(
                "remove_book.html", year=datetime.datetime.now().year, books=Book.query.all()
            )

        flash("No books are available to be removed!")
        return render_template(
            "remove_book.html", year=datetime.datetime.now().year, books=Book.query.all()
        )

    def post(self):
        book_id = int(request.form.get("book"))
        book = Book.query.filter_by(id=book_id).first()
        db.session.delete(book)
        db.session.commit()
        flash("Book removed successfully!")
        return redirect(url_for("admin_dashboard"))


app.add_url_rule("/register", view_func=RegisterView.as_view("register"))
app.add_url_rule("/login", view_func=LoginView.as_view("login"))
app.add_url_rule("/admin", view_func=AdminView.as_view("admin"))
app.add_url_rule(
    "/add/book",
    view_func=login_required(requires_admin(AddBookView.as_view("add_book"))),
)
app.add_url_rule(
    "/return/book", view_func=login_required(ReturnBookView.as_view("return_book"))
)
app.add_url_rule(
    "/remove/book", view_func=login_required(RemoveBookView.as_view("remove_book"))
)
app.add_url_rule(
    "/issue/book", view_func=login_required(IssueBookView.as_view("issue_book"))
)


@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@login_manager.unauthorized_handler
def unauthorized():
    flash("You are not authorized to access the content!")
    return redirect(url_for("login"))
