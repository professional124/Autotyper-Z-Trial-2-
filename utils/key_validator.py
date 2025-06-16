import threading
import logging
from pathlib import Path
import os
import time

class SubscriptionKeyManager:
    def __init__(self, key_file_path="keys.txt", max_concurrent_accounts=3):
        self.key_file_path = key_file_path
        self.max_concurrent_accounts = max_concurrent_accounts
        self.keys = set()
        self.active_accounts = {}  # key -> count of active accounts
        self.last_modified_time = 0
        self.lock = threading.RLock()

        self.load_keys()

    def load_keys(self):
        """Load keys from the file if it has changed."""
        with self.lock:
            path = Path(self.key_file_path)
            if not path.exists():
                logging.warning(f"[KeyManager] {self.key_file_path} not found.")
                return

            modified_time = path.stat().st_mtime
            if modified_time != self.last_modified_time:
                logging.info("[KeyManager] Detected change in keys file. Reloading...")
                try:
                    with open(path, "r") as f:
                        new_keys = set()
                        for line in f:
                            key = line.strip()
                            if key:
                                new_keys.add(key)

                        self.keys = new_keys
                        # Reset active_accounts for invalid keys
                        self.active_accounts = {
                            k: self.active_accounts.get(k, 0) for k in new_keys
                        }
                        self.last_modified_time = modified_time
                        logging.info(f"[KeyManager] Loaded {len(new_keys)} keys.")
                except Exception as e:
                    logging.error(f"[KeyManager] Error reading keys: {e}")

    def is_valid_key(self, key):
        """Validate key and reload if needed."""
        self.load_keys()
        with self.lock:
            return key in self.keys

    def can_start_account(self, key):
        """Return True if this key can start a new task (limit: 3)."""
        with self.lock:
            if key not in self.keys:
                return False
            return self.active_accounts.get(key, 0) < self.max_concurrent_accounts

    def increment_account(self, key):
        """Register a new task if within limits."""
        with self.lock:
            if self.can_start_account(key):
                self.active_accounts[key] = self.active_accounts.get(key, 0) + 1
                logging.info(f"[KeyManager] Started task for key {key} — Active: {self.active_accounts[key]}")
                return True
            else:
                logging.warning(f"[KeyManager] Key {key} reached max concurrent accounts.")
                return False

    def decrement_account(self, key):
        """Remove a running task from a key (on completion)."""
        with self.lock:
            if key in self.active_accounts and self.active_accounts[key] > 0:
                self.active_accounts[key] -= 1
                logging.info(f"[KeyManager] Task finished for key {key} — Remaining: {self.active_accounts[key]}")
            else:
                logging.warning(f"[KeyManager] Tried to decrement for {key}, but none running.")

    def get_active_count(self, key):
        """Return how many accounts are currently active for a given key."""
        with self.lock:
            return self.active_accounts.get(key, 0)

    def get_status_report(self):
        """Return a dict showing active accounts per key (for analytics/logging)."""
        with self.lock:
            return dict(self.active_accounts)


# Optional: Create a global manager instance
subscription_manager = SubscriptionKeyManager()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_key = "ABC123"

    if subscription_manager.is_valid_key(test_key):
        if subscription_manager.increment_account(test_key):
            logging.info("Bot task started successfully!")
            # Simulate task
            time.sleep(3)
            subscription_manager.decrement_account(test_key)
        else:
            logging.warning("Reached limit. Cannot start new bot.")
    else:
        logging.error("Invalid subscription key.")
