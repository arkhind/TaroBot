import peewee
import peewee_async

from db import database


class User(peewee_async.AioModel):
    user_id = peewee.AutoField(primary_key=True)
    telegram_user_id = peewee.BigIntegerField(unique=True)
    telegram_chat_id = peewee.BigIntegerField()
    language = peewee.TextField(default="ru")
    name = peewee.TextField(null=True)

    class Meta:
        database = database
