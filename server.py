import os
from flask import Flask, redirect, request, session, jsonify
import requests
import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

# ENV VARIABLES
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_API_URL = os.getenv("BOT_API_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

app.secret_key = SECRET_KEY

# TEMP STORAGE (replace with DB later)
user_claims = {}

# HOME
@app.route("/")
def home():
    return "Backend Running"

# LOGIN
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

# CALLBACK
@app.route("/callback")
def callback():
    code = request.args.get("code")

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

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    session["user_id"] = user_res["id"]
    session["username"] = user_res["username"]

    return redirect("https://your-website-url.com")

# CLAIM DAILY
@app.route("/claim", methods=["POST"])
def claim():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    user_id = session["user_id"]
    today = str(datetime.date.today())

    if user_claims.get(user_id) == today:
        return jsonify({"message": "Already claimed today"})

    user_claims[user_id] = today

    # Call bot
    requests.post(
        BOT_API_URL,
        json={"user_id": user_id},
        headers={"Authorization": os.getenv("API_SECRET")}
    )

    return jsonify({"message": "✅ Daily claimed successfully!"})


if __name__ == "__main__":
    app.run()
