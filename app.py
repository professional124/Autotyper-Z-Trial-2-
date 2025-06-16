from flask import Flask, render_template_string, request, jsonify
from threading import Thread
import re
import logging

# Import the big bot manager class from your bot.py
from bot import AutoTyperBotManager, BotTask

app = Flask(__name__)
manager = AutoTyperBotManager()

# Enable debug logging for Flask app
logging.basicConfig(level=logging.DEBUG)

# -------------------
# Simple in-memory reviews store (replace with DB or file in real)
REVIEWS = [
    {"user": "Speedster99", "review": "This bot boosted my races like crazy! 10/10."},
    {"user": "TyperQueen", "review": "Easy to use, very reliable and accurate."},
    {"user": "RaceMaster", "review": "Keeps running smoothly for days without a hitch."},
]

# -------------------
# Helper: Validate subscription key format (simple regex, tweak as needed)
def is_valid_subscription_key(key: str) -> bool:
    # Only alphanumeric and underscores allowed, length 6-30 for example
    return bool(re.fullmatch(r"\w{6,30}", key))


# -------------------
# ROUTES

# Homepage - Info, bot stats, and reviews
@app.route("/")
def home():
    stats = manager.get_stats()
    # Simple standalone HTML page with embedded stats and reviews
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>AutoTyper-Z Bot - Home</title>
        <style>
            body {{ background-color: #000; color: #0ff; font-family: Arial, sans-serif; }}
            .container {{ max-width: 800px; margin: auto; padding: 20px; }}
            h1 {{ text-align: center; }}
            .stats, .reviews {{ background: #111; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
            .review {{ border-bottom: 1px solid #222; padding: 10px 0; }}
            .review:last-child {{ border-bottom: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AutoTyper-Z Nitrotype Bot</h1>
            <p>The most reliable Nitrotype bot with customizable speed, accuracy, and proxy support.</p>
            <h2>Pricing</h2>
            <p><strong>Cost:</strong> 500 NTC per subscription</p>
            <div class="stats">
                <h3>Bot Stats</h3>
                <ul>
                    <li>Total Races Botted: {stats['total_races_botted']}</li>
                    <li>Total Accounts Botted: {stats['total_accounts_botted']}</li>
                    <li>Days Online: {stats['uptime_seconds'] // 86400}</li>
                </ul>
            </div>
            <div class="reviews">
                <h3>User Reviews</h3>
                {"".join(f'<div class="review"><strong>{r["user"]}</strong>: {r["review"]}</div>' for r in REVIEWS)}
            </div>
            <p>Go to the <a href="/tasks">Tasks Page</a> to view and add tasks.</p>
        </div>
    </body>
    </html>
    """
    return html


# Tasks page - show active and queued tasks + add task modal
@app.route("/tasks")
def tasks():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>AutoTyper-Z Bot - Tasks</title>
        <style>
            body { background-color: #000; color: #0ff; font-family: Arial, sans-serif; }
            .container { max-width: 900px; margin: auto; padding: 20px; }
            h1 { text-align: center; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #0ff; padding: 8px; text-align: center; }
            th { background-color: #022; }
            tr:nth-child(even) { background-color: #011; }
            button { background-color: #0ff; border: none; color: #000; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 6px; }
            button:hover { background-color: #0cc; }
            #addTaskBtn { position: fixed; bottom: 30px; right: 30px; }
            /* Modal styles */
            #modalOverlay {
                display: none;
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background-color: rgba(0,0,0,0.85);
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            #modalContent {
                background: #111;
                padding: 20px;
                border-radius: 10px;
                width: 350px;
                color: #0ff;
            }
            input, select {
                width: 100%;
                margin-bottom: 15px;
                padding: 8px;
                background: #222;
                border: 1px solid #0ff;
                color: #0ff;
                border-radius: 5px;
            }
            label { font-weight: bold; margin-bottom: 5px; display: block; }
            .error { color: #f66; margin-bottom: 10px; }
            #closeModalBtn {
                background-color: #f00;
                color: #fff;
                border: none;
                padding: 5px 10px;
                float: right;
                cursor: pointer;
                border-radius: 5px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Active & Queued Bot Tasks</h1>
            <table id="tasksTable">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Races Done</th>
                        <th>Total Races</th>
                        <th>Avg WPM</th>
                        <th>Min Accuracy</th>
                        <th>Proxy</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="tasksBody">
                    <!-- Filled by JS -->
                </tbody>
            </table>
            <button id="addTaskBtn">Add Task</button>
        </div>

        <!-- Modal -->
        <div id="modalOverlay">
            <div id="modalContent">
                <button id="closeModalBtn">X</button>
                <h2>Add New Task</h2>
                <div id="errorMsg" class="error"></div>
                <form id="taskForm">
                    <label for="username">Username</label>
                    <input id="username" name="username" type="text" required />

                    <label for="password">Password</label>
                    <input id="password" name="password" type="password" required />

                    <label for="avg_wpm">Average WPM (10-180)</label>
                    <input id="avg_wpm" name="avg_wpm" type="number" min="10" max="180" value="80" required />

                    <label for="min_acc">Minimum Accuracy % (85-97)</label>
                    <input id="min_acc" name="min_acc" type="number" min="85" max="97" value="90" required />

                    <label for="num_races">Number of Races</label>
                    <input id="num_races" name="num_races" type="number" min="1" max="50" value="5" required />

                    <label for="subscription_key">Subscription Key</label>
                    <input id="subscription_key" name="subscription_key" type="text" required />

                    <button type="submit">Submit Task</button>
                </form>
            </div>
        </div>

        <script>
            const addTaskBtn = document.getElementById("addTaskBtn");
            const modalOverlay = document.getElementById("modalOverlay");
            const closeModalBtn = document.getElementById("closeModalBtn");
            const taskForm = document.getElementById("taskForm");
            const errorMsg = document.getElementById("errorMsg");
            const tasksBody = document.getElementById("tasksBody");

            // Show modal
            addTaskBtn.addEventListener("click", () => {
                errorMsg.textContent = "";
                taskForm.reset();
                modalOverlay.style.display = "flex";
            });

            // Close modal
            closeModalBtn.addEventListener("click", () => {
                modalOverlay.style.display = "none";
            });

            // Submit form
            taskForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                errorMsg.textContent = "";

                const formData = {
                    username: taskForm.username.value.trim(),
                    password: taskForm.password.value.trim(),
                    avg_wpm: parseInt(taskForm.avg_wpm.value),
                    min_acc: parseInt(taskForm.min_acc.value),
                    num_races: parseInt(taskForm.num_races.value),
                    subscription_key: taskForm.subscription_key.value.trim()
                };

                // Basic client validation
                if (!formData.username || !formData.password) {
                    errorMsg.textContent = "Username and password are required.";
                    return;
                }
                if (formData.avg_wpm < 10 || formData.avg_wpm > 180) {
                    errorMsg.textContent = "Average WPM must be between 10 and 180.";
                    return;
                }
                if (formData.min_acc < 85 || formData.min_acc > 97) {
                    errorMsg.textContent = "Minimum accuracy must be between 85% and 97%.";
                    return;
                }
                if (formData.num_races < 1 || formData.num_races > 50) {
                    errorMsg.textContent = "Number of races must be between 1 and 50.";
                    return;
                }
                if (!formData.subscription_key) {
                    errorMsg.textContent = "Subscription key is required.";
                    return;
                }

                // Send to backend
                try {
                    const res = await fetch("/api/add_task", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(formData)
                    });
                    const data = await res.json();
                    if (data.success) {
                        modalOverlay.style.display = "none";
                        fetchTasks();
                    } else {
                        errorMsg.textContent = data.error || "Unknown error.";
                    }
                } catch (err) {
                    errorMsg.textContent = "Failed to submit task.";
                }
            });

            // Fetch and display tasks every 5 seconds
            async function fetchTasks() {
                try {
                    const res = await fetch("/api/tasks");
                    const data = await res.json();
                    tasksBody.innerHTML = "";
                    data.tasks.forEach(task => {
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td>${task.username}</td>
                            <td>${task.races_done}</td>
                            <td>${task.num_races}</td>
                            <td>${task.avg_wpm}</td>
                            <td>${task.min_acc}%</td>
                            <td>${task.proxy || "None"}</td>
                            <td><button onclick="stopTask('${task.username}')">Stop</button></td>
                        `;
                        tasksBody.appendChild(tr);
                    });
                } catch (e) {
                    console.error("Failed to fetch tasks:", e);
                }
            }

            // Stop a running task
            async function stopTask(username) {
                if (!confirm(`Stop task for user ${username}?`)) return;
                try {
                    const res = await fetch("/api/stop_task", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ username })
                    });
                    const data = await res.json();
                    if (data.success) {
                        fetchTasks();
                    } else {
                        alert(data.error || "Failed to stop task.");
                    }
                } catch (e) {
                    alert("Error stopping task.");
                }
            }

            // Initial fetch
            fetchTasks();

            // Refresh tasks every 5 seconds
            setInterval(fetchTasks, 5000);
        </script>
    </body>
    </html>
    """
    return html


# -------------------
# API ENDPOINTS

@app.route("/api/add_task", methods=["POST"])
def api_add_task():
    data = request.get_json(force=True)
    required_fields = ["username", "password", "avg_wpm", "min_acc", "num_races", "subscription_key"]
    if not all(field in data for field in required_fields):
        return jsonify(success=False, error="Missing required fields.")

    username = data["username"].strip()
    password = data["password"].strip()
    try:
        avg_wpm = int(data["avg_wpm"])
        min_acc = int(data["min_acc"])
        num_races = int(data["num_races"])
    except ValueError:
        return jsonify(success=False, error="WPM, accuracy, and races must be integers.")

    subscription_key = data["subscription_key"].strip()

    # Validate inputs on server-side
    if not username or not password:
        return jsonify(success=False, error="Username and password are required.")
    if not (MIN_WPM <= avg_wpm <= MAX_WPM):
        return jsonify(success=False, error=f"Average WPM must be between {MIN_WPM} and {MAX_WPM}.")
    if not (MIN_ACC <= min_acc <= MAX_ACC):
        return jsonify(success=False, error=f"Minimum accuracy must be between {MIN_ACC}% and {MAX_ACC}%.")
    if not (1 <= num_races <= 50):
        return jsonify(success=False, error="Number of races must be between 1 and 50.")
    if not is_valid_subscription_key(subscription_key):
        return jsonify(success=False, error="Invalid subscription key format.")

    task = BotTask(username, password, avg_wpm, min_acc, num_races, subscription_key)
    added = manager.add_task(task)
    if added:
        return jsonify(success=True)
    else:
        return jsonify(success=False, error="Failed to add task. Check if subscription key is valid or task is duplicate.")


@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    tasks = []
    active = manager.get_active_tasks()
    # Convert active tasks dict to list for frontend
    for username, info in active.items():
        tasks.append({
            "username": username,
            "races_done": info.get("races_done", 0),
            "num_races": info.get("num_races", 0),
            "avg_wpm": info.get("avg_wpm", 0),
            "min_acc": info.get("min_acc", 0),
            "proxy": info.get("proxy")
        })
    return jsonify(tasks=tasks)


@app.route("/api/stop_task", methods=["POST"])
def api_stop_task():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    if not username:
        return jsonify(success=False, error="Username is required.")
    manager.stop_task(username)
    return jsonify(success=True)


# -------------------
# RUN THE APP

if __name__ == "__main__":
    # Run Flask app in threaded mode so bot manager threads can run simultaneously
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
