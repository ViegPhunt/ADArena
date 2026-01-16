import os
import sys

import psycopg2

conn = psycopg2.connect(
    host=os.environ['POSTGRES_HOST'],
    port=os.environ['POSTGRES_PORT'],
    dbname=os.environ['POSTGRES_DB'],
    user=os.environ['POSTGRES_USER'],
    password=os.environ['POSTGRES_PASSWORD'],
)
curs = conn.cursor()

query = 'SELECT COUNT(id) from GameConfig'
try:
    curs.execute(query)
except psycopg2.ProgrammingError:
    sys.exit(1)
initialized, = curs.fetchone()

# Exit with 0 if initialized (count > 0), exit 1 if not initialized (count == 0)
sys.exit(0 if initialized > 0 else 1)
