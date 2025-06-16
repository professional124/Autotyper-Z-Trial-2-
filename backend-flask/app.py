from flask import Flask, render_template, request, redirect, url_for
from bot_manager import BotManager

app = Flask(__name__)
bot_manager = BotManager()

# Global stats
total_races_botted = 0
unique_accounts_botted = set()

@app.route("/")
def home():
    global total_races_botted, unique_accounts_botted
    return render_template(
        "home.html",
        total_races=total_races_botted,
        total_accounts=len(unique_accounts_botted)
    )

@app.route("/start", methods=["GET", "POST"])
def start_bot():
    global total_races_botted, unique_accounts_botted

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        avg_wpm = int(request.form["avg_wpm"])
        min_accuracy = int(request.form["min_accuracy"])
        races = int(request.form["races"])

        started = bot_manager.start_bot(username, password, avg_wpm, min_accuracy, races)
        if started:
            unique_accounts_botted.add(username)
            total_races_botted += races
            return redirect(url_for("start_bot"))
        else:
            return render_template("start.html", error="Bot is already running for that username.", bots=bot_manager.get_active_bots())

    return render_template("start.html", bots=bot_manager.get_active_bots())

@app.route("/tabs")
def tabs():
    return render_template("tabs.html")

if __name__ == "__main__":
    app.run(debug=True)
