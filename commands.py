from datetime import timedelta
import time
import data

# Cycle times for subscriptions
CYCLE_TIMES = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


def process_comment_command(comment_author, command_parts):
    command = command_parts[0].lower().lstrip("!")
    sender = data.fix_name(comment_author)
    ts = data.generate_readable_timestamp()

    if command == "s":
        if len(command_parts) != 3:
            data.add_notification(sender, f"{ts} - Invalid s command format. Use s [user] [amount].")
            return
        receiver = data.fix_name(command_parts[1])
        try:
            amount = round(float(command_parts[2]), 1)
        except ValueError:
            data.add_notification(sender, f"{ts} - Invalid amount for !s command.")
            return
        if sender == receiver:
            data.add_notification(sender, f"{ts} - You cannot send bits to yourself.")
            return
        if amount <= 0:
            data.add_notification(sender, f"{ts} - Amount must be positive for !s command.")
            return
        sender_balance = data.get_balance(sender)
        if sender_balance < amount:
            data.add_notification(sender, f"{ts} - Insufficient balance ({sender_balance:.1f} bits) to send {amount:.1f} bits to {receiver}.")
            return
        receiver_balance = data.get_balance(receiver)
        data.set_balance(sender, sender_balance - amount)
        data.set_balance(receiver, receiver_balance + amount)
        data.save_transaction(sender, receiver, amount)
        data.add_notification(receiver, f"{ts} - {sender} gave you {amount:.1f} bits via comment!")
        data.add_notification(sender, f"{ts} - You gave {amount:.1f} bits to {receiver} via comment. Your new balance: {data.get_balance(sender):.1f}")
        print(f"Processed s command: {sender} sent {amount} to {receiver}")

    elif command == "sub":
        if len(command_parts) != 4:
            data.add_notification(sender, f"{ts} - Invalid sub command format. Use sub [user] [amount] [daily/weekly/monthly].")
            return
        payee = data.fix_name(command_parts[1])
        try:
            amount = round(float(command_parts[2]), 1)
        except ValueError:
            data.add_notification(sender, f"{ts} - Invalid amount for !sub command.")
            return
        cycle_type = command_parts[3].lower()
        if cycle_type not in CYCLE_TIMES:
            data.add_notification(sender, f"{ts} - Invalid cycle type for !sub. Use daily, weekly, or monthly.")
            return
        if sender == payee:
            data.add_notification(sender, f"{ts} - You cannot subscribe to yourself.")
            return
        if amount <= 0:
            data.add_notification(sender, f"{ts} - Subscription amount must be positive.")
            return
        sender_balance = data.get_balance(sender)
        if sender_balance < amount:
            data.add_notification(sender, f"{ts} - Insufficient balance ({sender_balance:.1f} bits) for initial subscription payment of {amount:.1f} bits to {payee}.")
            return
        receiver_balance = data.get_balance(payee)
        data.set_balance(sender, sender_balance - amount)
        data.set_balance(payee, receiver_balance + amount)
        data.save_transaction(sender, payee, amount)
        current_time = int(time.time())
        cycle_seconds = CYCLE_TIMES[cycle_type].total_seconds()
        next_payment_timestamp = current_time + cycle_seconds
        data.add_subscription(sender, payee, amount, cycle_type, current_time, next_payment_timestamp)
        data.add_notification(payee, f"{ts} - {sender} subscribed to pay you {amount:.1f} bits every {cycle_type}!")
        data.add_notification(sender, f"{ts} - You subscribed to pay {payee} {amount:.1f} bits every {cycle_type}. Your new balance: {data.get_balance(sender):.1f}")
        print(f"Processed sub command: {sender} subscribed to {payee} for {amount} {cycle_type}")

    elif command == "can":
        if len(command_parts) != 2:
            data.add_notification(sender, f"{ts} - Invalid can command format. Use can [user].")
            return
        payee_to_cancel = data.fix_name(command_parts[1])
        if data.remove_subscription(sender, payee_to_cancel):
            data.add_notification(payee_to_cancel, f"{ts} - {sender} cancelled their subscription to pay you.")
            data.add_notification(sender, f"{ts} - You cancelled your subscription to pay {payee_to_cancel}.")
            print(f"Processed can command: {sender} cancelled subscription to {payee_to_cancel}")
        else:
            data.add_notification(sender, f"{ts} - No active subscription found for {payee_to_cancel} from your account.")

    elif command == "canall":
        if len(command_parts) != 1:
            data.add_notification(sender, f"{ts} - Invalid canall command format. Use canall.")
            return
        removed_payees = data.remove_all_subscriptions_by_payer(sender)
        if removed_payees:
            for payee in removed_payees:
                data.add_notification(payee, f"{ts} - {sender} cancelled their subscription to pay you.")
            data.add_notification(sender, f"{ts} - You cancelled all your active subscriptions ({', '.join(removed_payees)}).")
            print(f"Processed canall command: {sender} cancelled all subscriptions.")
        else:
            data.add_notification(sender, f"{ts} - You have no active subscriptions to cancel.")

    elif command == "found":
        if len(command_parts) != 2:
            data.add_notification(sender, f"{ts} - Invalid found command format. Use found [initial_amount].")
            return
        try:
            initial_amount = round(float(command_parts[1]), 1)
        except ValueError:
            data.add_notification(sender, f"{ts} - Invalid initial amount for !found command.")
            return
        if initial_amount <= 0:
            data.add_notification(sender, f"{ts} - Initial amount for company must be positive.")
            return
        company_name = sender + "company"
        if data.get_company_data(company_name) is not None:
            data.add_notification(sender, f"{ts} - You already own a company: {company_name}. You cannot found another one.")
            return
        sender_balance = data.get_balance(sender)
        if sender_balance < initial_amount:
            data.add_notification(sender, f"{ts} - Insufficient balance ({sender_balance:.1f} bits) to fund your new company with {initial_amount:.1f} bits.")
            return
        data.set_balance(sender, sender_balance - initial_amount)
        data.set_balance(company_name, initial_amount)
        data.save_transaction(sender, company_name, initial_amount)
        if data.add_company(company_name, sender):
            data.add_notification(sender, f"{ts} - You founded a new company: {company_name} with {initial_amount:.1f} bits! Your personal balance: {data.get_balance(sender):.1f}")
            print(f"Processed found command: {sender} founded {company_name} with {initial_amount} bits.")
        else:
            data.add_notification(sender, f"{ts} - Failed to create company {company_name}. It might already exist.")

    elif command == "add":
        if len(command_parts) != 3:
            data.add_notification(sender, f"{ts} - Invalid add command format. Use add [company_name] [username_to_add].")
            return
        company_name_arg = data.fix_name(command_parts[1])
        user_to_add = data.fix_name(command_parts[2])
        company_data = data.get_company_data(company_name_arg)
        if company_data is None:
            data.add_notification(sender, f"{ts} - Company '{company_name_arg}' not found.")
            return
        if not data.is_company_member(company_name_arg, sender):
            data.add_notification(sender, f"{ts} - You are not an authorized member of '{company_name_arg}'.")
            return
        if user_to_add in company_data["members"]:
            data.add_notification(sender, f"{ts} - {user_to_add} is already a member of '{company_name_arg}'.")
            return
        if data.add_company_member(company_name_arg, user_to_add):
            data.add_notification(sender, f"{ts} - You added {user_to_add} to '{company_name_arg}'.")
            data.add_notification(user_to_add, f"{ts} - You have been added as an authorized member to company '{company_name_arg}' by {sender}!")
            print(f"Processed add command: {sender} added {user_to_add} to {company_name_arg}.")
        else:
            data.add_notification(sender, f"{ts} - Failed to add {user_to_add} to '{company_name_arg}'.")

    elif command == "sendco":
        if len(command_parts) != 4:
            data.add_notification(sender, f"{ts} - Invalid sendco command format. Use sendco [company_name] [recipient] [amount].")
            return
        company_name_arg = data.fix_name(command_parts[1])
        recipient = data.fix_name(command_parts[2])
        try:
            amount = round(float(command_parts[3]), 1)
        except ValueError:
            data.add_notification(sender, f"{ts} - Invalid amount for !sendco command.")
            return
        if amount <= 0:
            data.add_notification(sender, f"{ts} - Amount must be positive for !sendco command.")
            return
        if sender == recipient:
            data.add_notification(sender, f"{ts} - You cannot send bits to yourself from a company account.")
            return
        company_data = data.get_company_data(company_name_arg)
        if company_data is None:
            data.add_notification(sender, f"{ts} - Company '{company_name_arg}' not found.")
            return
        if not data.is_company_member(company_name_arg, sender):
            data.add_notification(sender, f"{ts} - You are not an authorized member of '{company_name_arg}' to send funds.")
            return
        company_balance = data.get_balance(company_name_arg)
        if company_balance < amount:
            data.add_notification(sender, f"{ts} - Company '{company_name_arg}' has insufficient balance ({company_balance:.1f} bits) to send {amount:.1f} bits to {recipient}.")
            return
        recipient_balance = data.get_balance(recipient)
        data.set_balance(company_name_arg, company_balance - amount)
        data.set_balance(recipient, recipient_balance + amount)
        data.save_transaction(company_name_arg, recipient, amount)
        data.add_notification(recipient, f"{ts} - Company '{company_name_arg}' sent you {amount:.1f} bits!")
        data.add_notification(sender, f"{ts} - You sent {amount:.1f} bits from '{company_name_arg}' to {recipient}. Company balance: {data.get_balance(company_name_arg):.1f}")
        print(f"Processed sendco command: {sender} sent {amount} from {company_name_arg} to {recipient}.")


