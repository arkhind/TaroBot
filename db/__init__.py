import config
import peewee_async

database = peewee_async.PooledPostgresqlDatabase(
    database=config.PGDATABASE,
    user=config.PGUSER,
    host=config.PGHOST,
    port="5432",
    password=config.PGPASSWORD,
)
