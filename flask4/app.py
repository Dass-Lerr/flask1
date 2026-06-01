from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    request
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from extensions import db, login_manager

from models import (
    User,
    News,
    Category,
    Tag
)

from forms import (
    LoginForm,
    RegistrationForm,
    NewsForm,
    CategoryForm,
    TagForm
)

from datetime import datetime

import os


app = Flask(__name__)

app.config["SECRET_KEY"] = os.urandom(24)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db.init_app(app)

login_manager.init_app(app)


@app.context_processor
def inject_categories():
    return {
        "categories": Category.query.filter_by(is_deleted=False)
    }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():

    db.create_all()

    if Category.query.filter_by(is_deleted=False).count() == 0:

        categories = [
            Category(name="Политика"),
            Category(name="Спорт"),
            Category(name="Технологии"),
        ]

        db.session.add_all(categories)

        db.session.commit()


@app.route("/")
def index():

    query = News.query.filter_by(is_deleted=False)

    if not current_user.is_authenticated:
        query = query.filter_by(is_private=False)

    # Фильтрация
    category_id = request.args.get("category", type=int)
    tag_id = request.args.get("tag", type=int)
    author_id = request.args.get("author", type=int)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if tag_id:
        query = query.join(News.tags).filter(Tag.id == tag_id)

    if author_id:
        query = query.filter_by(user_id=author_id)

    news_list = query.order_by(
        News.created.desc()
    ).limit(50)

    return render_template(
        "index.html",
        news_list=news_list,
        current_category=category_id,
        current_tag=tag_id,
        current_author=author_id
    )


@app.route("/register", methods=["GET", "POST"])
def register():

    form = RegistrationForm()

    if form.validate_on_submit():

        user_exists = User.query.filter_by(
            username=form.username.data,
            is_deleted=False
        ).first()

        if user_exists:

            flash(
                "Пользователь уже существует",
                "danger"
            )

            return redirect(url_for("register"))

        user = User(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data
        )

        user.set_password(form.password.data)

        db.session.add(user)

        db.session.commit()

        flash(
            "Регистрация успешна",
            "success"
        )

        return redirect(url_for("login"))

    return render_template(
        "register.html",
        form=form
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(
            username=form.username.data,
            is_deleted=False
        ).first()

        if user and user.check_password(
            form.password.data
        ):

            user.last_access = datetime.utcnow()

            db.session.commit()

            login_user(user)

            flash(
                "Вы вошли",
                "success"
            )

            return redirect(url_for("index"))

        flash(
            "Неверный логин или пароль",
            "danger"
        )

    return render_template(
        "login.html",
        form=form
    )


@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "Вы вышли",
        "info"
    )

    return redirect(url_for("index"))


@app.route("/news/add", methods=["GET", "POST"])
@login_required
def add_news():

    form = NewsForm()

    categories = Category.query.filter_by(is_deleted=False)

    form.category.choices = [
        (c.id, c.name)
        for c in categories
    ]

    if form.validate_on_submit():

        news = News(
            title=form.title.data,
            content=form.content.data,
            category_id=form.category.data,
            user_id=current_user.id,
            is_private=form.is_private.data
        )

        tag_names = [
            tag.strip()
            for tag in form.tags.data.split(",")
            if tag.strip()
        ]

        tags = []

        for tag_name in tag_names:

            tag = Tag.query.filter_by(
                name=tag_name,
                is_deleted=False
            ).first()

            if not tag:

                tag = Tag(name=tag_name)

                db.session.add(tag)

            tags.append(tag)

        news.tags = tags

        db.session.add(news)

        db.session.commit()

        flash(
            "Новость создана",
            "success"
        )

        return redirect(url_for("index"))

    return render_template(
        "news_form.html",
        form=form,
        title="Создание новости"
    )


