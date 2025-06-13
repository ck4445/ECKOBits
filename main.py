import scratchattach as sa
import threading
import data
import commands

with open('secrets/session_id.txt', 'r') as session_id_txt:
    session_id = session_id_txt.read().strip()

project_id = 1169901452
session = sa.login_by_id(session_id, username='OfficialECKO')
cloud = session.connect_cloud(project_id)
client = cloud.requests(used_cloud_vars=['1\u200e', '2\u200e', '3\u200e', '4\u200e'])
project = session.connect_project(project_id)


@client.request
def balance():
    requester = data.fix_name(client.get_requester())
    bal = data.get_balance(requester)
    notifs = data.get_notifications(requester)
    if not notifs:
        data.add_notification(requester, 'Welcome! No new notifications.')
    return f"{bal:.1f}"


@client.request
def get_preferences():
    requester = data.fix_name(client.get_requester())
    prefs = data.get_preferences(requester)
    return [prefs[i] for i in prefs]


@client.request
def set_preferences(theme, mute):
    requester = data.fix_name(client.get_requester())
    data.set_preferences(requester, theme, mute)
    return 'updated preferences'


@client.request
def give(amount, user):
    try:
        amount = round(float(amount), 1)
    except ValueError:
        return 'Invalid amount.'
    sender = data.fix_name(client.get_requester())
    user = data.fix_name(user)
    if sender == user:
        return 'You cannot send bits to yourself.'
    if amount <= 0:
        return 'Amount must be positive.'
    sender_balance = data.get_balance(sender)
    if sender_balance < amount:
        return 'Insufficient balance.'
    receiver_balance = data.get_balance(user)
    data.set_balance(sender, sender_balance - amount)
    data.set_balance(user, receiver_balance + amount)
    ts = data.generate_readable_timestamp()
    data.add_notification(user, f"{ts} - {sender} gave you {amount:.1f} bits!")
    data.add_notification(sender, f"{ts} - You gave {amount:.1f} bits to {user}!")
    data.save_transaction(sender, user, amount)
    return f"{data.get_balance(sender):.1f}"


@client.request
def search(user):
    user = data.fix_name(user)
    bal = data.get_balance(user)
    if bal is not None:
        return f"{user} has {bal:.1f} bits!"
    return f"{user}'s balance couldn't be found. Did you spell it right?"


@client.request
def leaderboard():
    return data.create_leaderboard()


@client.request
def notifications():
    requester = data.fix_name(client.get_requester())
    notifs = data.get_notifications(requester)
    if not notifs:
        return 'No notifications!'
    return notifs


@client.event
def on_ready():
    print('Request handler is running')


def main():
    data.backup_every_n_minutes(10, 10, 20)
    comment_thread = threading.Thread(target=commands.comment_listener_thread, args=(project,), daemon=True)
    comment_thread.start()
    subscription_thread = threading.Thread(target=commands.subscription_processor_thread, daemon=True)
    subscription_thread.start()
    client.start(thread=True)


if __name__ == '__main__':
    main()
