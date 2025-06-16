import threading
import logging
from pathlib import Path
import os

class SubscriptionKeyManager:
    def __init__(self, key_file_path=None, max_concurrent_accounts=3):
        self._lock = threading.RLock()
        self._key_file_path = key_file_path or os.getenv("SUBSCRIPTION_KEYS_FILE", "keys.txt")
        self._keys = set()
        self._last_loaded = 0
        self._max_concurrent_accounts = max_concurrent_accounts

        # Track active accounts per key: { key_string: count_of_active_accounts }
        self._active_accounts = {}

        self._load_keys()

    def _load_keys(self):
        with self._lock:
            keys_path = Path(self._key_file_path)
            if not keys_path.exists() or not keys_path.is_file():
                logging.error(f"[SubscriptionKeyManager] Subscription keys file not found: {self._key_file_path}")
                self._keys = set()
                self._last_loaded = 0
                return

            try:
                with keys_path.open("r") as f:
                    keys = set()
                    for line in f:
                        key = line.strip()
                        if key and key.isalnum() and len(key) >= 6:
                            keys.add(key)
                    self._keys = keys
                    self._last_loaded = keys_path.stat().st_mtime
                    # Reset active counts for new keys to zero if missing
                    for key in keys:
                        self._active_accounts.setdefault(key, 0)
                    # Remove active accounts tracking for keys no longer valid
                    for tracked_key in list(self._active_accounts.keys()):
                        if tracked_key not in keys:
                            del self._active_accounts[tracked_key]
                    logging.info(f"[SubscriptionKeyManager] Loaded {len(keys)} keys.")
            except Exception as e:
                logging.error(f"[SubscriptionKeyManager] Error loading keys: {e}")
                self._keys = set()
                self._last_loaded = 0

    def reload_keys_if_changed(self):
        with self._lock:
            keys_path = Path(self._key_file_path)
            if keys_path.exists() and keys_path.is_file():
                try:
                    mtime = keys_path.stat().st_mtime
                    if mtime > self._last_loaded:
                        logging.info("[SubscriptionKeyManager] Keys file changed, reloading.")
                        self._load_keys()
                except Exception as e:
                    logging.error(f"[SubscriptionKeyManager] Error checking keys file mtime: {e}")

    def validate_key(self, key: str) -> bool:
        if not key:
            return False
        self.reload_keys_if_changed()
        with self._lock:
            return key in self._keys

    def can_start_new_account(self, key: str) -> bool:
        """
        Returns True if this subscription key can start a new account (i.e., concurrency limit not hit)
        """
        with self._lock:
            active_count = self._active_accounts.get(key, 0)
            if active_count < self._max_concurrent_accounts:
                return True
            else:
                logging.warning(f"[SubscriptionKeyManager] Key {key} reached max concurrent accounts: {active_count}")
                return False

    def increment_active_accounts(self, key: str) -> bool:
        """
        Increment active account count for the key if under limit.
        Returns True if increment succeeded, False if limit reached.
        """
        with self._lock:
            if key not in self._keys:
                logging.warning(f"[SubscriptionKeyManager] Trying to increment for invalid key: {key}")
                return False

            if self.can_start_new_account(key):
                self._active_accounts[key] = self._active_accounts.get(key, 0) + 1
                logging.info(f"[SubscriptionKeyManager] Incremented active accounts for key {key}: {self._active_accounts[key]}")
                return True
            else:
                return False

    def decrement_active_accounts(self, key: str):
        """
        Decrement active account count for the key.
        Make sure count never goes below zero.
        """
        with self._lock:
            if key in self._active_accounts and self._active_accounts[key] > 0:
                self._active_accounts[key] -= 1
                logging.info(f"[SubscriptionKeyManager] Decremented active accounts for key {key}: {self._active_accounts[key]}")
            else:
                logging.warning(f"[SubscriptionKeyManager] Tried to decrement active accounts for key {key} but count was zero or key unknown.")

    # ... add_key and remove_key methods as before ...

# Instantiate global manager with limit 3
subscription_key_manager = SubscriptionKeyManager(max_concurrent_accounts=3)

# Example wrapper for your bot_manager to check and update account usage:

def start_bot_task(key: str) -> bool:
    """
    Call before starting a bot with this subscription key.
    Returns True if bot can start, False if key limit exceeded or invalid.
    """
    if not subscription_key_manager.validate_key(key):
        logging.error(f"Invalid subscription key: {key}")
        return False

    if not subscription_key_manager.increment_active_accounts(key):
        logging.error(f"Subscription key {key} has reached max concurrent accounts.")
        return False

    # All good, bot can start
    return True

def end_bot_task(key: str):
    """
    Call when a bot finishes/stops to release the slot for this subscription key.
    """
    subscription_key_manager.decrement_active_accounts(key)
