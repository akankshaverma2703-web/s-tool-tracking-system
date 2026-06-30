import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

dbconfig = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "employee_auth"),
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    **dbconfig
)

def get_connection():
    return connection_pool.get_connection()

def get_employee_by_id(employee_id):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM employees WHERE UPPER(REPLACE(employee_id, ' ', '')) = %s",
        (employee_id.replace(" ", "").upper(),)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result