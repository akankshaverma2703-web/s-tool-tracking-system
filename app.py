from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import check_password_hash
import database as db
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")
CORS(app)


@app.route('/')
def login_page():
    if 'employee_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def login():
    data        = request.get_json()
    employee_id = data.get('employee_id', '').strip().upper()

    if not employee_id:
        return jsonify({"success": False, "message": "Employee ID is required."}), 400

    employee = db.get_employee_by_id(employee_id)

    if not employee:
        return jsonify({
            "success": False,
            "message": f"Employee not found for ID: {employee_id}"
        }), 404

    session['employee_id'] = employee['employee_id']
    session['name']        = employee['name']

    return jsonify({
        "success": True,
        "message": f"Welcome, {employee['name']}!",
        "redirect": "/dashboard",
        "employee": {
            "employee_id": employee['employee_id'],
            "name":        employee['name'],
            "contact_no":  employee['contact_no'],
        }
    })

@app.route('/api/my-stats')
def my_stats():
    if 'employee_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    employee_id = session['employee_id']
    stats = db.get_employee_stats(employee_id)

    return jsonify({
        "success": True,
        "stats": stats
    })

@app.route('/api/my-tools')
def my_tools():
    if 'employee_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    db.mark_overdue_transactions()
    rows = db.get_employee_active_transactions(session['employee_id'])
    return jsonify({"success": True, "tools": _serialize_rows(rows)})


@app.route('/api/my-history')
def my_history():
    if 'employee_id' not in session:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    rows = db.get_employee_history(session['employee_id'])
    return jsonify({"success": True, "history": _serialize_rows(rows)})


# =====================================================================
# EMPLOYEE DASHBOARD PAGES (each sidebar item = its own route/page)
# =====================================================================

def _employee_context():
    """Returns dict of common template vars, or None if not logged in."""
    if 'employee_id' not in session:
        return None
    return {'name': session.get('name'), 'emp_id': session.get('employee_id')}


@app.route('/dashboard')
def dashboard():
    ctx = _employee_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('dashboard_home.html', active='dashboard', **ctx)


@app.route('/dashboard/scan')
def scan_center():
    ctx = _employee_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('scan_center.html', active='scan', **ctx)


@app.route('/dashboard/my-tools')
def my_tools_page():
    ctx = _employee_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('my_tools.html', active='mytools', **ctx)


@app.route('/dashboard/history')
def history_page():
    ctx = _employee_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('history.html', active='history', **ctx)


@app.route('/dashboard/profile')
def profile_page():
    ctx = _employee_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('profile.html', active='profile', **ctx)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# =====================================================================
# ADMIN AUTH + PAGES (each sidebar item = its own route/page)
# =====================================================================

@app.route('/api/admin-login', methods=['POST'])
def admin_login():
    data     = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required."}), 400

    admin = db.get_admin_by_username(username)

    if not admin or not check_password_hash(admin['password'], password):
        return jsonify({"success": False, "message": "Invalid username or password."}), 401

    session['admin_id']   = admin['id']
    session['admin_name'] = admin['name']

    return jsonify({
        "success": True,
        "message": f"Welcome, {admin['name']}!",
        "redirect": "/admin/dashboard"
    })


def _admin_context():
    """Returns dict of common template vars, or None if not logged in."""
    if 'admin_id' not in session:
        return None
    return {'name': session.get('admin_name')}


@app.route('/admin/dashboard')
def admin_dashboard():
    ctx = _admin_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('admin_dashboard_home.html', active='dashboard', **ctx)


@app.route('/admin/employees')
def admin_employees_page():
    ctx = _admin_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('admin_employees.html', active='employees', **ctx)


@app.route('/admin/tools')
def admin_tools_page():
    ctx = _admin_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('admin_tools.html', active='tools', **ctx)


@app.route('/admin/transactions')
def admin_transactions_page():
    ctx = _admin_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('admin_transactions.html', active='transactions', **ctx)


@app.route('/admin/reports')
def admin_reports_page():
    ctx = _admin_context()
    if ctx is None:
        return redirect(url_for('login_page'))
    return render_template('admin_reports.html', active='reports', **ctx)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('login_page'))


