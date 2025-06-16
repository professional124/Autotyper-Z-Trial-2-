from flask import Flask, render_template, request, redirect, url_for, jsonify
from bot_manager import BotManager
import threading

app = Flask(__name__)
bot_manager = BotManager()

@app.route("/", methods=["GET"])
def index():
    # Show form + current active bots
    bots = bot_manager.get_active_bots()
    return render_template("index.html", bots=bots)

@app.route("/start_bot", methods=["POST"])
def start_bot():
    username = request.form.get("username")
    password = request.form.get("password")
    avg_wpm = float(request.form.get("avg_wpm", 40))
    min_accuracy = int(request.form.get("min_accuracy", 95))
    races = int(request.form.get("races", 1))

    if not username or not password:
        return "Username and password are required", 400

    # Start the bot in background thread
    bot_manager.start_bot(username, password, avg_wpm, min_accuracy, races)

    return redirect(url_for("index"))

@app.route("/api/status", methods=["GET"])
def api_status():
    # Return JSON of current bots and race counts
    return jsonify(bot_manager.get_active_bots())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
