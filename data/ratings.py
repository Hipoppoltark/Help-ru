import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin


class Rating(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'ratings'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    author = sqlalchemy.Column(sqlalchemy.Integer,
                               sqlalchemy.ForeignKey("users.id"))
    value = sqlalchemy.Column(sqlalchemy.Integer)
    comment_id = sqlalchemy.Column(sqlalchemy.Integer,
                               sqlalchemy.ForeignKey("comments.id"))
    user = orm.relation('User')
    comment = orm.relation('Comment')