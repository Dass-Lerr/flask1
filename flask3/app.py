from flask import Flask, render_template, redirect, url_for, flash, session, abort
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError, EqualTo
import bcrypt
import json
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(256)
app.config['JSON_FILE'] = 'users.json'


def load_users():
    if not os.path.exists(app.config['JSON_FILE']):
        return {}
    with open(app.config['JSON_FILE'], 'r', encoding='utf-8') as f:
        return json.load(f)


def save_users(users):
    with open(app.config['JSON_FILE'], 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


def is_strong_password(password):
    if len(password) < 8:
        return False, "Пароль должен быть не менее 8 символов"
    if not any(c.isupper() for c in password):
        return False, "Пароль должен содержать заглавную букву"
    if not any(c.islower() for c in password):
        return False, "Пароль должен содержать строчную букву"
    if not any(c.isdigit() for c in password):
        return False, "Пароль должен содержать цифру"
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        return False, "Пароль должен содержать спецсимвол"
    return True, "OK"


def username_unique(form, field):
    users = load_users()
    if field.data in users:
        raise ValidationError('Это имя уже занято!')


def password_strong(form, field):
    is_strong, message = is_strong_password(field.data)
    if not is_strong:
        raise ValidationError(message)


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class CreateUserForm(FlaskForm):
    username = StringField('Имя пользователя',
                           validators=[DataRequired(), Length(min=3, max=50), username_unique])
    password = PasswordField('Пароль', validators=[DataRequired(), password_strong])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password', message='Пароли не совпадают!')])
    submit = SubmitField('Создать пользователя')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Сначала войдите!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Сначала войдите!', 'warning')
            return redirect(url_for('login'))

        users = load_users()
        username = session['user']

        if username not in users or users[username].get('role') != 'admin':
            flash('У вас нет прав для выполнения этого действия!', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():
    if 'user' in session:
        # Получаем роль пользователя
        users = load_users()
        username = session['user']
        if username in users and users[username].get('role') == 'admin':
            return redirect(url_for('create_user'))
        else:
            return redirect(url_for('profile'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        users = load_users()
        username = form.username.data
        password = form.password.data.encode('utf-8')

        if username in users:
            stored_hash = users[username]['password'].encode('utf-8')
            if bcrypt.checkpw(password, stored_hash):
                session['user'] = username
                session['role'] = users[username].get('role', 'user')  # Сохраняем роль в сессии
                users[username]['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_users(users)
                flash(f'Добро пожаловать, {username}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверный пароль!', 'danger')
        else:
            flash('Пользователь не найден!', 'danger')

    return render_template('login.html', form=form)


@app.route('/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        users = load_users()
        username = form.username.data
        password = form.password.data.encode('utf-8')

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt)

        users[username] = {
            'password': hashed_password.decode('utf-8'),
            'role': 'user',  # Новые пользователи по умолчанию обычные
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': session['user'],  # Кто создал пользователя
            'last_login': None
        }

        save_users(users)
        flash(f'Пользователь "{username}" создан!', 'success')
        return redirect(url_for('create_user'))

    return render_template('create_user.html', form=form)


@app.route('/profile')
@login_required
def profile():
    users = load_users()
    username = session['user']
    user_data = users.get(username, {})

    return render_template('profile.html',
                           username=username,
                           role=user_data.get('role', 'user'),
                           created_at=user_data.get('created_at'),
                           last_login=user_data.get('last_login'))


@app.route('/users')
@login_required
@admin_required
def list_users():
    users = load_users()
    users_safe = {}
    for username, data in users.items():
        users_safe[username] = {
            'role': data.get('role', 'user'),
            'created_at': data.get('created_at'),
            'last_login': data.get('last_login'),
            'created_by': data.get('created_by', 'system')
        }
    return render_template('users.html', users=users_safe)


@app.route('/delete_user/<username>')
@login_required
@admin_required
def delete_user(username):
    if username == 'admin':
        flash('Нельзя удалить администратора!', 'danger')
        return redirect(url_for('list_users'))

    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        flash(f'Пользователь "{username}" удален!', 'success')
    else:
        flash('Пользователь не найден!', 'danger')

    return redirect(url_for('list_users'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('role', None)  # Очищаем роль из сессии
    flash('Вы вышли', 'info')
    return redirect(url_for('login'))


def create_admin():
    users = load_users()
    if 'admin' not in users:
        password = 'Admin123!'.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password, salt)
        users['admin'] = {
            'password': hashed.decode('utf-8'),
            'role': 'admin',  # Роль администратора
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': 'system',
            'last_login': None
        }
        save_users(users)
        print("✅ Admin: admin / Admin123!")
    else:
        # Обновляем существующего админа, если у него нет роли
        if 'role' not in users['admin']:
            users['admin']['role'] = 'admin'
            users['admin']['created_by'] = 'system'
            save_users(users)
            print("✅ Admin role updated!")


if __name__ == '__main__':
    create_admin()
    app.run(debug=True)