# =====================================================================
# EMPLOYEE DASHBOARD API
# =====================================================================

def _require_employee():
    return 'employee_id' in session


@app.route('/api/employee/summary')
def api_employee_summary():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_overdue_transactions()
    emp_id = session['employee_id']
    return jsonify({
        "success": True,
        "name": session.get('name'),
        "employee_id": emp_id,
        "stats": db.get_employee_stats(emp_id),
    })


@app.route('/api/employee/my-tools')
def api_employee_my_tools():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_overdue_transactions()
    rows = db.get_employee_active_transactions(session['employee_id'])
    return jsonify({"success": True, "tools": _serialize_rows(rows)})


@app.route('/api/employee/history')
def api_employee_history():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    rows = db.get_employee_history(session['employee_id'])
    return jsonify({"success": True, "history": _serialize_rows(rows)})


@app.route('/api/tools/available')
def api_tools_available():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    rows = db.get_available_tools()
    return jsonify({"success": True, "tools": _serialize_rows(rows)})


@app.route('/api/borrow', methods=['POST'])
def api_borrow():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    data    = request.get_json()
    tool_id = data.get('tool_id')
    due_date = data.get('due_date')  # optional, 'YYYY-MM-DD'
    if not tool_id:
        return jsonify({"success": False, "message": "tool_id is required."}), 400

    ok, message = db.borrow_tool(session['employee_id'], tool_id, due_date)
    return jsonify({"success": ok, "message": message}), (200 if ok else 400)

@app.route('/api/return', methods=['POST'])
def api_return():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    data    = request.get_json()
    tool_id = data.get('tool_id')
    if not tool_id:
        return jsonify({"success": False, "message": "tool_id is required."}), 400

    rows = db.get_employee_active_transactions(session['employee_id'])
    match = next((r for r in rows if r['tool_id'] == int(tool_id)), None)
    if not match:
        return jsonify({"success": False, "message": "No active borrow found for this tool."}), 400

    ok, message = db.return_tool(match['transaction_id'])
    return jsonify({"success": ok, "message": message}), (200 if ok else 400)

# =====================================================================
# ADMIN DASHBOARD API
# =====================================================================

def _require_admin():
    return 'admin_id' in session


@app.route('/api/admin/summary')
def api_admin_summary():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_overdue_transactions()
    return jsonify({"success": True, "stats": db.get_admin_stats()})


@app.route('/api/admin/employees')
def api_admin_employees():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    return jsonify({"success": True, "employees": db.get_all_employees()})


@app.route('/api/admin/tools', methods=['GET', 'POST'])
def api_admin_tools():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    if request.method == 'POST':
        data = request.get_json()
        new_id = db.add_tool(
            data.get('tool_name', '').strip(),
            data.get('category', '').strip(),
            data.get('total_qty', 1),
        )
        return jsonify({"success": True, "tool_id": new_id})
    return jsonify({"success": True, "tools": _serialize_rows(db.get_all_tools())})


@app.route('/api/admin/tools/<int:tool_id>', methods=['PUT', 'DELETE'])
def api_admin_tool_detail(tool_id):
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    if request.method == 'DELETE':
        db.delete_tool(tool_id)
        return jsonify({"success": True})
    data = request.get_json()
    db.update_tool(tool_id, data.get('tool_name', '').strip(), data.get('category', '').strip())
    return jsonify({"success": True})


@app.route('/api/admin/transactions')
def api_admin_transactions():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_overdue_transactions()
    status_filter = request.args.get('status')  # Active | Returned | Overdue
    date_filter    = request.args.get('range')   # today | week | month
    rows = db.get_all_transactions(status_filter=status_filter, date_filter=date_filter)
    return jsonify({"success": True, "transactions": _serialize_rows(rows)})


def _serialize_rows(rows):
    """Converts date/time/datetime objects to strings so jsonify can handle them."""
    out = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            clean[k] = str(v) if v is not None and not isinstance(v, (int, float, str, bool)) else v
        out.append(clean)
    return out


if __name__ == '__main__':
    app.run(debug=True, port=3000)