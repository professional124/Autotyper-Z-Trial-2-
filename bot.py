import os
import threading
import time
import random
import json
import logging
from queue import Queue
from typing import Optional

# Simulated Nitrotype API wrapper
# Replace with your actual Nitrotype API client or implementation
class NitroClient:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.logged_in = False
        self.username = None
    
    def login(self, username: str, password: str) -> bool:
        # TODO: Replace with real login using Nitrotype API
        time.sleep(1)  # Simulate network delay
        # Fake success/fail login logic
        if username and password:
            self.logged_in = True
            self.username = username
            return True
        return False
    
    def join_race(self):
        # TODO: Connect to Nitrotype race server, join a race
        # Returning a dict with race text and captcha requirement for demo
        time.sleep(1)
        return {
            "text": "The quick brown fox jumps over the lazy dog",
            "captcha_required": random.choice([False, False, False, True])  # Rare captcha
        }
    
    def send_keystroke(self, char: str):
        # TODO: Send single character keystroke to Nitrotype race
        time.sleep(0.02)  # Simulate typing speed
    
    def submit_race(self, typed_text: str) -> bool:
        # TODO: Submit the typed text and return success or failure
        time.sleep(0.5)
        return True

# Helper utilities
def encrypt(password: str) -> str:
    # Placeholder: Implement your own encryption
    return password[::-1]

def decrypt(enc_password: str) -> str:
    # Placeholder: Implement your own decryption
    return enc_password[::-1]

def is_valid_key(key: str) -> bool:
    # Placeholder: Validate subscription key
    # You can integrate with your licensing backend here
    return key == "VALID-SUBSCRIPTION-KEY"

def get_proxy() -> Optional[str]:
    # Placeholder: Return a proxy string if you have proxies configured
    # e.g., "http://user:pass@proxyserver:port"
    return None

def solve_captcha(username: str, captcha_key: str) -> bool:
    # Simulate captcha solving via external service using captcha_key
    # Replace with your actual captcha solver API integration here
    logging.info(f"[{username}] Solving captcha with key: {captcha_key[:5]}***")
    time.sleep(3)  # Simulate solver delay
    # Randomly succeed or fail captcha solve
    success = random.random() > 0.2
    logging.info(f"[{username}] Captcha solve {'success' if success else 'failure'}")
    return success

# Setup logging
logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("AutoTyper")

# Read CAPTCHA key from environment variable
CAPTCHA_KEY = os.getenv("CAPTCHA_KEY")
if not CAPTCHA_KEY:
    raise Exception("CAPTCHA_KEY environment variable not set! Set it before running the bot.")

MAX_CONCURRENT_BOTS = 3
TASKS_FILE = "tasks.json"

# Thread-safe queue and dict for bot management
active_bots = {}
bot_queue = Queue()
lock = threading.Lock()