def comment_listener_thread(project):
    while True:
        try:
            print("Checking for new comments...")
            comments = project.comments(limit=30)
            for comment in reversed(comments):
                if not data.is_comment_processed(comment.id):
                    content = comment.content
                    author = comment.author_name
                    command_parts = content.strip().split(" ")
                    if not command_parts or not command_parts[0]:
                        data.add_processed_comment(comment.id)
                        continue
                    first_word = command_parts[0].lower()
                    clean_word = first_word.lstrip("!")
                    if clean_word in ["s", "sub", "can", "canall", "found", "add", "sendco"]:
                        print(f"Found command '{content}' from {author} (ID: {comment.id})")
                        process_comment_command(author, command_parts)
                        data.add_processed_comment(comment.id)
                    else:
                        data.add_processed_comment(comment.id)
        except Exception as e:
            print(f"Error in comment listener: {e}")
        time.sleep(1)


def subscription_processor_thread():
    while True:
        try:
            current_time = int(time.time())
            subscriptions = data._subscriptions_load()
            updated_subscriptions = []
            for sub in subscriptions:
                payer = sub["payer"]
                payee = sub["payee"]
                amount = sub["amount"]
                cycle_type = sub["cycle"]
                next_payment_timestamp = sub["next_payment_timestamp"]
                if current_time >= next_payment_timestamp:
                    print(f"Subscription payment due: {payer} to {payee} for {amount} ({cycle_type})")
                    payer_balance = data.get_balance(payer)
                    if payer_balance >= amount:
                        receiver_balance = data.get_balance(payee)
                        data.set_balance(payer, payer_balance - amount)
                        data.set_balance(payee, receiver_balance + amount)
                        data.save_transaction(payer, payee, amount)
                        ts = data.generate_readable_timestamp()
                        data.add_notification(payee, f"{ts} - {payer} paid you {amount:.1f} bits for your {cycle_type} subscription!")
                        data.add_notification(payer, f"{ts} - You paid {amount:.1f} bits to {payee} for your {cycle_type} subscription. Your new balance: {data.get_balance(payer):.1f}")
                        cycle_seconds = CYCLE_TIMES[cycle_type].total_seconds()
                        sub["last_paid_timestamp"] = current_time
                        sub["next_payment_timestamp"] = current_time + cycle_seconds
                        print(f"Payment successful: {payer} to {payee}. Next payment due: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sub['next_payment_timestamp']))}")
                    else:
                        ts = data.generate_readable_timestamp()
                        data.add_notification(payer, f"{ts} - Your subscription payment of {amount:.1f} bits to {payee} failed due to insufficient balance. Subscription cancelled.")
                        data.add_notification(payee, f"{ts} - {payer}'s subscription payment of {amount:.1f} bits failed due to insufficient balance. Subscription cancelled.")
                        print(f"Payment failed: {payer} to {payee}. Insufficient balance. Subscription cancelled.")
                        continue
                updated_subscriptions.append(sub)
            data._subscriptions_save(updated_subscriptions)
        except Exception as e:
            print(f"Error in subscription processor: {e}")
        time.sleep(60)
