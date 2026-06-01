from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectField,
    SubmitField,
    BooleanField
)

from wtforms.validators import (
    DataRequired,
    Length,
    EqualTo,
    Email
)


class LoginForm(FlaskForm):

    username = StringField(
        "Логин",
        validators=[DataRequired()]
    )

    password = PasswordField(
        "Пароль",
        validators=[DataRequired()]
    )

    submit = SubmitField("Войти")


class RegistrationForm(FlaskForm):

    username = StringField(
        "Логин",
        validators=[
            DataRequired(),
            Length(min=4, max=30)
        ]
    )

    first_name = StringField("Имя")

    last_name = StringField("Фамилия")

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(),
            Length(min=8)
        ]
    )

    confirm_password = PasswordField(
        "Повторите пароль",
        validators=[
            DataRequired(),
            EqualTo("password")
        ]
    )

    submit = SubmitField("Регистрация")


class NewsForm(FlaskForm):

    title = StringField(
        "Заголовок",
        validators=[
            DataRequired(),
            Length(min=5, max=200)
        ]
    )

    content = TextAreaField(
        "Текст новости",
        validators=[
            DataRequired(),
            Length(min=10)
        ]
    )

    category = SelectField(
        "Категория",
        coerce=int,
        validators=[DataRequired()]
    )

    tags = StringField(
        "Теги через запятую"
    )

    is_private = BooleanField(
        "Приватная новость"
    )

    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):

    name = StringField(
        "Название категории",
        validators=[
            DataRequired(),
            Length(min=2, max=50)
        ]
    )

    submit = SubmitField("Сохранить")


class TagForm(FlaskForm):

    name = StringField(
        "Название тега",
        validators=[
            DataRequired(),
            Length(min=2, max=50)
        ]
    )

    submit = SubmitField("Сохранить")