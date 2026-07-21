from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_cors import CORS
from werkzeug.security import check_password_hash
import database as db
import os
import qrcode
from io import BytesIO
from dotenv import load_dotenv

from backend.yolo.model_loader import get_model, is_model_ready
from backend.yolo.detector import detect_tool, decode_base64_frame
from backend.yolo.classes import normalize_class_name
from email_utils import init_mail, send_email

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret")
CORS(app)
init_mail(app)


@app.route('/')
def index_page():
    if 'employee_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login')
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
    employee = db.get_employee_by_id(session['employee_id'])
    return {
        'name': session.get('name'),
        'emp_id': session.get('employee_id'),
        'company_nam': employee.get('company_nam') if employee else None,
    }


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


def _resolve_tool_id(raw_value):
    """Accepts either a numeric tool_id (from the manual dropdown) or a
    qr_code string like 'HAMMER001' (from the camera scan) and returns
    the matching numeric tool_id, or None if nothing matches."""
    if raw_value is None:
        return None

    raw_value = str(raw_value).strip()
    if not raw_value:
        return None

    if raw_value.isdigit():
        return int(raw_value)

    tool = db.get_tool_by_qr_code(raw_value)
    return tool['tool_id'] if tool else None


# =====================================================================
# MODULE 2: TOOL QR IDENTIFICATION (identify only, no borrow yet)
# =====================================================================

@app.route('/api/tool-lookup')
def api_tool_lookup():
    """Identifies the tool from a scanned QR code without borrowing it."""
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401

    qr_code = request.args.get('qr_code', '').strip()
    if not qr_code:
        return jsonify({"success": False, "message": "qr_code is required."}), 400

    tool = db.get_tool_by_qr_code(qr_code)
    if not tool:
        return jsonify({"success": False, "message": "No tool found for this QR code."}), 404

    return jsonify({
        "success": True,
        "tool_id": tool['tool_id'],
        "tool_name": tool['tool_name'],
        "available_qty": tool['available_qty'],
        "status": "Available" if tool['available_qty'] > 0 else "Out of Stock"
    })


# =====================================================================
# AI VERIFICATION MODULE (QR + YOLO cross-check)
# =====================================================================

def verify_tool_with_yolo(qr_code, image_data=None):
    """
    Compares the tool expected by the scanned QR code against what YOLO
    detects in the camera frame.

    Falls back to matched=True (QR-only) if the YOLO model isn't ready yet
    or no image was sent — so the existing QR flow never breaks.
    """
    tool = db.get_tool_by_qr_code(qr_code)
    if not tool:
        return {
            "matched": False,
            "expected_class": None,
            "detected_class": None,
            "confidence": None,
            "message": "QR code does not match any tool in the system."
        }

    expected_class      = tool.get('yolo_class')
    expected_class_norm = normalize_class_name(expected_class) if expected_class else None

    if not is_model_ready() or not image_data or not expected_class:
        return {
            "matched": True,
            "expected_class": expected_class,
            "detected_class": None,
            "confidence": None,
            "message": "YOLO verification skipped — QR match accepted."
        }

    try:
        frame = decode_base64_frame(image_data)
        detection = detect_tool(frame)
    except Exception as e:
        return {
            "matched": True,
            "expected_class": expected_class,
            "detected_class": None,
            "confidence": None,
            "message": f"YOLO check skipped (error): {e}"
        }

    if detection is None:
        return {
            "matched": False,
            "expected_class": expected_class,
            "detected_class": None,
            "confidence": None,
            "message": "No tool detected in camera frame. Hold the tool clearly in view and try again."
        }

    detected_class = detection["class_name"]
    confidence     = detection["confidence"]
    matched        = (detected_class == expected_class_norm)

    return {
        "matched": matched,
        "expected_class": expected_class,
        "detected_class": detected_class,
        "confidence": confidence,
        "message": "Tool verified ✔" if matched else
                   f"Camera sees '{detected_class}', expected '{expected_class}'."
    }


