"""
db_check.py
This script checks if Postgres and Redis are ready.
"""

import os
import sys
import redis
import psycopg2


def database_check():
    dbname = os.environ['POSTGRES_DB']
    user = os.environ['POSTGRES_USER']
    password = os.environ['POSTGRES_PASSWORD']
    host = os.environ['POSTGRES_HOST']
    port = os.environ['POSTGRES_PORT']

    print(f'DB: {host}:{port}/{dbname}, USER: {user}')

    try:
        psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port)
    except Exception as e:
        print(f'Failed: {e}')
        sys.exit(1)
    else:
        print('Success')


def redis_check():
    host = os.environ['REDIS_HOST']
    port = int(os.environ['REDIS_PORT'])
    password = os.environ['REDIS_PASSWORD']

    print(f'Redis: {host}:{port}')

    try:
        r = redis.Redis(host=host, port=port, password=password, socket_connect_timeout=2)
        r.ping()
    except Exception as e:
        print(f'Failed: {e}')
        sys.exit(1)
    else:
        print('Success')


if __name__ == "__main__":
    database_check()
    redis_check()