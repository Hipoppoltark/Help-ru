import os

from api import record_resources
from flask import Flask, flash
from flask import url_for, request, render_template, session, abort
from flask import redirect, make_response, jsonify

from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import reqparse, abort, Api, Resource

from flask_socketio import SocketIO, send

from data import db_session
from data.records import Record
from data.users import User
from data.comments import Comment
from data.complaints import Complaint
from data.ratings import Rating

from forms.register import RegisterForm
from forms.login import LoginForm
from forms.record import RecordForm
from forms.comment import CommentForm
from forms.profile_edit import ProfileForm

import json
from time import sleep

from celery import Celery
import celeryconfig

import requests

import uuid
import hashlib


def hash_password(password):
    # uuid используется для генерации случайного числа
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt


def check_password(hashed_password, user_password):
    password, salt = hashed_password.split(':')
    return password == hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()



app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
api = Api(app)
client = Celery(app.name)
client.config_from_object("celeryconfig")


class ContextTask(client.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


client.Task = ContextTask

login_manager = LoginManager()
login_manager.init_app(app)


@client.task
def celery_editable_task(record_id):
    """Фоновая задача. Через n время (после того, как запись считается закрытой)
       запрщает редактировать запись и все комментарии к ней"""
    print(1)
    db_session.global_init('db/help.db')
    print(2)
    session = db_session.create_session()
    print(3)
    record = session.query(Record).get(record_id)
    print(session)
    record.is_editable = False
    session.commit()
    session.close()
    db_session.close_session()


@client.task
def celery_processing_complaint(comment_id):
    """Фоновая задача обработки жалобы (в течение n времени задача запускается и решает
       нужно ли удалять комментарий или нет"""
    print(2)
    db_session.global_init("db/help.db")
    session = db_session.create_session()
    comment = session.query(Comment).get(comment_id)
    comment_points = comment.cost
    record = session.query(Record).get(comment.record_id)
    author_comment = session.query(User).get(comment.author)
    if len(comment.complaints) >= len(comment.ratings):
        session.delete(comment)
        record.is_editable = True
        record.is_finished = False
        author_comment.points -= comment_points
    else:
        comment.pending_review = False
    session.commit()
    session.close()
    db_session.close_session()


@app.route('/')
def main():
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        records = []
        for record in db_sess.query(Record).filter(Record.author != current_user.id):
            records.append((record, record.description[:250]))
        param = {}
        param['title'] = 'Работы'
        param['records'] = records
        return render_template('index.html', **param)
    else:
        param = {}
        param['title'] = 'Работы'
        return render_template('landing.html', **param)


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form = RegisterForm()
    param = {}
    param['title'] = 'Регистрация'
    if request.method == 'GET':
        return render_template('register.html', **param, form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            user = User()
            user.surname = form.surname.data
            user.name = form.name.data
            user.age = form.age.data
            user.hashed_password = hash_password(form.password.data)
            user.email = form.username.data
            db_sess = db_session.create_session()
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
        return render_template('register.html', **param, form=form)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required  # Страница, только для авторизованного пользователя
def logout():
    logout_user()
    return redirect("/")


@app.route('/record',  methods=['GET', 'POST'])
@login_required
def add_record():
    form = RecordForm()
    if form.validate_on_submit():
        response = requests.post(
            'http://help-our-ru.herokuapp.com/api/records',
            headers={'content-type': 'application/json; charset=utf-8'},
            json={'title': form.title.data,
                  'description': form.description.data,
                  'cost': form.cost.data,
                  'email': current_user.email,
                  'password': current_user.hashed_password}
        ).json()
        if 'success' in response.keys():
            return redirect('/')
        elif 'error' in response.keys():
            return render_template('record_form.html', form=form, message='Недостаточно средств')
        abort(401)
    return render_template('record_form.html', form=form)


@app.route('/record/<int:record_id>',  methods=['GET', 'POST'])
def page_record(record_id):
    if request.method == 'GET':
        db_sess = db_session.create_session()
        param = {}
        param['record'] = db_sess.query(Record).get(record_id)
        param['may_comment'] = len(param['record'].comments) < 3
        return render_template('record.html', **param)


@app.route('/record-edit/<int:record_id>',  methods=['GET', 'POST'])
@login_required
def edit_record(record_id):
    form = RecordForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        record = db_sess.query(Record).filter(Record.id == record_id).first()
        if record:
            form.title.data = record.title
            form.description.data = record.description
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        record = db_sess.query(Record).filter(Record.id == record_id).first()
        if record:
            record.title = form.title.data
            record.description = form.description.data
            db_sess.commit()
            return redirect(f'/record/{record_id}')
        else:
            abort(404)
    return render_template('record_form.html', title='Редактирование пользователя', form=form)


@app.route('/record/<int:record_id>/comment',  methods=['GET', 'POST'])
@login_required
def add_comment(record_id):
    form = CommentForm()
    db_sess = db_session.create_session()
    record = db_sess.query(Record).get(record_id)
    cost_record = record.cost
    if request.method == 'GET':
        return render_template('comment.html',
                               record=record,
                               form=form)
    elif request.method == 'POST':
        if form.validate_on_submit():
            comment = Comment()
            comment.author = current_user.id
            comment.comment = form.comment.data
            comment.record_id = record.id
            record.comments.append(comment)
            db_sess.merge(record)
            db_sess.commit()

            db_sess = db_session.create_session()
            record = db_sess.query(Record).get(record_id)
            record.is_finished = True

            db_sess.commit()

            db_sess = db_session.create_session()
            user = db_sess.query(User).get(current_user.id)
            user.points = int(current_user.points) + int(cost_record)
            db_sess.commit()

            celery_editable_task.apply_async(args=[record_id], countdown=20)
            return redirect(f'/record/{record_id}')
        return render_template('comment.html',
                               record=record,
                               form=form)


@app.route('/record/comments-edit/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    form = CommentForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        comment = db_sess.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            form.comment.data = comment.comment
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        comment = db_sess.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            comment.comment = form.comment.data
            db_sess.commit()
            return redirect(f'/record/{comment.record_id}')
        else:
            abort(404)
    return render_template('comment.html', record=comment.record, form=form)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/profile/<int:user_id>',  methods=['GET', 'POST'])
def page_profile(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(user_id)
    return render_template('profile.html', user=user)


@app.route('/profile-edit/<int:user_id>',  methods=['GET', 'POST'])
@login_required
def edit_profile(user_id):
    form = ProfileForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == user_id).first()
        if user:
            form.username.data = user.email
            form.surname.data = user.surname
            form.name.data = user.name
            form.age.data = user.age
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == user_id).first()
        if db_sess.query(User).filter(User.email == form.username.data,
                                      current_user.email != form.username.data).first():
            return render_template('record_form.html', title='Редактирование пользователя', form=form,
                                   message='Такой email уже существует')
        if user:
            user.email = form.username.data
            user.surname = form.surname.data
            user.name = form.name.data
            user.age = form.age.data
            db_sess.commit()
            return render_template('record_form.html', title='Редактирование пользователя', form=form,
                                   message='Изменения успешно сохранены')
        else:
            abort(404)
    return render_template('record_form.html', title='Редактирование пользователя', form=form)


@app.route("/rating_comment", methods=["POST"])
@login_required
def set_rating_comment():
    value_rating = int(request.form.get("value_rating"))
    db_sess = db_session.create_session()
    comment = db_sess.query(Comment).get(int(request.form.get("comment_id")))
    if current_user.id not in [rating.author for rating in comment.ratings]:
        comment.estimation = (comment.estimation + value_rating) / 2 if comment.estimation != 0 else value_rating
        comment_estimation = comment.estimation
        db_sess.commit()
        rating = Rating()
        rating.author = current_user.id
        rating.value = int(value_rating)
        rating.comment_id = int(request.form.get("comment_id"))
        db_sess = db_session.create_session()
        db_sess.add(rating)
        db_sess.commit()
        return jsonify({"success": True, "new_value_comment": comment_estimation})
    return jsonify({"success": False})


@app.route("/record/complaint/<int:comment_id>", methods=["POST"])
@login_required
def create_complaint(comment_id):
    try:
        session = db_session.create_session()
        comment = session.query(Comment).get(comment_id)
        comm_is_pending_review = comment.pending_review
        complaint = Complaint()
        complaint.author = current_user.id
        complaint.comment_id = comment_id
        comment.complaints.append(complaint)
        session.merge(comment)
        session.commit()
        if not comm_is_pending_review:
            celery_processing_complaint.apply_async(args=[comment_id], countdown=60)
        return jsonify({'success': 'OK'})
    except Exception:
        return jsonify({'error': 'Fasle'})


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    session = db_session.create_session()
    params = {name: request.args.get(name) for name in ['q']}
    records = []
    records_all = session.query(Record).filter((Record.title.like(f'%{params["q"]}%')) |
                                           (Record.description.like(f'%{params["q"]}%'))).all()
    for record in records_all:
        records.append((record, record.description[:250]))
    param = {}
    param['title'] = 'Работы'
    param['records'] = records
    return render_template('index.html', **param)


if __name__ == '__main__':
    db_session.global_init("db/help.db")
    # для списка объектов
    api.add_resource(record_resources.RecordListResource, '/api/records')

    # для одного объекта
    api.add_resource(record_resources.RecordResource, '/api/record/<int:record_id>')
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
