from datetime import timedelta
import time
import data # data.check_rate_limits, data.record_api_call, data.add_notification, data.generate_readable_timestamp
import google.generativeai as genai
# Using genai.types directly is often cleaner if 'types' is not extensively used standalone.
# from google.generativeai import types # Original
import gemini_config

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
                    clean_word = first_word.lstrip("!")
                    # Updated list of known commands for direct processing
                    known_direct_commands = ["s", "sub", "can", "canall", "found", "add", "sendco"]

                    if clean_word in known_direct_commands:
                        print(f"Found direct command '{content}' from {author} (ID: {comment.id})")
                        # command_parts already includes the command with '!' (e.g., ['!s', 'user', '10'])
                        # or without '!' if lstrip removed it and it was just 's'.
                        # process_comment_command expects '!command' as first part.
                        # Ensure first part has '!' if it was stripped by clean_word logic.
                        # Original command_parts[0] is like '!s' or 's'.
                        # process_comment_command internally lstrips '!' again.
                        # So, it's robust to either ['!s', 'user', '10'] or ['s', 'user', '10'] if first_word was 's'.
                        # However, our clean_word logic means command_parts[0] might be just 's'.
                        # Let's ensure process_comment_command receives it as it expects.
                        # The original `command_parts` is `['!s', 'user', '10']`.
                        # `process_comment_command` does `command_parts[0].lower().lstrip("!")`.
                        # So, passing `command_parts` directly is correct.
                        process_comment_command(author, command_parts)
                        data.add_processed_comment(comment.id)
                    elif clean_word == "n":
                        if len(command_parts) > 1: # e.g., ['!n', 'send', '10', 'to', 'user']
                            natural_input = " ".join(command_parts[1:])
                            print(f"Found natural language command '!n {natural_input}' from {author} (ID: {comment.id})")
                            process_natural_language_command(author, natural_input)
                            data.add_processed_comment(comment.id)
                        else: # Malformed !n command, e.g., just ['!n']
                            ts = data.generate_readable_timestamp()
                            # Ensure author's name is fixed for notification consistency
                            data.add_notification(data.fix_name(author), f"{ts} - Invalid !n command format. Use: !n [your natural language instruction].")
                            data.add_processed_comment(comment.id) # Mark as processed to avoid retrying
                    else:
                        # If it's not a known direct command and not '!n',
                        # and it started with '!', it's an unknown command.
                        # Otherwise, it's just a regular comment not intended for the bot.
                        if first_word.startswith("!"):
                             print(f"Unknown command '{content}' from {author} (ID: {comment.id}). Marked as processed.")
                        # Always mark as processed to prevent re-evaluation in next cycle.
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


def get_gemini_command_response(natural_language_input: str, model_name: str, api_key: str) -> str | None:
    """
    Gets a command response from the Gemini API based on natural language input.

    Args:
        natural_language_input: The user's input in natural language.
        model_name: The name of the Gemini model to use.
        api_key: The Gemini API key.

    Returns:
        The command string from Gemini, or None if an error occurs or no command is found.
    """
    try:
        # Ensure API key is configured for each call, as genai might be used by other parts or configured differently elsewhere.
        genai.configure(api_key=api_key, transport='rest')

        model_with_system_instruction = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=gemini_config.SYSTEM_INSTRUCTION
        )

        generation_config_obj = genai.types.GenerationConfig(
            candidate_count=1
        )

        response = model_with_system_instruction.generate_content(
            contents=[natural_language_input],
            generation_config=generation_config_obj
        )

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
                if response_text:
                    return response_text.strip()
                else:
                    finish_reason_enum = genai.types.Candidate.FinishReason
                    if candidate.finish_reason != finish_reason_enum.STOP:
                         print(f"Warning: Gemini response candidate for {model_name} finished due to: {candidate.finish_reason.name}")
                    else:
                         print(f"Warning: Gemini response candidate for {model_name} has part but no text, finish_reason: {candidate.finish_reason.name}.")
                    return None
            elif hasattr(response, 'text') and response.text: # Fallback
                 return response.text.strip()
            else:
                print(f"Warning: Gemini response for {model_name} has candidates but no parsable text content.")
                return None
        else:
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(f"Warning: Gemini API request for {model_name} was blocked. Reason: {response.prompt_feedback.block_reason.name}")
            else:
                print(f"Warning: Gemini response for {model_name} has no candidates.")
            return None

    except genai.types.BlockedPromptException as e:
        print(f"Gemini API request for {model_name} blocked due to prompt: {e}")
        return None
    except genai.core.exceptions.PermissionDenied as e: # Specific exception for permission issues
        print(f"Gemini API request for {model_name} failed due to permission denied (check API key and access to model): {e}")
        return None
    except genai.core.exceptions.GoogleAPIError as e:
        print(f"Error interacting with Gemini API ({model_name}): {e}")
        return None
    except Exception as e: # Catch any other unexpected errors
        print(f"Generic error during Gemini API call for {model_name}: {e}")
        return None


