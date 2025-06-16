import time
import random
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def read_proxies():
    try:
        with open("proxies.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def read_capsolver_key():
    try:
        with open("capsolver.txt", "r") as f:
            return f.read().strip()
    except:
        return ""

def solve_captcha():
    # Placeholder for captcha solving (use capsolver key)
    key = read_capsolver_key()
    if key:
        print("[+] Captcha solving would go here using key:", key)
    else:
        print("[-] No capsolver key found")
    time.sleep(1)

def simulate_typing(driver, avg_wpm, min_accuracy):
    try:
        time.sleep(3)
        words = driver.find_elements(By.CLASS_NAME, "dash-word")
        text = " ".join([w.text for w in words])
        delay = 60.0 / (avg_wpm * 5)
        actions = ActionChains(driver)

        for char in text:
            if random.randint(1, 100) > min_accuracy:
                char = random.choice("abcdefghijklmnopqrstuvwxyz")
            actions.send_keys(char)
            actions.perform()
            time.sleep(random.uniform(delay * 0.8, delay * 1.2))

    except Exception as e:
        print("[-] Typing failed:", e)

def run_bot(username, password, avg_wpm, min_accuracy):
    print(f"[+] Starting bot: {username} | {avg_wpm} WPM | {min_accuracy}% Accuracy")

    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--profile-directory=Default")

    # Use proxy if available
    proxies = read_proxies()
    if proxies:
        proxy = random.choice(proxies)
        options.add_argument(f"--proxy-server={proxy}")
        print(f"[+] Using proxy: {proxy}")

    driver = uc.Chrome(options=options)
    driver.get("https://www.nitrotype.com/login")
    time.sleep(3)

    try:
        # Login
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.TAG_NAME, "form").submit()
        time.sleep(5)

        # Check if logged in successfully
        if "login" in driver.current_url:
            print("[-] Login failed. Retrying after captcha check...")
            solve_captcha()
            driver.get("https://www.nitrotype.com/login")
            time.sleep(3)

        # Navigate to race
        driver.get("https://www.nitrotype.com/race")
        time.sleep(10)

        # Simulate typing
        simulate_typing(driver, avg_wpm, min_accuracy)

        # Wait for race to end
        time.sleep(5)

    except Exception as e:
        print("[-] Bot Error:", e)

    finally:
        print(f"[✓] Bot finished for {username}")
        driver.quit()
