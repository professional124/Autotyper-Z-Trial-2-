import os
import time
import threading
import queue
import random
import logging
import requests
from typing import Optional, Dict

# ---- SETUP LOGGING ----
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum verbosity
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ---- CONSTANTS AND CONFIG ----
MAX_CONCURRENT_TASKS = 3
PROXIES_FILE = "proxies.txt"
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY")  # Put your CAPTCHA solving service key here
SUBSCRIPTION_KEYS = {"SUBSCRIPTION_KEY_123", "SUBSCRIPTION_KEY_456"}  # Demo keys, replace as needed
RETRY_LIMIT = 5
MIN_WPM = 10
MAX_WPM = 180
MIN_ACC = 85
MAX_ACC = 97


# ---- NITROTYPE.JS API SIMULATION ----
class NitrotypeAPI:
    """
    Simulates Nitrotype.js API integration.
    Replace placeholders with real Nitrotype.js calls.
    """
    def __init__(self, username: str, password: str, proxy: Optional[str] = None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.logged_in = False
        self.races_completed = 0

    def login(self) -> bool:
        logging.debug(f"[{self.username}] Attempting to login...")
        try:
            # Placeholder: Replace with actual Nitrotype.js login call
            time.sleep(random.uniform(1.0, 1.5))  # Simulate network latency
            if not self.username or not self.password:
                raise ValueError("Username or password missing")
            # Simulate successful login
            self.logged_in = True
            logging.info(f"[{self.username}] Login successful.")
            return True
        except Exception as e:
            logging.error(f"[{self.username}] Login failed: {e}")
            return False

    def solve_captcha(self) -> bool:
        if not CAPTCHA_API_KEY:
            logging.warning(f"[{self.username}] CAPTCHA API key not set, skipping CAPTCHA solving.")
            return True  # Assume no captcha required
        try:
            logging.debug(f"[{self.username}] Solving CAPTCHA with API key...")
            # Placeholder for actual CAPTCHA solving API call
            time.sleep(2)  # Simulate delay
            # Pretend captcha was solved successfully
            logging.info(f"[{self.username}] CAPTCHA solved successfully.")
            return True
        except Exception as e:
            logging.error(f"[{self.username}] CAPTCHA solving failed: {e}")
            return False

    def start_race(self, avg_wpm: int, min_acc: int) -> bool:
        if not self.logged_in:
            logging.warning(f"[{self.username}] Cannot start race, not logged in.")
            return False
        logging.debug(f"[{self.username}] Starting a race at target WPM {avg_wpm} and min accuracy {min_acc}%.")
        try:
            # Placeholder: Simulate the race with delays and accuracy checks
            race_duration = random.uniform(5, 10)  # seconds per race
            time.sleep(race_duration)
            achieved_wpm = random.uniform(max(MIN_WPM, avg_wpm - 10), min(MAX_WPM, avg_wpm + 10))
            achieved_acc = random.uniform(min_acc, 100)
            if achieved_acc < min_acc:
                logging.warning(f"[{self.username}] Race failed due to low accuracy: {achieved_acc:.2f}% < {min_acc}%")
                return False
            self.races_completed += 1
            logging.info(f"[{self.username}] Race completed: WPM={achieved_wpm:.2f}, Accuracy={achieved_acc:.2f}%. Total races: {self.races_completed}")
            return True
        except Exception as e:
            logging.error(f"[{self.username}] Error during race: {e}")
            return False

    def logout(self):
        if self.logged_in:
            logging.info(f"[{self.username}] Logging out.")
            self.logged_in = False
        else:
            logging.debug(f"[{self.username}] Logout called but user was not logged in.")


# ---- TASK CLASS ----
class BotTask:
    def __init__(self, username: str, password: str, avg_wpm: int, min_acc: int, num_races: int, subscription_key: str):
        self.username = username
        self.password = password
        self.avg_wpm = max(MIN_WPM, min(MAX_WPM, avg_wpm))
        self.min_acc = max(MIN_ACC, min(MAX_ACC, min_acc))
        self.num_races = num_races
        self.subscription_key = subscription_key
        self.races_done = 0
        self.active = False
        self.failed_attempts = 0
        self.proxy = None  # Will assign from proxy pool later


# ---- BOT MANAGER ----
class AutoTyperBotManager:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.active_tasks: Dict[str, BotTask] = {}
        self.lock = threading.Lock()
        self.proxies = self.load_proxies(PROXIES_FILE)
        self.running = True

        self.total_races_botted = 0
        self.total_accounts_botted = 0
        self.start_time = time.time()

        logging.info("AutoTyperBotManager initialized.")

    def load_proxies(self, filename: str) -> list:
        proxies = []
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        proxies.append(line)
            logging.info(f"Loaded {len(proxies)} proxies from {filename}.")
        else:
            logging.warning(f"Proxy file {filename} not found. Proceeding without proxies.")
        return proxies

    def validate_subscription(self, key: str) -> bool:
        valid = key in SUBSCRIPTION_KEYS
        if not valid:
            logging.warning(f"Invalid subscription key: {key}")
        return valid

    def assign_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        # Rotate proxies by popping first and appending to the end (round-robin)
        proxy = self.proxies.pop(0)
        self.proxies.append(proxy)
        logging.debug(f"Assigned proxy {proxy}")
        return proxy

    def add_task(self, task: BotTask) -> bool:
        if not self.validate_subscription(task.subscription_key):
            logging.error(f"[{task.username}] Subscription key invalid.")
            return False
        with self.lock:
            if task.username in self.active_tasks or any(t.username == task.username for t in list(self.task_queue.queue)):
                logging.warning(f"[{task.username}] Task already running or queued.")
                return False

            if len(self.active_tasks) < MAX_CONCURRENT_TASKS:
                logging.info(f"[{task.username}] Starting task immediately.")
                task.proxy = self.assign_proxy()
                self.active_tasks[task.username] = task
                threading.Thread(target=self._run_task, args=(task,), daemon=True).start()
            else:
                logging.info(f"[{task.username}] Task queued (max concurrency reached).")
                self.task_queue.put(task)
        return True

    def _run_task(self, task: BotTask):
        task.active = True
        api = NitrotypeAPI(task.username, task.password, proxy=task.proxy)

        if not api.login():
            logging.error(f"[{task.username}] Login failed, task aborted.")
            self._finish_task(task)
            return

        for i in range(task.num_races):
            if not task.active:
                logging.info(f"[{task.username}] Task stopped externally.")
                break

            # CAPTCHA solving
            if not api.solve_captcha():
                logging.error(f"[{task.username}] CAPTCHA solving failed, retrying...")
                task.failed_attempts += 1
                if task.failed_attempts > RETRY_LIMIT:
                    logging.error(f"[{task.username}] Retry limit exceeded, aborting task.")
                    break
                time.sleep(5)
                continue

            success = api.start_race(task.avg_wpm, task.min_acc)
            if not success:
                task.failed_attempts += 1
                logging.warning(f"[{task.username}] Race attempt failed (attempt {task.failed_attempts}). Retrying...")
                if task.failed_attempts > RETRY_LIMIT:
                    logging.error(f"[{task.username}] Retry limit exceeded during races, aborting.")
                    break
                time.sleep(3)
                continue

            task.races_done += 1
            with self.lock:
                self.total_races_botted += 1

            logging.info(f"[{task.username}] Completed race {task.races_done}/{task.num_races}.")

        api.logout()
        self._finish_task(task)

    def _finish_task(self, task: BotTask):
        logging.info(f"[{task.username}] Task finished. Total races completed: {task.races_done}.")
        with self.lock:
            self.active_tasks.pop(task.username, None)
            self.total_accounts_botted += 1
            if not self.task_queue.empty():
                next_task: BotTask = self.task_queue.get()
                logging.info(f"[{next_task.username}] Dequeued task, starting now.")
                next_task.proxy = self.assign_proxy()
                self.active_tasks[next_task.username] = next_task
                threading.Thread(target=self._run_task, args=(next_task,), daemon=True).start()

    def stop_task(self, username: str):
        with self.lock:
            task = self.active_tasks.get(username)
            if task:
                task.active = False
                logging.info(f"[{username}] Stop requested for active task.")
            else:
                # Also remove from queue if waiting
                removed = False
                temp_queue = queue.Queue()
                while not self.task_queue.empty():
                    t = self.task_queue.get()
                    if t.username == username:
                        logging.info(f"[{username}] Removed task from queue.")
                        removed = True
                        continue
                    temp_queue.put(t)
                self.task_queue = temp_queue
                if not removed:
                    logging.warning(f"[{username}] No active or queued task found to stop.")

    def get_stats(self) -> Dict[str, int]:
        uptime = int(time.time() - self.start_time)
        return {
            "total_races_botted": self.total_races_botted,
            "total_accounts_botted": self.total_accounts_botted,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "uptime_seconds": uptime
        }

    def get_active_tasks(self) -> Dict[str, Dict]:
        with self.lock:
            return {
                username: {
                    "races_done": task.races_done,
                    "num_races": task.num_races,
                    "avg_wpm": task.avg_wpm,
                    "min_acc": task.min_acc,
                    "proxy": task.proxy,
                }
                for username, task in self.active_tasks.items()
            }

    def shutdown(self):
        logging.info("Shutting down AutoTyperBotManager...")
        self.running = False
        with self.lock:
            for task in self.active_tasks.values():
                task.active = False


# ---- MAIN ENTRY POINT ----
if __name__ == "__main__":
    manager = AutoTyperBotManager()

    # Sample tasks for testing
    sample_tasks = [
        BotTask("user1", "pass1", 90, 90, 5, "SUBSCRIPTION_KEY_123"),
        BotTask("user2", "pass2", 85, 85, 3, "SUBSCRIPTION_KEY_456"),
        BotTask("user3", "pass3", 100, 95, 10, "SUBSCRIPTION_KEY_123"),
        BotTask("user4", "pass4", 75, 90, 7, "INVALID_KEY")  # Should be rejected
    ]

    for task in sample_tasks:
        added = manager.add_task(task)
        logging.info(f"Task for {task.username} added: {added}")

    try:
        while manager.running:
            stats = manager.get_stats()
            logging.info(f"Bot stats: {stats}")
            active = manager.get_active_tasks()
            logging.debug(f"Active tasks: {active}")
            time.sleep(10)  # Main thread loop delay
    except KeyboardInterrupt:
        manager.shutdown()
        logging.info("Bot manager terminated by user.")