@app.route('/api/verify-tool', methods=['POST'])
def api_verify_tool():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401

    data       = request.get_json()
    qr_code    = data.get('qr_code', '').strip()
    image_data = data.get('image')

    if not qr_code:
        return jsonify({"success": False, "message": "qr_code is required."}), 400

    result = verify_tool_with_yolo(qr_code, image_data)
    return jsonify({"success": True, **result})


@app.route('/api/borrow', methods=['POST'])
def api_borrow():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    data     = request.get_json()
    raw      = data.get('tool_id')
    due_date = data.get('due_date')  # optional, 'YYYY-MM-DD'
    quantity = data.get('quantity', 1)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(1, quantity)

    tool_id = _resolve_tool_id(raw)
    if tool_id is None:
        return jsonify({"success": False, "message": "Invalid QR code — no matching tool found."}), 400

    ok, message, tool_name = db.borrow_tool(session['employee_id'], tool_id, due_date, quantity)

    if ok:
        db.create_notification(
            session['employee_id'], tool_id, 'borrow',
            f"You borrowed {tool_name}. Due in 5 days."
        )
        employee = db.get_employee_by_id(session['employee_id'])
        if employee and employee.get('email'):
            send_email(
                employee['email'],
                "Tool Borrowed — S-Tool Tracking",
                f"Hi {employee['name']},\n\nYou've borrowed: {tool_name}\nDue date: within 5 days.\n\n— S-Tool Tracking System"
            )
        tool = db.get_tool_by_id(tool_id)
        if tool and tool['available_qty'] <= (tool.get('min_stock_threshold') or 2):
            db.create_notification(
                None, tool_id, 'low_stock',
                f"{tool['tool_name']} is low on stock ({tool['available_qty']} left)."
            )

    return jsonify({"success": ok, "message": message, "tool_name": tool_name}), (200 if ok else 400)


@app.route('/api/return', methods=['POST'])
def api_return():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    data = request.get_json()
    raw  = data.get('tool_id')

    tool_id = _resolve_tool_id(raw)
    if tool_id is None:
        return jsonify({"success": False, "message": "Invalid QR code — no matching tool found."}), 400

    rows = db.get_employee_active_transactions(session['employee_id'])
    match = next((r for r in rows if r['tool_id'] == tool_id), None)
    if not match:
        tool = db.get_tool_by_id(tool_id)
        name = tool['tool_name'] if tool else 'This tool'
        return jsonify({"success": False, "message": f"{name} is not currently borrowed by you."}), 400

    ok, message, tool_name = db.return_tool(match['transaction_id'])

    if ok:
        db.create_notification(
            session['employee_id'], tool_id, 'return',
            f"You returned {tool_name}."
        )
        employee = db.get_employee_by_id(session['employee_id'])
        if employee and employee.get('email'):
            send_email(
                employee['email'],
                "Tool Returned — S-Tool Tracking",
                f"Hi {employee['name']},\n\nYou've returned: {tool_name}.\n\nThanks!\n— S-Tool Tracking System"
            )

    return jsonify({"success": ok, "message": message, "tool_name": tool_name}), (200 if ok else 400)


# =====================================================================
# NOTIFICATIONS API
# =====================================================================

@app.route('/api/notifications')
def api_notifications():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    notifs = db.get_employee_notifications(session['employee_id'])
    unread = db.get_unread_count(session['employee_id'])
    return jsonify({"success": True, "notifications": _serialize_rows(notifs), "unread_count": unread})


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def api_mark_notification_read(notification_id):
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_notification_read(notification_id)
    return jsonify({"success": True})


@app.route('/api/notifications/mark-all-read', methods=['POST'])
def api_mark_all_read():
    if not _require_employee():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_all_read(session['employee_id'])
    return jsonify({"success": True})