class Bot(threading.Thread):
    def __init__(self, username: str, password_enc: str, avg_wpm: int, min_acc: int, num_races: int, key: str, proxy: Optional[str] = None):
        super().__init__()
        self.username = username
        self.password_enc = password_enc
        self.avg_wpm = avg_wpm
        self.min_acc = min_acc
        self.num_races = num_races
        self.key = key
        self.proxy = proxy
        self.races_completed = 0
        self.status = "Initialized"
        self.client = None
        self._stop_event = threading.Event()

    def decrypt_password(self) -> str:
        return decrypt(self.password_enc)

    def run(self):
        logger.info(f"[{self.username}] Bot thread started.")

        if not is_valid_key(self.key):
            self.status = "Invalid subscription key"
            logger.error(f"[{self.username}] Invalid subscription key. Exiting.")
            return

        try:
            self.status = "Logging in"
            self.client = NitroClient(proxy=self.proxy)
            password = self.decrypt_password()
            if not self.client.login(self.username, password):
                self.status = "Login failed"
                logger.error(f"[{self.username}] Login failed with provided credentials.")
                return

            self.status = "Racing"
            while not self._stop_event.is_set() and self.races_completed < self.num_races:
                race_info = self.client.join_race()
                if not race_info:
                    self.status = "Failed to join race"
                    logger.error(f"[{self.username}] Failed to join a race.")
                    break

                if race_info.get("captcha_required", False):
                    self.status = "Captcha required"
                    logger.info(f"[{self.username}] Captcha challenge encountered.")
                    if not solve_captcha(self.username, CAPTCHA_KEY):
                        self.status = "Captcha solve failed"
                        logger.error(f"[{self.username}] Failed to solve captcha. Stopping bot.")
                        break
                    self.status = "Captcha solved, continuing"

                self.status = "Typing"
                if not self.simulate_typing(race_info["text"]):
                    self.status = "Race typing failed"
                    logger.error(f"[{self.username}] Typing failed during race.")
                    break

                self.races_completed += 1
                logger.info(f"[{self.username}] Completed race {self.races_completed}/{self.num_races}")
                time.sleep(random.uniform(2, 4))  # Cooldown between races

            self.status = "Completed" if self.races_completed == self.num_races else "Stopped"
            logger.info(f"[{self.username}] Bot finished with status: {self.status}")

        except Exception as e:
            self.status = f"Error: {str(e)}"
            logger.exception(f"[{self.username}] Exception occurred: {str(e)}")

        finally:
            self.cleanup()

    def simulate_typing(self, text: str) -> bool:
        """Simulates human-like typing with speed and accuracy control."""
        base_delay = 60 / (self.avg_wpm * 5)  # average seconds per char (5 chars = 1 word)
        typed_text = ""

        for char in text:
            if self._stop_event.is_set():
                logger.info(f"[{self.username}] Stop signal received during typing.")
                return False

            # Simulate accuracy (sometimes mistype)
            if random.random() > (self.min_acc / 100):
                mistake = random.choice("abcdefghijklmnopqrstuvwxyz ")
                self.client.send_keystroke(mistake)
                typed_text += mistake
            else:
                self.client.send_keystroke(char)
                typed_text += char

            # Randomize typing delay a bit for realism
            time.sleep(base_delay * random.uniform(0.8, 1.3))

        # Submit race and return success status
        return self.client.submit_race(typed_text)

    def stop(self):
        self._stop_event.set()
        self.status = "Stopped"
        logger.info(f"[{self.username}] Bot stop requested.")

    def cleanup(self):
        # Called when bot finishes or stops to clean up and persist state
        with lock:
            if self.username in active_bots:
                del active_bots[self.username]
            self.persist_tasks()
            self.start_next_queued_bot()

    @staticmethod
    def persist_tasks():
        with lock:
            tasks_data = {u: bot.to_dict() for u, bot in active_bots.items()}
            with open(TASKS_FILE, "w") as f:
                json.dump(tasks_data, f, indent=2)
            logger.info("Saved active bot tasks to file.")

    @staticmethod
    def start_next_queued_bot():
        with lock:
            if not bot_queue.empty() and len(active_bots) < MAX_CONCURRENT_BOTS:
                next_bot = bot_queue.get()
                active_bots[next_bot.username] = next_bot
                next_bot.start()
                logger.info(f"Started queued bot: {next_bot.username}")

    def to_dict(self):
        return {
            "username": self.username,
            "password_enc": self.password_enc,
            "avg_wpm": self.avg_wpm,
            "min_acc": self.min_acc,
            "num_races": self.num_races,
            "key": self.key,
            "proxy": self.proxy,
            "races_completed": self.races_completed,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data):
        bot = cls(
            username=data["username"],
            password_enc=data["password_enc"],
            avg_wpm=data["avg_wpm"],
            min_acc=data["min_acc"],
            num_races=data["num_races"],
            key=data["key"],
            proxy=data.get("proxy")
        )
        bot.races_completed = data.get("races_completed", 0)
        bot.status = data.get("status", "Initialized")
        return bot

def add_task(data: dict) -> str:
    username = data["username"]
    with lock:
        if username in active_bots:
            return "Bot is already running for this username."

        if len(active_bots) >= MAX_CONCURRENT_BOTS:
            # Queue the task
            proxy = get_proxy()
            bot = Bot(
                username=username,
                password_enc=encrypt(data["password"]),
                avg_wpm=int(data["avg_wpm"]),
                min_acc=int(data["min_acc"]),
                num_races=int(data["num_races"]),
                key=data["key"],
                proxy=proxy
            )
            bot_queue.put(bot)
            logger.info(f"Queued new bot for user: {username}")
            return "Max bots running. Your task has been queued."

        # Start the bot immediately
        proxy = get_proxy()
        bot = Bot(
            username=username,
            password_enc=encrypt(data["password"]),
            avg_wpm=int(data["avg_wpm"]),
            min_acc=int(data["min_acc"]),
            num_races=int(data["num_races"]),
            key=data["key"],
            proxy=proxy
        )
        active_bots[username] = bot
        bot.start()
        logger.info(f"Started bot for user: {username}")
        return "Bot started successfully."

def stop_task(username: str) -> str:
    with lock:
        if username not in active_bots:
            return "No active bot found for this username."
        bot = active_bots[username]
        bot.stop()
        del active_bots[username]
        Bot.start_next_queued_bot()
        logger.info(f"Stopped bot for user: {username}")
        return "Bot stopped."

def get_status() -> dict:
    with lock:
        return {
            username: {
                "status": bot.status,
                "races_completed": bot.races_completed,
                "num_races": bot.num_races,
                "proxy": bot.proxy
            }
            for username, bot in active_bots.items()
        }

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return
    with open(TASKS_FILE, "r") as f:
        tasks = json.load(f)
    for username, data in tasks.items():
        bot = Bot.from_dict(data)
        with lock:
            active_bots[username] = bot
        bot.start()
    logger.info("Loaded saved tasks and restarted bots.")

if __name__ == "__main__":
    logger.info("Starting AutoTyper bot manager...")
    load_tasks()
    # Main thread can handle CLI or API server integration
    # For demo, just keep the script running
    try:
        while True:
            time.sleep(5)
            with lock:
                logger.info(f"Active bots: {list(active_bots.keys())}, Queue size: {bot_queue.qsize()}")
    except KeyboardInterrupt:
        logger.info("Shutting down all bots...")
        with lock:
            for bot in list(active_bots.values()):
                bot.stop()
