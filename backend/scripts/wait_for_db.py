import logging
import os
import re
import time

import psycopg2
from psycopg2 import OperationalError
from psycopg2 import sql


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [wait_for_db] %(message)s'
)
logger = logging.getLogger(__name__)


def build_conn_params() -> dict:
    return {
        'host': os.getenv('DB_HOST', 'db'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'dbname': os.getenv('DB_NAME', 'czxt'),
        'user': os.getenv('DB_USER', 'czxt'),
        'password': os.getenv('DB_PASSWORD', 'Czxt@3598'),
        'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '10')),
        'sslmode': os.getenv('DB_SSLMODE', 'disable'),
    }


def wait_for_db(max_retries: int = 30, delay_seconds: int = 2) -> None:
    conn_params = build_conn_params()
    for attempt in range(1, max_retries + 1):
        try:
            logger.info('Database connection check attempt %s/%s', attempt, max_retries)
            with psycopg2.connect(**conn_params) as conn:
                conn.autocommit = True
                schema = os.getenv('DB_SCHEMA', 'czxt')
                if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', schema):
                    raise RuntimeError('Invalid DB_SCHEMA. Only letters, digits, and underscore are allowed.')
                with conn.cursor() as cursor:
                    cursor.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
                    cursor.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
            logger.info('Database is ready.')
            return
        except OperationalError as exc:
            logger.warning('Database not ready: %s', exc)
            time.sleep(delay_seconds)
    raise RuntimeError('Database connection failed after retries.')


if __name__ == '__main__':
    wait_for_db()
