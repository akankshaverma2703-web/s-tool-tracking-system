import mysql.connector
from mysql.connector import pooling
import os
from datetime import datetime, date
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


def get_admin_by_username(username):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM admins WHERE username = %s",
        (username,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


# =====================================================================
# TOOLS
# =====================================================================

def get_all_tools():
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tools ORDER BY tool_name")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_available_tools():
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tools WHERE available_qty > 0 ORDER BY tool_name")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_tool_by_id(tool_id):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tools WHERE tool_id = %s", (tool_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def add_tool(tool_name, category, total_qty=1):
    """Creates a new tool with the given starting quantity.
    NOTE: total_qty must be an int. If a non-numeric value (like an old
    qr_code string) is passed by mistake, it falls back to 1."""
    try:
        total_qty = int(total_qty)
    except (TypeError, ValueError):
        total_qty = 1

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tools (tool_name, category, total_qty, available_qty) VALUES (%s, %s, %s, %s)",
        (tool_name, category, total_qty, total_qty)
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id


def update_tool(tool_id, tool_name, category):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tools SET tool_name = %s, category = %s WHERE tool_id = %s",
        (tool_name, category, tool_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_tool(tool_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tools WHERE tool_id = %s", (tool_id,))
    conn.commit()
    cursor.close()
    conn.close()


# =====================================================================
# BORROW / RETURN
# =====================================================================

def borrow_tool(employee_id, tool_id, due_date=None):
    """Creates a new Active transaction and decrements available_qty.
    Returns (success, message)."""
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT available_qty FROM tools WHERE tool_id = %s", (tool_id,))
    tool = cursor.fetchone()
    if not tool:
        cursor.close(); conn.close()
        return False, "Tool not found."
    if tool['available_qty'] <= 0:
        cursor.close(); conn.close()
        return False, "No units available."

    now = datetime.now()
    cursor.execute(
        """INSERT INTO transactions
           (employee_id, tool_id, borrow_date, borrow_time, due_date, status)
           VALUES (%s, %s, %s, %s, %s, 'Active')""",
        (employee_id, tool_id, now.date(), now.time(), due_date)
    )
    cursor.execute(
        "UPDATE tools SET available_qty = available_qty - 1 WHERE tool_id = %s",
        (tool_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return True, "Tool borrowed successfully."


def return_tool(transaction_id):
    """Closes an Active transaction and increments available_qty."""
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
    txn = cursor.fetchone()
    if not txn:
        cursor.close(); conn.close()
        return False, "Transaction not found."
    if txn['status'] == 'Returned':
        cursor.close(); conn.close()
        return False, "Tool already returned."

    now = datetime.now()
    cursor.execute(
        """UPDATE transactions
           SET return_date = %s, return_time = %s, status = 'Returned'
           WHERE transaction_id = %s""",
        (now.date(), now.time(), transaction_id)
    )
    cursor.execute(
        "UPDATE tools SET available_qty = available_qty + 1 WHERE tool_id = %s",
        (txn['tool_id'],)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return True, "Tool returned successfully."


def mark_overdue_transactions():
    """Flips any Active transaction past its due_date to Overdue. Call this
    at the top of any dashboard/report request so the status is always fresh."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE transactions
           SET status = 'Overdue'
           WHERE status = 'Active' AND due_date IS NOT NULL AND due_date < %s""",
        (date.today(),)
    )
    conn.commit()
    cursor.close()
    conn.close()


# =====================================================================
# EMPLOYEE-SIDE QUERIES
# =====================================================================

def get_employee_active_transactions(employee_id):
    """'My Tools' tab — tools currently out with this employee."""
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT t.transaction_id, t.tool_id, tl.tool_name, t.borrow_date, t.borrow_time,
       t.due_date, t.status
           FROM transactions t
           JOIN tools tl ON tl.tool_id = t.tool_id
           WHERE t.employee_id = %s AND t.status IN ('Active', 'Overdue')
           ORDER BY t.borrow_date DESC, t.borrow_time DESC""",
        (employee_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_employee_history(employee_id):
    """'Transaction History' tab — full borrow/return history for one employee."""
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT t.transaction_id, tl.tool_name, t.borrow_date, t.borrow_time,
                  t.return_date, t.return_time, t.due_date, t.status
           FROM transactions t
           JOIN tools tl ON tl.tool_id = t.tool_id
           WHERE t.employee_id = %s
           ORDER BY t.borrow_date DESC, t.borrow_time DESC""",
        (employee_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_employee_stats(employee_id):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS c FROM transactions WHERE employee_id = %s", (employee_id,))
    total_borrowed = cursor.fetchone()['c']

    cursor.execute(
        "SELECT COUNT(*) AS c FROM transactions WHERE employee_id = %s AND status IN ('Active','Overdue')",
        (employee_id,)
    )
    pending_return = cursor.fetchone()['c']

    cursor.execute(
        "SELECT COUNT(*) AS c FROM transactions WHERE employee_id = %s AND status = 'Returned'",
        (employee_id,)
    )
    returned = cursor.fetchone()['c']

    cursor.execute("SELECT COALESCE(SUM(available_qty), 0) AS c FROM tools")
    available_tools = cursor.fetchone()['c']

    cursor.close()
    conn.close()
    return {
        "total_borrowed": total_borrowed,
        "pending_return": pending_return,
        "returned": returned,
        "available_tools": available_tools,
    }


# =====================================================================
# ADMIN-SIDE QUERIES
# =====================================================================

def get_all_employees():
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT employee_id, name, contact_no FROM employees ORDER BY name")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_admin_stats():
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS c FROM employees")
    total_employees = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) AS c FROM tools")
    total_tools = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) AS c FROM transactions WHERE status = 'Active'")
    borrowed = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) AS c FROM transactions WHERE status = 'Returned'")
    returned = cursor.fetchone()['c']

    cursor.execute("SELECT COUNT(*) AS c FROM transactions WHERE status = 'Overdue'")
    overdue = cursor.fetchone()['c']

    cursor.close()
    conn.close()
    return {
        "total_employees": total_employees,
        "total_tools": total_tools,
        "borrowed": borrowed,
        "returned": returned,
        "overdue": overdue,
    }


def get_all_transactions(status_filter=None, date_filter=None):
    """status_filter: 'Active' | 'Returned' | 'Overdue' | None
       date_filter: 'today' | 'week' | 'month' | None"""
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT t.transaction_id, e.employee_id, e.name AS employee_name,
               tl.tool_name, t.borrow_date, t.borrow_time,
               t.return_date, t.return_time, t.due_date, t.status
        FROM transactions t
        JOIN employees e ON e.employee_id = t.employee_id
        JOIN tools tl ON tl.tool_id = t.tool_id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND t.status = %s"
        params.append(status_filter)

    if date_filter == 'today':
        query += " AND t.borrow_date = CURDATE()"
    elif date_filter == 'week':
        query += " AND t.borrow_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
    elif date_filter == 'month':
        query += " AND t.borrow_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"

    query += " ORDER BY t.borrow_date DESC, t.borrow_time DESC"

    cursor.execute(query, tuple(params))
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result