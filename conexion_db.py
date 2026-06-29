import psycopg2
from psycopg2 import OperationalError
from sqlalchemy import create_engine

def connect_postgres(host, database, user, password, port=5432):
    try:
        connection = psycopg2.connect(host=host,database=database, user=user,password=password,port=port)
        return connection
    except OperationalError as error:
        raise RuntimeError(f"Error connecting to PostgreSQL: {error}")

def engine(host, database, user, password, port=5432):
    try:
        return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")
    except Exception as e:
        print("Error al conectar a Base de Datos")
        return False