def process_natural_language_command(comment_author: str, natural_language_input: str):
    """
    Processes a natural language command by trying available Gemini models.
    """
    author_name_fixed = data.fix_name(comment_author) # Use fixed name for rate limiting and notifications

    for model_config in gemini_config.get_model_configs():
        model_name = model_config['name']

        can_use_model = data.check_rate_limits(author_name_fixed, model_name)

        if can_use_model:
            print(f"Attempting to use model: {model_name} for user {author_name_fixed} for input: '{natural_language_input}'")
            # Ensure GEMINI_API_KEY is correctly passed; it's defined in gemini_config
            gemini_response_text = get_gemini_command_response(natural_language_input, model_name, gemini_config.GEMINI_API_KEY)

            if gemini_response_text is not None and gemini_response_text.strip():
                data.record_api_call(author_name_fixed, model_name)
                potential_commands = gemini_response_text.strip().split('\n')

                if not potential_commands or not potential_commands[0].strip():
                    ts = data.generate_readable_timestamp()
                    data.add_notification(author_name_fixed, f"{ts} - Your natural language command was processed by {model_name} but resulted in no specific action.")
                    print(f"User {author_name_fixed}, model {model_name}: NL command processed, no action from AI output '{gemini_response_text}'.")
                    return # Successfully processed by AI, but no command output.

                executed_at_least_one = False
                known_commands = ["s", "sub", "can", "canall", "found", "add", "sendco"]

                for cmd_line in potential_commands:
                    cmd_line = cmd_line.strip()
                    if cmd_line:
                        gemini_command_parts = cmd_line.split(" ")
                        if not gemini_command_parts: continue

                        actual_command_keyword = gemini_command_parts[0].lower()

                        if actual_command_keyword in known_commands:
                            print(f"User {author_name_fixed}, model {model_name}: Executing AI generated command: !{actual_command_keyword} {' '.join(gemini_command_parts[1:])}")
                            # process_comment_command expects the author name and the full command parts list
                            # where the first part is the command including "!"
                            process_comment_command(comment_author, [f"!{actual_command_keyword}"] + gemini_command_parts[1:])
                            executed_at_least_one = True
                        else:
                            ts = data.generate_readable_timestamp()
                            error_msg = f"{ts} - Skipped unknown command from AI ({model_name}): '{cmd_line}'."
                            print(error_msg) # Also print to server log for debugging
                            data.add_notification(author_name_fixed, error_msg)

                if executed_at_least_one:
                    # Optionally, notify user that command from AI was run
                    # ts = data.generate_readable_timestamp()
                    # data.add_notification(author_name_fixed, f"{ts} - Your natural language command was successfully executed by {model_name}.")
                    return # Stop trying other models if commands were processed
                elif not executed_at_least_one and potential_commands and potential_commands[0].strip():
                    # AI returned something, but it wasn't a runnable command (e.g. just text, or unknown command)
                    ts = data.generate_readable_timestamp()
                    msg = f"{ts} - AI ({model_name}) processed your request but didn't return a recognized command. AI Output: '{gemini_response_text}'"
                    data.add_notification(author_name_fixed, msg)
                    print(f"User {author_name_fixed}, model {model_name}: AI output not a recognized command: '{gemini_response_text}'.")
                    return # Handled by this model, even if not runnable.
            else: # Gemini returned None or empty string
                print(f"Model {model_name} returned no valid response or an empty response for user {author_name_fixed}. Response: '{gemini_response_text}'")
                # Optionally notify user model failed, or just try next model silently
                # ts = data.generate_readable_timestamp()
                # data.add_notification(author_name_fixed, f"{ts} - Model {model_name} could not process your request at this time.")
                # Continue to the next model (fallback)
        else:
            print(f"Rate limit check failed for user {author_name_fixed}, model {model_name}.")

    # If loop finishes, all models failed or were rate-limited
    ts = data.generate_readable_timestamp()
    final_msg = f"{ts} - Sorry, your natural language command could not be processed at this time. All models are currently unavailable or rate-limited."
    data.add_notification(author_name_fixed, final_msg)
    print(f"User {author_name_fixed}: All models failed or rate-limited for NL command: '{natural_language_input}'.")
