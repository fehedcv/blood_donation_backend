import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import json
import base64
import re

# Load environment variables
load_dotenv()

# Secure Firebase API Key from .env
API_KEY = os.getenv("FIREBASE_API_KEY")

# Decode `credentials.json` from Base64
cred_json = os.getenv("FIREBASE_CREDENTIALS")
if cred_json:
    cred_dict = json.loads(base64.b64decode(cred_json).decode())  # Decode & parse JSON
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🔥 FIREBASE_CREDENTIALS environment variable is missing!")

# Initialize Flask app
app = Flask(__name__)

# Restrict CORS (Replace with your frontend domain)
CORS(app, resources={r"/*": {"origins": ["https://blood-dontaion-frontend.onrender.com/"]}})  # Replace with actual domain

### 🔹 HELPER FUNCTIONS ###
# Verify Firebase Auth Token
def verify_token(id_token):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
    response = requests.post(url, json={"idToken": id_token})
    return response.status_code == 200

# Prevent XSS by stripping `<script>` tags and `< >` brackets
def sanitize_input(value):
    return re.sub(r'[<>]', '', value) if isinstance(value, str) else value

### 🔹 SIGNUP (User Registration) ###
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password"}), 400

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    response = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})

    if response.status_code == 200:
        return jsonify({"success": True, "message": "User Registered Successfully!"}), 200
    else:
        error_message = response.json().get("error", {}).get("message", "Unknown error")
        return jsonify({"success": False, "message": error_message}), 400

### 🔹 LOGIN ###
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password"}), 400

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    response = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})

    if response.status_code == 200:
        return jsonify({"success": True, "message": "Login Successful!", "idToken": response.json()["idToken"]}), 200
    else:
        error_message = response.json().get("error", {}).get("message", "Unknown error")
        return jsonify({"success": False, "message": error_message}), 400

### 🔹 ADD DONOR TO FIRESTORE (AUTH REQUIRED) ###
@app.route("/add_donor", methods=["POST"])
def add_donor():
    id_token = request.headers.get("Authorization")
    if not id_token or not verify_token(id_token):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json
    name = sanitize_input(data.get("name"))
    blood_type = sanitize_input(data.get("blood_type"))
    phone = sanitize_input(data.get("phone"))
    location = sanitize_input(data.get("location"))

    if not all([name, blood_type, phone, location]):
        return jsonify({"success": False, "message": "Missing donor details"}), 400

    donor_data = {"name": name, "blood_type": blood_type, "phone": phone, "location": location}
    db.collection("donors").add(donor_data)

    return jsonify({"success": True, "message": "Donor added successfully!"}), 200

### 🔹 SEARCH DONORS BY BLOOD TYPE (AUTH REQUIRED) ###
@app.route("/search_blood", methods=["GET"])
def search_blood():
    id_token = request.headers.get("Authorization")
    if not id_token or not verify_token(id_token):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    blood_type = sanitize_input(request.args.get("blood_type", "").strip().upper())

    if not blood_type:
        return jsonify({"success": False, "message": "Missing blood type"}), 400

    donors_ref = db.collection("donors").where("blood_type", "==", blood_type).stream()
    donors_list = [doc.to_dict() for doc in donors_ref]

    if not donors_list:
        return jsonify({"success": False, "message": "No donors found"}), 404

    return jsonify({"success": True, "donors": donors_list}), 200

### 🔹 RUN FLASK APP ###
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
