import psycopg2

from . import config


def get_conn():
    return psycopg2.connect(config.DATABASE_URL)
