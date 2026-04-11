import os
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
BOT_API_URL = os.getenv("BOT_API_URL")
API_SECRET = os.getenv("API_SECRET")
JWT_SECRET = os.getenv("SECRET_KEY")

# TEMP STORAGE (replace with DB later)
user_claims = {}

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

    # Exchange code for token
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

    # Get user info
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = user_res["id"]
    username = user_res["username"]
    avatar = user_res["avatar"]

    # Avatar URL
    if avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    # Create JWT token
    payload = {
        "user_id": user_id,
        "username": username,
        "avatar": avatar_url,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    # Redirect to frontend with token
    return redirect(f"https://enjoybot.hostedbyfps.com/?token={token}")

# ================= CLAIM DAILY =================
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
    today = str(datetime.date.today())

    if user_claims.get(user_id) == today:
        return jsonify({"message": "❌ Already claimed today"})

    user_claims[user_id] = today

    # Call bot API
    try:
        requests.post(
            BOT_API_URL,
            json={"user_id": user_id},
            headers={"Authorization": API_SECRET},
            timeout=5
        )
    except Exception as e:
        return jsonify({"message": f"❌ Bot error: {str(e)}"}), 500

    return jsonify({"message": "✅ Daily claimed successfully!"})

# ================= PROFILE API =================
@app.route("/profile/<user_id>")
def profile(user_id):
    # Dummy data (replace with DB later)
    return jsonify({
        "user_id": user_id,
        "username": "User",
        "avatar": "https://cdn.discordapp.com/embed/avatars/0.png",
        "coins": 100,
        "streak": 1
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
