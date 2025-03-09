import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify,render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Secure Firebase API Key from .env
API_KEY = os.getenv("FIREBASE_API_KEY")

# Initialize Firebase Admin SDK
cred = credentials.Certificate("credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication


### 🔹 USER AUTHENTICATION (Signup & Login) ###

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


### 🔹 ADD DONOR TO FIRESTORE ###
@app.route("/add_donor", methods=["POST"])
def add_donor():
    data = request.json
    name = data.get("name")
    blood_type = data.get("blood_type")
    phone = data.get("phone")
    location = data.get("location")

    if not all([name, blood_type, phone, location]):
        return jsonify({"success": False, "message": "Missing donor details"}), 400

    donor_data = {"name": name, "blood_type": blood_type, "phone": phone, "location": location}
    db.collection("donors").add(donor_data)

    return jsonify({"success": True, "message": "Donor added successfully!"}), 200


### 🔹 SEARCH DONORS BY BLOOD TYPE ###
@app.route("/search_blood", methods=["GET"])
def search_blood():
    blood_type = request.args.get("blood_type", "").strip().upper()
    print(f"🔍 Searching for blood type: '{blood_type}'")  # Debugging log

    if not blood_type:
        return jsonify({"success": False, "message": "Missing blood type"}), 400

    # Firestore query using .where() for exact match
    donors_ref = db.collection("donors").where("blood_type", "==", blood_type).stream()
    donors_list = [doc.to_dict() for doc in donors_ref]

    if not donors_list:
        print("❌ No donors found")  # Debugging log
        return jsonify({"success": False, "message": "No donors found"}), 404

    return jsonify({"success": True, "donors": donors_list}), 200






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)