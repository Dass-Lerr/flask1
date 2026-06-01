import os
import re
import json
import uuid
import copy
import base64
import secrets
import time
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_bootstrap5 import Bootstrap
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from google import genai
from google.genai import types
from models import db, User, HistoryEntry
import solver

app = Flask(__name__)

# ── Конфиг ────────────────────────────────────────────────────────────────────
# SECRET_KEY берётся из переменной окружения — не хардкодим в коде
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    # В продакшене переменная ОБЯЗАНА быть задана; в дев-режиме генерируем случайный
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY must be set in production!")
    _secret = secrets.token_hex(32)

app.config['SECRET_KEY'] = _secret
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///sudoku.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Защита сессионной куки
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# app.config['SESSION_COOKIE_SECURE'] = True

# Ограничение размера загружаемых файлов — 16 МБ
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

Bootstrap(app)
csrf = CSRFProtect(app)
db.init_app(app)

client = genai.Client(api_key="AQ.Ab8RN6JeYreBEcg7c_D50_IphQNPi_nungdTt9KHtHhSq-BHRQ")

# Разрешённые MIME-типы для загружаемых изображений
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

with app.app_context():
    db.create_all()
    # Создаём администратора по умолчанию если его нет
    if not User.query.filter_by(username='admin').first():
        admin_pwd = secrets.token_urlsafe(12)  # случайный пароль — распечатается в консоли
        admin = User(
            username='admin',
            password_hash=generate_password_hash(admin_pwd),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("=" * 50)
        print("Создан администратор по умолчанию:")
        print("  логин:  admin")
        print(f"  пароль: {admin_pwd}")
        print("Сохраните пароль!")
        print("=" * 50)

# ── WTForms ───────────────────────────────────────────────────────────────────
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, Regexp

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(), Length(min=3, max=50)
    ])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class SignupForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=3, max=50),
        # Только буквы, цифры, _, . и -
        Regexp(r'^[A-Za-z0-9_.\\-]+$', message='Только латиница, цифры, _, . и -'),
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(), Length(min=8, message='Минимум 8 символов')
    ])
    confirm_password = PasswordField('Повторите пароль', validators=[
        DataRequired(), EqualTo('password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Зарегистрироваться')

class AdminCreateUserForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(), Length(min=3, max=50),
        Regexp(r'^[A-Za-z0-9_.\\-]+$', message='Только латиница, цифры, _, . и -'),
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(), Length(min=8)
    ])
    password_confirm = PasswordField('Повторите пароль', validators=[
        DataRequired(), EqualTo('password', message='Пароли должны совпадать')
    ])
    is_admin = BooleanField('Администратор')
    submit = SubmitField('Создать')

