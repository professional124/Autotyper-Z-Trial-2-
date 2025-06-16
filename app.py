import os
import json
import threading
import time
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort

app = Flask(__name__)

# --- Config & Constants ---
TASKS_FILE = "task_data.json"
KEYS_FILE = "valid_keys.json"
MAX_TASKS_PER_KEY = 3
MAX_CONCURRENT_TASKS = 3
TASK_STATUS_QUEUED = "queued"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"
TASK_PURGE_DAYS = 7

# Locks for thread safety on shared files
file_lock = threading.Lock()

# In-memory thread pool for task runners
running_threads = []
running_threads_lock = threading.Lock()

# ==================== Helper Classes & Functions ====================

class TaskManager:
    """
    Manages the lifecycle of tasks: add, update, save/load from disk,
    purge old tasks, concurrency control, and logging.
    """
    
    def __init__(self, tasks_file=TASKS_FILE):
        self.tasks_file = tasks_file
        self.lock = file_lock  # Use shared lock for all file I/O

    def load_tasks(self):
        with self.lock:
            if not os.path.exists(self.tasks_file):
                return []
            with open(self.tasks_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []

    def save_tasks(self, tasks):
        with self.lock:
            with open(self.tasks_file, "w") as f:
                json.dump(tasks, f, indent=2)

    def add_task(self, task):
        tasks = self.load_tasks()
        tasks.append(task)
        self.save_tasks(tasks)

    def update_task(self, task_id, **kwargs):
        tasks = self.load_tasks()
        updated = False
        for task in tasks:
            if task["id"] == task_id:
                for k, v in kwargs.items():
                    task[k] = v
                updated = True
                break
        if updated:
            self.save_tasks(tasks)
        return updated

    def get_task(self, task_id):
        tasks = self.load_tasks()
        for task in tasks:
            if task["id"] == task_id:
                return task
        return None

    def find_tasks_by_key(self, subscription_key, active_only=True):
        tasks = self.load_tasks()
        if active_only:
            return [t for t in tasks if t.get("subscription_key") == subscription_key and t["status"] in [TASK_STATUS_QUEUED, TASK_STATUS_RUNNING]]
        else:
            return [t for t in tasks if t.get("subscription_key") == subscription_key]

    def purge_old_tasks(self):
        """
        Remove tasks that are completed or failed and older than TASK_PURGE_DAYS
        """
        tasks = self.load_tasks()
        now = datetime.utcnow()
        new_tasks = []
        for t in tasks:
            created = datetime.fromisoformat(t["created_at"].replace("Z", ""))
            age_days = (now - created).days
            if t["status"] in [TASK_STATUS_COMPLETED, TASK_STATUS_FAILED] and age_days >= TASK_PURGE_DAYS:
                # Skip old completed/failed tasks
                continue
            new_tasks.append(t)
        if len(new_tasks) != len(tasks):
            self.save_tasks(new_tasks)

    def total_stats(self):
        """
        Compute overall stats for homepage display
        """
        tasks = self.load_tasks()
        total_races = sum(t.get("races_botted", 0) for t in tasks)
        total_accounts = len(tasks)
        days_online = (datetime.utcnow() - datetime(2024, 12, 1)).days
        return {
            "total_races": total_races,
            "total_accounts": total_accounts,
            "days_online": days_online
        }

    def get_all_tasks(self):
        return self.load_tasks()


class SubscriptionManager:
    """
    Manages subscription keys and usage limits.
    """
    def __init__(self, keys_file=KEYS_FILE):
        self.keys_file = keys_file
        self.lock = file_lock

    def load_keys(self):
        with self.lock:
            if not os.path.exists(self.keys_file):
                return []
            with open(self.keys_file, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []

    def is_valid_key(self, key):
        keys = self.load_keys()
        return key in keys

    def can_use_key(self, key, task_manager: TaskManager):
        active_tasks = task_manager.find_tasks_by_key(key, active_only=True)
        if len(active_tasks) >= MAX_TASKS_PER_KEY:
            return False
        return True


def generate_task_id():
    return str(uuid.uuid4())

def iso_now():
    return datetime.utcnow().isoformat() + "Z"

# ==================== Task Runner Logic ====================

def simulate_typing_task(task_id, task_manager: TaskManager):
    """
    Simulate the bot running typing races. This function runs in a background thread.
    """
    print(f"[TaskRunner] Starting task {task_id}")
    while True:
        task = task_manager.get_task(task_id)
        if not task:
            print(f"[TaskRunner] Task {task_id} disappeared, exiting.")
            break

        status = task["status"]
        if status in [TASK_STATUS_COMPLETED, TASK_STATUS_FAILED]:
            print(f"[TaskRunner] Task {task_id} finished with status {status}")
            break

        if status == TASK_STATUS_QUEUED:
            # Mark as running and add log
            task_manager.update_task(task_id,
                                     status=TASK_STATUS_RUNNING,
                                     logs=task["logs"] + [{
                                        "timestamp": iso_now(),
                                        "message": "Task started running"
                                     }])
            continue

        # If running, simulate typing races
        try:
            races_done = task.get("races_botted", 0)
            total_races = task["how_many_races"]

            if races_done < total_races:
                # Simulate race time delay
                time.sleep(4)  # 4 seconds per race for demo

                # Update race count and logs
                new_log = {
                    "timestamp": iso_now(),
                    "message": f"Completed race {races_done + 1}/{total_races}"
                }
                new_races_botted = races_done + 1
                updated_logs = task["logs"] + [new_log]

                task_manager.update_task(task_id, races_botted=new_races_botted, logs=updated_logs)
            else:
                # Completed all races
                new_log = {
                    "timestamp": iso_now(),
                    "message": "Task completed successfully"
                }
                updated_logs = task["logs"] + [new_log]

                task_manager.update_task(task_id, status=TASK_STATUS_COMPLETED, logs=updated_logs)
                break
        except Exception as e:
            new_log = {
                "timestamp": iso_now(),
                "message": f"Error occurred: {str(e)}"
            }
            task_manager.update_task(task_id, status=TASK_STATUS_FAILED, logs=task["logs"] + [new_log])
            break

    # Remove from running threads list on exit
    with running_threads_lock:
        for t in running_threads:
            if t.name == task_id:
                running_threads.remove(t)
                print(f"[TaskRunner] Removed thread for task {task_id}")
                break
    print(f"[TaskRunner] Exiting task {task_id}")

def start_task_threads(task_manager: TaskManager):
    """
    Start new threads for queued tasks if under concurrency limit.
    """
    with running_threads_lock:
        tasks = task_manager.get_all_tasks()
        running_count = len(running_threads)

        for task in tasks:
            if task["status"] == TASK_STATUS_QUEUED and running_count < MAX_CONCURRENT_TASKS:
                task_id = task["id"]
                # Check if thread already running
                if any(t.name == task_id for t in running_threads):
                    continue

                thread = threading.Thread(target=simulate_typing_task, args=(task_id, task_manager), name=task_id, daemon=True)
                thread.start()
                running_threads.append(thread)
                running_count += 1
                print(f"[TaskRunner] Spawned thread for task {task_id}")

# ==================== Validation & Utilities ====================

def validate_task_form(form):
    """
    Validate submitted form data for creating a new task.
    Returns (is_valid:bool, message:str)
    """
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()
    avg_wpm = form.get("avg_wpm")
    min_accuracy = form.get("min_accuracy")
    how_many_races = form.get("how_many_races")
    subscription_key = form.get("subscription_key", "").strip()

    if not username:
        return False, "Username is required"
    if not password:
        return False, "Password is required"

    try:
        avg_wpm = int(avg_wpm)
        if not (10 <= avg_wpm <= 180):
            return False, "Average WPM must be between 10 and 180"
    except:
        return False, "Invalid Average WPM value"

    try:
        min_accuracy = int(min_accuracy)
        if not (85 <= min_accuracy <= 97):
            return False, "Minimum accuracy must be between 85 and 97"
    except:
        return False, "Invalid Minimum Accuracy value"

    try:
        how_many_races = int(how_many_races)
        if how_many_races <= 0:
            return False, "How Many Races must be a positive integer"
    except:
        return False, "Invalid How Many Races value"

    if not subscription_key:
        return False, "Subscription key is required"

    return True, None

# ==================== Flask Routes ====================

task_manager = TaskManager()
subscription_manager = SubscriptionManager()

@app.route("/")
def home():
    task_manager.purge_old_tasks()
    stats = task_manager.total_stats()
    return render_template("index.html", stats=stats)

@app.route("/tasks")
def tasks_page():
    return render_template("tasks.html")

@app.route("/modal_form")
def modal_form_page():
    return render_template("modal_form.html")

@app.route("/api/tasks", methods=["GET"])
def api_get_tasks():
    tasks = task_manager.get_all_tasks()
    return jsonify(tasks)

@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    stats = task_manager.total_stats()
    return jsonify(stats)

@app.route("/api/task/<task_id>/logs", methods=["GET"])
def api_task_logs(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.get("logs", []))

@app.route("/submit", methods=["POST"])
def submit_task():
    form = request.form
    is_valid, msg = validate_task_form(form)
    if not is_valid:
        return abort(400, msg)

    subscription_key = form.get("subscription_key", "").strip()
    if not subscription_manager.is_valid_key(subscription_key):
        return abort(403, "Invalid subscription key")

    if not subscription_manager.can_use_key(subscription_key, task_manager):
        return abort(403, f"Subscription key usage limit reached (max {MAX_TASKS_PER_KEY} active tasks)")

    # Create the new task dictionary
    new_task = {
        "id": generate_task_id(),
        "username": form.get("username").strip(),
        "password": form.get("password").strip(),
        "avg_wpm": int(form.get("avg_wpm")),
        "min_accuracy": int(form.get("min_accuracy")),
        "how_many_races": int(form.get("how_many_races")),
        "subscription_key": subscription_key,
        "created_at": iso_now(),
        "status": TASK_STATUS_QUEUED,
        "races_botted": 0,
        "logs": [{
            "timestamp": iso_now(),
            "message": "Task created and queued"
        }]
    }

    task_manager.add_task(new_task)

    # Start threads for queued tasks (respecting concurrency)
    start_task_threads(task_manager)

    return redirect(url_for("tasks_page"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500

# ==================== Main Run ====================

if __name__ == "__main__":
    print("Starting Nitrotype Bot Manager Flask backend...")
    # Purge old tasks on startup
    task_manager.purge_old_tasks()
    # Kick off any queued task runners (if any)
    start_task_threads(task_manager)

    # Run Flask with debug for dev, bind all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
