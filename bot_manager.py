import threading
import uuid
from modules.bot import NitroBot

class BotManager:
    def __init__(self):
        self.bots = {}

    def start_bot(self, username, password, avg_wpm, min_accuracy, race_count):
        bot_id = str(uuid.uuid4())
        bot = NitroBot(username, password, avg_wpm, min_accuracy, race_count)
        thread = threading.Thread(target=bot.run)
        thread.start()
        self.bots[bot_id] = {
            'bot': bot,
            'thread': thread,
            'username': username,
            'status': 'running',
            'races_done': 0
        }

    def get_bots_status(self):
        status = {}
        for bot_id, info in self.bots.items():
            bot = info['bot']
            status[bot_id] = {
                'username': info['username'],
                'status': 'running' if bot.is_running else 'stopped',
                'races_done': bot.races_completed
            }
        return status

    def stop_bot(self, bot_id):
        if bot_id in self.bots:
            bot = self.bots[bot_id]['bot']
            bot.stop()
            self.bots[bot_id]['status'] = 'stopped'