class ProfileEditForm(FlaskForm):
    bio = TextAreaField('О себе', validators=[Optional(), Length(max=500)])
    avatar_color = StringField('Цвет аватара', validators=[Optional(), Length(max=7)])
    current_password = PasswordField('Текущий пароль', validators=[Optional()])
    new_password = PasswordField('Новый пароль', validators=[
        Optional(), Length(min=8, message='Минимум 8 символов')
    ])
    new_password_confirm = PasswordField('Повторите новый пароль', validators=[
        Optional(), EqualTo('new_password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Сохранить')

# ── Хелперы аутентификации ────────────────────────────────────────────────────
def get_current_user():
    """Получаем пользователя по user_id из сессии — не по username."""
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('login'))
        if not user.is_admin:
            flash('Недостаточно прав.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# Передаём текущего пользователя во все шаблоны
@app.context_processor
def inject_user():
    return dict(user=get_current_user())

# ── Валидация загружаемых файлов ──────────────────────────────────────────────
def _is_allowed_file(file) -> bool:
    """Проверяем расширение и MIME-тип файла."""
    filename = file.filename or ''
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    mime = file.mimetype or ''
    return mime in ALLOWED_MIME_TYPES

def _validate_image_bytes(data: bytes) -> bool:
    """Минимальная проверка magic bytes — убеждаемся что это реально изображение."""
    magic = {
        b'\xff\xd8\xff': 'jpeg',
        b'\x89PNG':       'png',
        b'GIF8':          'gif',
        b'RIFF':          'webp',   # RIFF....WEBP
    }
    for sig in magic:
        if data[:len(sig)] == sig:
            return True
    return False

# ── Хелпер: форматируем историю ───────────────────────────────────────────────
def parse_history(entries):
    result = []
    for e in entries:
        result.append({
            "id": e.id,
            "image": e.image_path,
            "board_initial": json.loads(e.board_initial),
            "board_solved": json.loads(e.board_solved),
            "timestamp": e.created_at.strftime('%d.%m.%Y %H:%M'),
        })
    return result

# ── Роуты ─────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if not user or not check_password_hash(user.password_hash, form.password.data):
            flash('Неверное имя пользователя или пароль.', 'danger')
        else:
            session.clear()
            session['user_id'] = user.id
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('index'))
    return render_template("login.html", form=form)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if get_current_user():
        return redirect(url_for('index'))
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует.', 'danger')
            return render_template("signup.html", form=form)
        user = User(
            username=username,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Войдите.', 'success')
        return redirect(url_for('login'))
    return render_template("signup.html", form=form)

@app.route("/logout")
def logout():
    session.clear()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route("/history")
@login_required
def history_page():
    user = get_current_user()
    # Пользователь видит только свою историю
    entries = HistoryEntry.query.filter_by(username=user.username)\
        .order_by(HistoryEntry.created_at.desc()).all()
    return render_template("history.html", history=parse_history(entries))

@app.route("/profile")
@login_required
def profile():
    user = get_current_user()
    entries = HistoryEntry.query.filter_by(username=user.username)\
        .order_by(HistoryEntry.created_at.desc()).all()
    return render_template("profile.html", user=user, history=parse_history(entries))

AVATAR_COLORS = [
    '#C4803A', '#4A7C59', '#5B7FA6', '#9B59B6',
    '#C0392B', '#1A7A6E', '#7D6608', '#2C3E50',
]

@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    user = get_current_user()
    form = ProfileEditForm(obj=user)
    if form.validate_on_submit():
        if form.new_password.data:
            if not form.current_password.data or \
               not check_password_hash(user.password_hash, form.current_password.data):
                flash('Неверный текущий пароль.', 'danger')
                return render_template("profile_edit.html", form=form, user=user, avatar_colors=AVATAR_COLORS)
            user.password_hash = generate_password_hash(form.new_password.data)
        user.bio = form.bio.data.strip() if form.bio.data else None
        # Валидируем hex-цвет — не принимаем произвольную строку
        color = form.avatar_color.data or ''
        if re.match(r'^#[0-9A-Fa-f]{6}$', color):
            user.avatar_color = color
        db.session.commit()
        flash('Профиль обновлён.', 'success')
        return redirect(url_for('profile'))
    form.avatar_color.data = user.avatar_color or AVATAR_COLORS[0]
    return render_template("profile_edit.html", form=form, user=user, avatar_colors=AVATAR_COLORS)

@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if User.query.filter_by(username=username).first():
            flash('Пользователь уже существует.', 'danger')
        else:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(form.password.data),
                is_admin=form.is_admin.data
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Пользователь {username} создан.', 'success')
            return redirect(url_for('admin_users'))
    users = User.query.order_by(User.registered_at.desc()).all()
    return render_template("admin.html", form=form, users=users, me=get_current_user())

@app.route("/admin/users/<username>/delete", methods=["POST"])
@admin_required
def delete_user(username):
    me = get_current_user()
    # Защита: нельзя удалить себя или главного админа
    if username == me.username:
        flash('Нельзя удалить себя.', 'danger')
        return redirect(url_for('admin_users'))
    if username == 'admin':
        flash('Нельзя удалить главного администратора.', 'danger')
        return redirect(url_for('admin_users'))
    user = User.query.filter_by(username=username).first_or_404()
    # Только главный admin может удалять других администраторов
    if user.is_admin and me.username != 'admin':
        flash('Только главный администратор может удалять других администраторов.', 'danger')
        return redirect(url_for('admin_users'))
    HistoryEntry.query.filter_by(username=username).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь {username} удалён.', 'success')
    return redirect(url_for('admin_users'))

# ── Основной эндпоинт: OCR + решатель ────────────────────────────────────────
@app.route("/solve", methods=["POST"])
@csrf.exempt
@login_required
def solve_endpoint():
    if "image" not in request.files:
        return jsonify({"error": "Файл не найден в запросе"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "Файл не выбран"}), 400

    # Проверка расширения и MIME-типа
    if not _is_allowed_file(file):
        return jsonify({"error": "Недопустимый тип файла. Разрешены: JPG, PNG, WEBP, GIF"}), 400

    try:
        img_bytes = file.read()

        # Проверка magic bytes — убеждаемся что файл реально является изображением
        if not _validate_image_bytes(img_bytes):
            return jsonify({"error": "Файл не является изображением."}), 400

        # Ограничение размера (дополнительно к MAX_CONTENT_LENGTH)
        if len(img_bytes) > 16 * 1024 * 1024:
            return jsonify({"error": "Файл слишком большой (максимум 16 МБ)."}), 400

        prompt = """
        Ты — специализированный OCR-сканер игровых полей Судоку.
        Твоя задача — СТРОГО оцифровать начальное состояние сетки Судоку 9х9 с изображения.

        КРИТИЧЕСКИЕ ПРАВИЛА:
        1. Только распознавание: Перенеси только те цифры, которые ИЗНАЧАЛЬНО напечатаны на картинке. Ни в коем случае НЕ ПЫТАЙСЯ решать судоку или заполнять пустые ячейки самостоятельно!
        2. Пустые места: Если в ячейке нет цифры, строго ставь 0.
        3. Формат ответа: Возвращай результат исключительно в формате JSON. Матрица board должна состоять ровно из 9 списков, по 9 чисел в каждом.

        Пример правильного ответа:
        {"board": [[0,9,1,0,0,0,0,7,0],[3,0,0,0,0,0,0,0,6],[7,0,0,0,4,0,0,0,0],[0,0,0,1,0,0,0,0,5],[0,6,0,0,0,8,0,3,0],[5,3,0,0,0,0,2,0,9],[0,0,0,0,0,7,5,0,0],[0,8,0,0,0,0,0,4,2],[0,0,4,6,0,0,0,0,0]]}

        Выдай только сырой JSON, без какого-либо текста до или после структуры.
        """

        # Определяем правильный MIME-тип для Gemini API
        mime_map = {
            'image/jpeg': 'image/jpeg',
            'image/png':  'image/png',
            'image/webp': 'image/webp',
            'image/gif':  'image/gif',
        }
        mime_type = mime_map.get(file.mimetype, 'image/png')

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        prompt,
                        types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                    ],
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                break
            except Exception:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise

        response_text = response.text.strip()
        if response_text.startswith("```"):
            lines = [l for l in response_text.splitlines() if not l.startswith("```")]
            response_text = "\n".join(lines).strip()

        result_json = json.loads(response_text)
        board_initial = result_json.get("board")

        # Строгая валидация структуры доски
        if (not board_initial
                or not isinstance(board_initial, list)
                or len(board_initial) != 9
                or any(not isinstance(row, list) or len(row) != 9 for row in board_initial)
                or any(not isinstance(v, int) or not (0 <= v <= 9)
                       for row in board_initial for v in row)):
            return jsonify({"error": "Нейросеть не смогла корректно считать сетку 9×9. Попробуйте другое фото."}), 400

        board_solved = copy.deepcopy(board_initial)
        if not solver.solve(board_solved):
            return jsonify({"error": "Данная комбинация цифр не имеет решения. Проверьте правильность условий."}), 400

        # Сохраняем файл с uuid-именем — не используем оригинальное имя файла
        os.makedirs("static/uploads", exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        save_path = os.path.join("static/uploads", filename)
        with open(save_path, "wb") as f:
            f.write(img_bytes)

        user = get_current_user()
        entry = HistoryEntry(
            username=user.username,
            image_path=f"uploads/{filename}",
            board_initial=json.dumps(board_initial),
            board_solved=json.dumps(board_solved)
        )
        db.session.add(entry)
        db.session.commit()

        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        return jsonify({
            "result_image_b64": img_b64,
            "board_initial": board_initial,
            "board_solved": board_solved,
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Не удалось разобрать ответ от нейросети. Попробуйте ещё раз."}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Solve error: {e}")
        if app.debug:
            return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500
        return jsonify({"error": "Внутренняя ошибка сервера. Попробуйте ещё раз."}), 500


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_ENV") != "production", port=5000)
