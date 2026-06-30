from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
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
        return f"<h2>Logged in as {session['name']} ({session['employee_id']})</h2><a href='/logout'>Logout</a>"
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
        "employee": {
            "employee_id": employee['employee_id'],
            "name":        employee['name'],
            "contact_no":  employee['contact_no'],
        }
    })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


if __name__ == '__main__':
    app.run(debug=True, port=3000)