import threading
import time
from bot import run_bot

class BotThread(threading.Thread):
    def __init__(self, username, password, avg_wpm, min_accuracy, races):
        super().__init__()
        self.username = username
        self.password = password
        self.avg_wpm = avg_wpm
        self.min_accuracy = min_accuracy
        self.races_to_run = races
        self.races_done = 0
        self._stop_event = threading.Event()

    def run(self):
        while self.races_done < self.races_to_run and not self._stop_event.is_set():
            print(f"[BotThread] Starting race {self.races_done + 1} for {self.username}")
            try:
                run_bot(self.username, self.password, self.avg_wpm, self.min_accuracy)
                self.races_done += 1
                print(f"[BotThread] Completed race {self.races_done} for {self.username}")
            except Exception as e:
                print(f"[BotThread] Error in bot {self.username}: {e}")
                break
            time.sleep(2)  # brief pause between races

    def stop(self):
        self._stop_event.set()

class BotManager:
    def __init__(self):
        self.bots = {}  # key=username, value=BotThread
        self.lock = threading.Lock()

    def start_bot(self, username, password, avg_wpm, min_accuracy, races):
        with self.lock:
            if username in self.bots and self.bots[username].is_alive():
                print(f"[BotManager] Bot for {username} is already running!")
                return False
            bot_thread = BotThread(username, password, avg_wpm, min_accuracy, races)
            self.bots[username] = bot_thread
            bot_thread.start()
            print(f"[BotManager] Bot started for {username}")
            return True

    def stop_bot(self, username):
        with self.lock:
            bot = self.bots.get(username)
            if bot and bot.is_alive():
                bot.stop()
                bot.join()
                print(f"[BotManager] Bot stopped for {username}")
                return True
            return False

    def get_active_bots(self):
        with self.lock:
            active = []
            for username, bot in self.bots.items():
                if bot.is_alive():
                    active.append({
                        "username": username,
                        "races_done": bot.races_done,
                        "races_to_run": bot.races_to_run
                    })
            return active