@app.route("/news/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_news(id):

    news = News.query.get_or_404(id)

    if news.is_deleted:
        flash("Новость удалена", "danger")
        return redirect(url_for("index"))

    if news.user_id != current_user.id:
        flash("Нет прав на редактирование", "danger")
        return redirect(url_for("news_detail", id=id))

    form = NewsForm(obj=news)

    categories = Category.query.filter_by(is_deleted=False)

    form.category.choices = [
        (c.id, c.name)
        for c in categories
    ]

    if request.method == "GET":
        form.tags.data = ", ".join(
            [tag.name for tag in news.tags]
        )

    if form.validate_on_submit():

        news.title = form.title.data
        news.content = form.content.data
        news.category_id = form.category.data
        news.is_private = form.is_private.data

        tag_names = [
            tag.strip()
            for tag in form.tags.data.split(",")
            if tag.strip()
        ]

        tags = []

        for tag_name in tag_names:

            tag = Tag.query.filter_by(
                name=tag_name,
                is_deleted=False
            ).first()

            if not tag:

                tag = Tag(name=tag_name)

                db.session.add(tag)

            tags.append(tag)

        news.tags = tags

        db.session.commit()

        flash("Новость обновлена", "success")

        return redirect(url_for("news_detail", id=news.id))

    return render_template(
        "news_form.html",
        form=form,
        title="Редактирование новости"
    )


@app.route("/news/<int:id>/delete")
@login_required
def delete_news(id):

    news = News.query.get_or_404(id)

    if news.user_id != current_user.id:
        flash("Нет прав на удаление", "danger")
        return redirect(url_for("news_detail", id=id))

    news.is_deleted = True

    db.session.commit()

    flash("Новость удалена", "info")

    return redirect(url_for("index"))


@app.route("/news/<int:id>")
def news_detail(id):

    news = News.query.get_or_404(id)

    if news.is_deleted:
        flash("Новость удалена", "danger")
        return redirect(url_for("index"))

    if news.is_private and not current_user.is_authenticated:

        flash(
            "Эта новость приватная",
            "danger"
        )

        return redirect(url_for("index"))

    return render_template(
        "news_detail.html",
        news=news
    )


# CRUD для категорий

@app.route("/categories")
@login_required
def category_list():

    categories = Category.query.filter_by(is_deleted=False)

    return render_template(
        "category_list.html",
        categories=categories
    )


@app.route("/categories/add", methods=["GET", "POST"])
@login_required
def add_category():

    form = CategoryForm()

    if form.validate_on_submit():

        existing = Category.query.filter_by(
            name=form.name.data,
            is_deleted=False
        ).first()

        if existing:
            flash("Такая категория уже существует", "danger")
            return redirect(url_for("add_category"))

        category = Category(name=form.name.data)

        db.session.add(category)

        db.session.commit()

        flash("Категория создана", "success")

        return redirect(url_for("category_list"))

    return render_template(
        "category_form.html",
        form=form,
        title="Создание категории"
    )


@app.route("/categories/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(id):

    category = Category.query.get_or_404(id)

    if category.is_deleted:
        flash("Категория удалена", "danger")
        return redirect(url_for("category_list"))

    form = CategoryForm(obj=category)

    if form.validate_on_submit():

        existing = Category.query.filter(
            Category.name == form.name.data,
            Category.id != id,
            Category.is_deleted == False
        ).first()

        if existing:
            flash("Такая категория уже существует", "danger")
            return redirect(url_for("edit_category", id=id))

        category.name = form.name.data

        db.session.commit()

        flash("Категория обновлена", "success")

        return redirect(url_for("category_list"))

    return render_template(
        "category_form.html",
        form=form,
        title="Редактирование категории"
    )


@app.route("/categories/<int:id>/delete")
@login_required
def delete_category(id):

    category = Category.query.get_or_404(id)

    category.is_deleted = True

    # Помечаем все новости категории как удалённые
    News.query.filter_by(category_id=id).update(
        {"is_deleted": True}
    )

    db.session.commit()

    flash("Категория удалена", "info")

    return redirect(url_for("category_list"))


# CRUD для тегов

@app.route("/tags")
@login_required
def tag_list():

    tags = Tag.query.filter_by(is_deleted=False)

    return render_template(
        "tag_list.html",
        tags=tags
    )


@app.route("/tags/add", methods=["GET", "POST"])
@login_required
def add_tag():

    form = TagForm()

    if form.validate_on_submit():

        existing = Tag.query.filter_by(
            name=form.name.data,
            is_deleted=False
        ).first()

        if existing:
            flash("Такой тег уже существует", "danger")
            return redirect(url_for("add_tag"))

        tag = Tag(name=form.name.data)

        db.session.add(tag)

        db.session.commit()

        flash("Тег создан", "success")

        return redirect(url_for("tag_list"))

    return render_template(
        "tag_form.html",
        form=form,
        title="Создание тега"
    )


@app.route("/tags/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_tag(id):

    tag = Tag.query.get_or_404(id)

    if tag.is_deleted:
        flash("Тег удалён", "danger")
        return redirect(url_for("tag_list"))

    form = TagForm(obj=tag)

    if form.validate_on_submit():

        existing = Tag.query.filter(
            Tag.name == form.name.data,
            Tag.id != id,
            Tag.is_deleted == False
        ).first()

        if existing:
            flash("Такой тег уже существует", "danger")
            return redirect(url_for("edit_tag", id=id))

        tag.name = form.name.data

        db.session.commit()

        flash("Тег обновлён", "success")

        return redirect(url_for("tag_list"))

    return render_template(
        "tag_form.html",
        form=form,
        title="Редактирование тега"
    )


@app.route("/tags/<int:id>/delete")
@login_required
def delete_tag(id):

    tag = Tag.query.get_or_404(id)

    tag.is_deleted = True

    db.session.commit()

    flash("Тег удалён", "info")

    return redirect(url_for("tag_list"))


# Авторы

@app.route("/authors")
def author_list():

    authors = User.query.filter_by(is_deleted=False)

    return render_template(
        "author_list.html",
        authors=authors
    )


@app.route("/authors/<int:id>")
def author_detail(id):

    author = User.query.get_or_404(id)

    if author.is_deleted:
        flash("Пользователь удалён", "danger")
        return redirect(url_for("index"))

    query = News.query.filter_by(
        user_id=id,
        is_deleted=False
    )

    if not current_user.is_authenticated:
        query = query.filter_by(is_private=False)

    news_list = query.order_by(News.created.desc()).limit(50)

    return render_template(
        "author_detail.html",
        author=author,
        news_list=news_list
    )


if __name__ == "__main__":
    app.run(debug=True)