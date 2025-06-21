from db import database
from db.User import User

if __name__ == "__main__":
    database.connect()
    database.create_tables([User], safe=True)