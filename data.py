import os
import time
import ast
from datetime import datetime
from filelock import FileLock
import shutil
import threading

# Helper to ensure a directory exists

def ensure_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# --- Paths and Directories
DATA_DIR = "db_files"
BACKUP_DIR = "backups"
ensure_dir(DATA_DIR)
ensure_dir(BACKUP_DIR)
BALANCE_FILE = os.path.join(DATA_DIR, "balances.txt")
NOTIFS_DIR = os.path.join(DATA_DIR, "notifications")
PREFS_DIR = os.path.join(DATA_DIR, "preferences")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.txt")
PROCESSED_COMMENTS_FILE = os.path.join(DATA_DIR, "processed_comments.txt")
SUBSCRIPTIONS_FILE = os.path.join(DATA_DIR, "subscriptions.txt")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.txt")

for subdir in [NOTIFS_DIR, PREFS_DIR]:
    ensure_dir(subdir)

MAX_NOTIFICATIONS_PER_USER = 100
# --- Sanitize name, block all problematic characters

def fix_name(name: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    n = name.replace(" ", "").replace("@", "").strip().lower()
    return "".join(c for c in n if c in allowed)

# --- Balances Management

def _balances_load():
    balances = {}
    lockfile = BALANCE_FILE + ".lock"
    with FileLock(lockfile):
        if not os.path.exists(BALANCE_FILE):
            return balances
        with open(BALANCE_FILE, "r") as f:
            for line in f:
                if ":" in line:
                    user, bal = line.strip().split(":", 1)
                    try:
                        balances[user] = float(bal)
                    except ValueError:
                        continue
    return balances


def _balances_save(balances):
    lockfile = BALANCE_FILE + ".lock"
    tmp_file = BALANCE_FILE + ".tmp"
    with FileLock(lockfile):
        with open(tmp_file, "w") as f:
            for user, bal in balances.items():
                f.write(f"{user}:{round(bal, 4):.4f}\n")
        os.replace(tmp_file, BALANCE_FILE)


def set_balance(user, amount):
    user = fix_name(user)
    try:
        amount = float(amount)
    except ValueError:
        amount = 0.0
    balances = _balances_load()
    balances[user] = amount
    _balances_save(balances)


def get_balance(user):
    user = fix_name(user)
    balances = _balances_load()
    if user in balances:
        return round(balances[user], 1)
    set_balance(user, 100.0)
    return 100.0

# --- Notifications Management

def _notifs_file(user):
    return os.path.join(NOTIFS_DIR, f"{user}.txt")


def get_notifications(user):
    user = fix_name(user)
    notif_file = _notifs_file(user)
    lockfile = notif_file + ".lock"
    with FileLock(lockfile):
        if not os.path.exists(notif_file):
            return []
        with open(notif_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]



def add_notification(user, message):
    user = fix_name(user)
    notif_file = _notifs_file(user)
    lockfile = notif_file + ".lock"
    with FileLock(lockfile):
        entries = []
        if os.path.exists(notif_file):
            with open(notif_file, "r") as f:
                entries = [line.strip() for line in f.readlines() if line.strip()]
        entries.append(message)
        if len(entries) > MAX_NOTIFICATIONS_PER_USER:
            entries = entries[-MAX_NOTIFICATIONS_PER_USER:]
        with open(notif_file, "w") as f:
            for line in entries:
                f.write(line + "\n")

def clear_notifications(user):
    user = fix_name(user)
    notif_file = _notifs_file(user)
    lockfile = notif_file + ".lock"
    with FileLock(lockfile):
        open(notif_file, "w").close()

# --- Preferences Management

def _prefs_file(user):
    return os.path.join(PREFS_DIR, f"{user}.txt")


def get_preferences(user):
    user = fix_name(user)
    prefs_file = _prefs_file(user)
    lockfile = prefs_file + ".lock"
    default_prefs = {"theme": "blue", "mute": "False"}
    with FileLock(lockfile):
        if not os.path.exists(prefs_file):
            set_preferences(user, default_prefs["theme"], default_prefs["mute"])
            return default_prefs
        with open(prefs_file, "r") as f:
            try:
                d = ast.literal_eval(f.read().strip())
                if isinstance(d, dict):
                    for k in default_prefs:
                        if k not in d:
                            d[k] = default_prefs[k]
                    return d
            except (ValueError, SyntaxError):
                return default_prefs
    return default_prefs


def set_preferences(user, theme, mute):
    user = fix_name(user)
    prefs_file = _prefs_file(user)
    lockfile = prefs_file + ".lock"
    d = {"theme": theme, "mute": mute}
    with FileLock(lockfile):
        with open(prefs_file, "w") as f:
            f.write(str(d))

# --- Transactions Management

def save_transaction(sender, receiver, amount):
    tx = {
        "timestamp": int(time.time()),
        "from": sender,
        "to": receiver,
        "amount": round(float(amount), 1)
    }
    lockfile = TRANSACTIONS_FILE + ".lock"
    with FileLock(lockfile):
        with open(TRANSACTIONS_FILE, "a") as f:
            f.write(str(tx) + "\n")

# --- Processed Comments Management

def _processed_comments_load():
    processed_ids = set()
    lockfile = PROCESSED_COMMENTS_FILE + ".lock"
    with FileLock(lockfile):
        if not os.path.exists(PROCESSED_COMMENTS_FILE):
            return processed_ids
        with open(PROCESSED_COMMENTS_FILE, "r") as f:
            for line in f:
                processed_ids.add(line.strip())
    return processed_ids


def _processed_comments_save(processed_ids):
    lockfile = PROCESSED_COMMENTS_FILE + ".lock"
    tmp_file = PROCESSED_COMMENTS_FILE + ".tmp"
    with FileLock(lockfile):
        with open(tmp_file, "w") as f:
            for comment_id in processed_ids:
                f.write(f"{comment_id}\n")
        os.replace(tmp_file, PROCESSED_COMMENTS_FILE)


def add_processed_comment(comment_id):
    processed_ids = _processed_comments_load()
    processed_ids.add(str(comment_id))
    _processed_comments_save(processed_ids)


def is_comment_processed(comment_id):
    processed_ids = _processed_comments_load()
    return str(comment_id) in processed_ids

# --- Subscriptions Management

def _subscriptions_load():
    subscriptions = []
    lockfile = SUBSCRIPTIONS_FILE + ".lock"
    with FileLock(lockfile):
        if not os.path.exists(SUBSCRIPTIONS_FILE):
            return subscriptions
        with open(SUBSCRIPTIONS_FILE, "r") as f:
            for line in f:
                try:
                    sub = ast.literal_eval(line.strip())
                    if isinstance(sub, dict) and all(k in sub for k in ["payer", "payee", "amount", "cycle", "last_paid_timestamp", "next_payment_timestamp"]):
                        subscriptions.append(sub)
                except (ValueError, SyntaxError):
                    continue
    return subscriptions


def _subscriptions_save(subscriptions):
    lockfile = SUBSCRIPTIONS_FILE + ".lock"
    tmp_file = SUBSCRIPTIONS_FILE + ".tmp"
    with FileLock(lockfile):
        with open(tmp_file, "w") as f:
            for sub in subscriptions:
                f.write(str(sub) + "\n")
        os.replace(tmp_file, SUBSCRIPTIONS_FILE)


def add_subscription(payer, payee, amount, cycle, last_paid_timestamp, next_payment_timestamp):
    payer = fix_name(payer)
    payee = fix_name(payee)
    subscriptions = _subscriptions_load()
    found = False
    for sub in subscriptions:
        if sub["payer"] == payer and sub["payee"] == payee:
            sub["amount"] = round(float(amount), 1)
            sub["cycle"] = cycle
            sub["last_paid_timestamp"] = last_paid_timestamp
            sub["next_payment_timestamp"] = next_payment_timestamp
            found = True
            break
    if not found:
        subscriptions.append({
            "payer": payer,
            "payee": payee,
            "amount": round(float(amount), 1),
            "cycle": cycle,
            "last_paid_timestamp": last_paid_timestamp,
            "next_payment_timestamp": next_payment_timestamp
        })
    _subscriptions_save(subscriptions)


def remove_subscription(payer, payee):
    payer = fix_name(payer)
    payee = fix_name(payee)
    subscriptions = _subscriptions_load()
    initial_count = len(subscriptions)
    subscriptions = [sub for sub in subscriptions if not (sub["payer"] == payer and sub["payee"] == payee)]
    if len(subscriptions) < initial_count:
        _subscriptions_save(subscriptions)
        return True
    return False


def remove_all_subscriptions_by_payer(payer):
    payer = fix_name(payer)
    subscriptions = _subscriptions_load()
    initial_count = len(subscriptions)
    removed_payees = [sub["payee"] for sub in subscriptions if sub["payer"] == payer]
    subscriptions = [sub for sub in subscriptions if sub["payer"] != payer]
    if len(subscriptions) < initial_count:
        _subscriptions_save(subscriptions)
        return removed_payees
    return []


def get_subscriptions_by_payer(payer):
    payer = fix_name(payer)
    subscriptions = _subscriptions_load()
    return [sub for sub in subscriptions if sub["payer"] == payer]


def get_all_subscriptions():
    return _subscriptions_load()

# --- Company Management

def _companies_load():
    companies = []
    lockfile = COMPANIES_FILE + ".lock"
    with FileLock(lockfile):
        if not os.path.exists(COMPANIES_FILE):
            return companies
        with open(COMPANIES_FILE, "r") as f:
            for line in f:
                try:
                    company = ast.literal_eval(line.strip())
                    if isinstance(company, dict) and all(k in company for k in ["name", "founder", "members"]):
                        companies.append(company)
                except (ValueError, SyntaxError):
                    continue
    return companies


def _companies_save(companies):
    lockfile = COMPANIES_FILE + ".lock"
    tmp_file = COMPANIES_FILE + ".tmp"
    with FileLock(lockfile):
        with open(tmp_file, "w") as f:
            for company in companies:
                f.write(str(company) + "\n")
        os.replace(tmp_file, COMPANIES_FILE)


def add_company(name, founder):
    name = fix_name(name)
    founder = fix_name(founder)
    companies = _companies_load()
    if any(c["name"] == name for c in companies):
        return False
    companies.append({"name": name, "founder": founder, "members": [founder]})
    _companies_save(companies)
    return True


def add_company_member(company_name, username_to_add):
    company_name = fix_name(company_name)
    username_to_add = fix_name(username_to_add)
    companies = _companies_load()
    updated = False
    for company in companies:
        if company["name"] == company_name:
            if username_to_add not in company["members"]:
                company["members"].append(username_to_add)
                updated = True
            break
    if updated:
        _companies_save(companies)
        return True
    return False


def is_company_member(company_name, username):
    company_name = fix_name(company_name)
    username = fix_name(username)
    companies = _companies_load()
    for company in companies:
        if company["name"] == company_name:
            return username in company["members"]
    return False


def get_company_data(company_name):
    company_name = fix_name(company_name)
    companies = _companies_load()
    for company in companies:
        if company["name"] == company_name:
            return company
    return None


def is_company(name):
    """Return True if the given account name belongs to a registered company."""
    return get_company_data(name) is not None


def get_companies_for_user(username):
    """Return a list of companies the given user belongs to."""
    username = fix_name(username)
    companies = _companies_load()
    return [c for c in companies if username in c.get("members", [])]


def get_all_companies():
    return _companies_load()

# --- Leaderboard and Timestamp

def get_leaderboard(amount, offset):
    balances = _balances_load()
    sorted_bal = sorted(balances.items(), key=lambda x: x[1], reverse=True)
    sliced = sorted_bal[offset:offset + amount]
    return {k: round(v, 1) for k, v in sliced}


def create_leaderboard():
    top = get_leaderboard(100, 0)
    entries = []
    for name, bal in top.items():
        label = f"{name} (CO)" if is_company(name) else name
        entries.append(f"{label}: {bal:.1f}")
    return entries


def generate_readable_timestamp():
    current_datetime = datetime.now()
    return current_datetime.strftime("%H:%M on %m/%d/%y")

# --- Backup helper ---

def backup_every_n_minutes(n=10, max_backups=10):
    def backup_func():
        while True:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_folder = os.path.join(BACKUP_DIR, timestamp)
                ensure_dir(dest_folder)
                for fname in ["balances.txt", "transactions.txt", "processed_comments.txt", "subscriptions.txt", "companies.txt"]:
                    src = os.path.join(DATA_DIR, fname)
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(dest_folder, fname))
                for d in ["notifications", "preferences"]:
                    src_dir = os.path.join(DATA_DIR, d)
                    if os.path.exists(src_dir):
                        dst_dir = os.path.join(dest_folder, d)
                        if os.path.exists(dst_dir):
                            shutil.rmtree(dst_dir)
                        shutil.copytree(src_dir, dst_dir)
                backups = sorted(os.listdir(BACKUP_DIR))
                if len(backups) > max_backups:
                    for to_del in backups[:-max_backups]:
                        fullpath = os.path.join(BACKUP_DIR, to_del)
                        try:
                            if os.path.isdir(fullpath):
                                shutil.rmtree(fullpath)
                            else:
                                os.remove(fullpath)
                        except Exception as e:
                            print(f"Error deleting old backup {fullpath}: {e}")
                print(f"Backup completed at {timestamp}")
            except Exception as e:
                print(f"Backup failed: {e}")
            time.sleep(n * 60)
    t = threading.Thread(target=backup_func, daemon=True)
    t.start()
