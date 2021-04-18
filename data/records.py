import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin


class Record(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'records'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    author = sqlalchemy.Column(sqlalchemy.Integer,
                                    sqlalchemy.ForeignKey("users.id"))
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    date_create = sqlalchemy.Column(sqlalchemy.DateTime,
                                   default=datetime.datetime.now)
    cost = sqlalchemy.Column(sqlalchemy.Integer,
                               default=30)
    is_finished = sqlalchemy.Column(sqlalchemy.Boolean,
                                   default=False)
    is_editable = sqlalchemy.Column(sqlalchemy.Boolean,
                                   default=True)
    user = orm.relation('User')
    comments = orm.relation("Comment", back_populates='record')