from flask import redirect, make_response, jsonify
from flask_restful import reqparse, abort, Api, Resource
from data import db_session
from data.records import Record
from data.users import User
from data.comments import Comment
from data.ratings import Rating


parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('description', required=True)
parser.add_argument('cost', required=True)
parser.add_argument('email', required=True)
parser.add_argument('password', required=True)


def abort_if_record_not_found(record_id):
    """Проверка существования записи"""
    session = db_session.create_session()
    record = session.query(Record).get(record_id)
    if not record:
        abort(404, message=f"Record {record_id} not found")


def check_money(user, cost_record):
    """Проверка наличия денег у пользователся для создания новой записи"""
    return int(user.points) >= int(cost_record)


class RecordResource(Resource):
    """Объект ресурсов записей, для получения и удаления одной записи"""
    def get(self, record_id):
        abort_if_record_not_found(record_id)
        session = db_session.create_session()
        record = session.query(Record).get(record_id)
        return jsonify({'record': record.to_dict(
            only=('title', 'description', 'cost', 'is_finished', 'user.name'))})

    def delete(self, record_id):
        abort_if_record_not_found(record_id)
        session = db_session.create_session()
        record = session.query(Record).get(record_id)
        session.delete(record)
        session.commit()
        return jsonify({'success': 'OK'})


class RecordListResource(Resource):
    """Объект list ресурсов записей, для получения всех записей и для добавления одной"""
    def get(self):
        session = db_session.create_session()
        records = session.query(Record).all()
        return jsonify({'records': [record.to_dict(
            only=('title', 'description', 'cost', 'is_finished', 'user', 'comments')) for record in records]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        current_user = session.query(User).filter(User.email == args['email']).first()
        if current_user and \
                (current_user.check_password(args['email']) or current_user.hashed_password == args['password']):
            if check_money(current_user, args['cost']):
                session = db_session.create_session()
                current_user = session.query(User).filter(User.email == args['email']).first()
                record = Record(
                    author=current_user.id,
                    title=args['title'],
                    description=args['description'],
                    cost=int(args['cost'])
                )
                current_user.records.append(record)
                session.merge(current_user)
                session.commit()
                session = db_session.create_session()
                current_user = session.query(User).filter(User.email == args['email']).first()
                current_user.points -= int(args['cost'])
                session.commit()
                return jsonify({'success': 'OK'})
            return jsonify({'error': 'insufficient funds'})
        return jsonify({'error': 'user not login'})