@app.route('/api/admin/notifications')
def api_admin_notifications():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    notifs = db.get_admin_notifications()
    unread = db.get_unread_count(None)
    return jsonify({"success": True, "notifications": _serialize_rows(notifs), "unread_count": unread})


@app.route('/api/admin/notifications/mark-all-read', methods=['POST'])
def api_admin_mark_all_read():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_all_read(None)
    return jsonify({"success": True})


@app.route('/api/admin/run-checks', methods=['POST'])
def api_admin_run_checks():
    """Manual trigger for due-tomorrow / overdue / low-stock checks."""
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401

    db.mark_overdue_transactions()

    due_soon = db.get_transactions_due_tomorrow()
    for t in due_soon:
        db.create_notification(t['employee_id'], None, 'due_soon',
            f"{t['tool_name']} is due tomorrow ({t['due_date']}).")
        if t.get('email'):
            send_email(t['email'], "Reminder: Tool Due Tomorrow",
                f"Hi {t['employee_name']},\n\n{t['tool_name']} is due tomorrow.\n\n— S-Tool Tracking")

    overdue = db.get_newly_overdue_transactions()
    for t in overdue:
        db.create_notification(t['employee_id'], None, 'overdue',
            f"{t['tool_name']} is overdue! Please return it ASAP.")
        db.create_notification(None, None, 'overdue',
            f"{t['employee_name']} has an overdue tool: {t['tool_name']}.")
        if t.get('email'):
            send_email(t['email'], "Overdue Tool Alert",
                f"Hi {t['employee_name']},\n\n{t['tool_name']} is overdue. Please return it.\n\n— S-Tool Tracking")

    low_stock = db.get_low_stock_tools()
    for tool in low_stock:
        db.create_notification(None, tool['tool_id'], 'low_stock',
            f"{tool['tool_name']} is low on stock ({tool['available_qty']} left).")

    return jsonify({
        "success": True,
        "message": f"Checked: {len(due_soon)} due soon, {len(overdue)} overdue, {len(low_stock)} low stock."
    })


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


@app.route('/api/admin/employees', methods=['GET', 'POST'])
def api_admin_employees():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        ok, message = db.add_employee(
            data.get('employee_id', '').strip(),
            data.get('name', '').strip(),
            data.get('company_name', '').strip() or None,
            data.get('contact_no', '').strip() or None,
            data.get('email', '').strip() or None,
        )
        return jsonify({"success": ok, "message": message}), (200 if ok else 400)

    return jsonify({"success": True, "employees": db.get_all_employees()})


@app.route('/api/admin/employees/<employee_id>/qr')
def api_admin_employee_qr(employee_id):
    """Generates a QR code PNG that encodes the employee_id itself —
    same value used for login scanning."""
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401

    employee = db.get_employee_by_id(employee_id)
    if not employee:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    img = qrcode.make(employee['employee_id'])
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', download_name=f"{employee['employee_id']}_qr.png")


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
            data.get('qr_code', '').strip() or None,
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
    db.update_tool(
        tool_id,
        data.get('tool_name', '').strip(),
        data.get('category', '').strip(),
        data.get('qr_code', '').strip() or None,
    )
    return jsonify({"success": True})


@app.route('/api/admin/tools/<int:tool_id>/qr')
def api_admin_tool_qr(tool_id):
    """Generates a QR code PNG that encodes this tool's qr_code string
    (e.g. 'HAMMER001'), not the numeric tool_id."""
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401

    tool = db.get_tool_by_id(tool_id)
    if not tool:
        return jsonify({"success": False, "message": "Tool not found."}), 404

    qr_value = tool.get('qr_code') or str(tool_id)
    img = qrcode.make(qr_value)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', download_name=f'{qr_value}_qr.png')


@app.route('/api/admin/transactions')
def api_admin_transactions():
    if not _require_admin():
        return jsonify({"success": False, "message": "Not logged in."}), 401
    db.mark_overdue_transactions()
    status_filter = request.args.get('status')
    date_filter    = request.args.get('range')
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