import os
import psycopg2
from flask import Flask, redirect, request, jsonify
import requests
import datetime
import jwt
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
JWT_SECRET = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= DATABASE =================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    last_claim DATE,
    streak INT DEFAULT 0,
    coins INT DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    status TEXT
)
""")

conn.commit()

# ================= HOME =================
@app.route("/")
def home():
    return "Backend Running ✅"

# ================= LOGIN =================
@app.route("/login")
def login():
    discord_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return redirect(discord_url)

# ================= CALLBACK =================
@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "❌ No code provided", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data=data,
        headers=headers
    ).json()

    access_token = token_res.get("access_token")

    if not access_token:
        return "❌ Failed to get access token", 400

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = user_res["id"]
    username = user_res["username"]
    avatar = user_res["avatar"]

    if avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    # Ensure user exists in DB
    cursor.execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,)
    )
    conn.commit()

    payload = {
        "user_id": user_id,
        "username": username,
        "avatar": avatar_url,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return redirect(f"https://enjoybot.hostedbyfps.com/?token={token}")

# ================= CLAIM =================
@app.route("/claim", methods=["POST"])
def claim():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return jsonify({"message": "❌ Not logged in"}), 401

    try:
        token = auth_header.split(" ")[1]
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        return jsonify({"message": "❌ Invalid token"}), 401

    user_id = data["user_id"]

    # Check if already claimed today
    today = datetime.date.today()
    cursor.execute(
        "SELECT last_claim FROM users WHERE user_id=%s",
        (user_id,)
    )
    result = cursor.fetchone()

    if result and result[0] == today:
        return jsonify({"message": "❌ Already claimed today"})

    # Store claim request (bot will process)
    cursor.execute(
        "INSERT INTO claims (user_id, status) VALUES (%s, %s)",
        (user_id, "pending")
    )
    conn.commit()

    return jsonify({"message": "✅ Claim request sent!"})

# ================= PROFILE =================
@app.route("/profile/<user_id>")
def profile(user_id):
    cursor.execute(
        "SELECT coins, streak FROM users WHERE user_id=%s",
        (user_id,)
    )
    data = cursor.fetchone()

    if not data:
        return jsonify({
            "user_id": user_id,
            "coins": 0,
            "streak": 0
        })

    return jsonify({
        "user_id": user_id,
        "coins": data[0],
        "streak": data[1]
    })

# ================= CURRENT USER =================
@app.route("/me")
def me():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return jsonify({"message": "Not logged in"})

    try:
        token = auth_header.split(" ")[1]
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return jsonify(data)
    except:
        return jsonify({"message": "Invalid token"})

# ================= RUN =================
if __name__ == "__main__":
    app.run()
