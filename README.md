# ECKOBits Server

ECKOBits is an automated virtual economy for Scratch projects built with the `scratchattach` library. It listens for cloud requests and comment commands to manage balances, subscriptions, and company accounts.

**Current version:** 0.6.5

## Features

- User balances and transaction history
- Recurring payments with daily, weekly, or monthly cycles
- Company accounts with multiple authorized members
- Leaderboard generation and notifications
- Automated backups every 10 minutes
- Automatic remote GitHub backups retaining the latest 20 snapshots

## Setup

1. *(Optional)* create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Place your Scratch session ID in `secrets/session_id.txt`.
4. **(Important for Natural Language Commands)**: If you plan to use the `!n` command, create a `gemini_config.py` file at the root of the project and populate it with your Gemini API Key. A template is provided below:
   ```python
   # gemini_config.py
   GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY'
   # ... (other configurations will default if not present, but API key is crucial)
   ```
   Ensure `gemini_config.py` includes at least `GEMINI_API_KEY`. Other configurations like model names and rate limits will use defaults from the provided `gemini_config.py` if you created one in an earlier step, or internal defaults if the file is minimal.
5. Start the server:
   ```bash
   python3 main.py
   ```

## Usage

### Comment Commands
Commands can be posted directly in the Scratch project comments. The `!` prefix is accepted for compatibility.

- `s <user> <amount>` – send bits to another user
- `sub <user> <amount> <daily|weekly|monthly>` – subscribe to pay a user periodically
- `can <user>` – cancel a subscription to the specified user
- `canall` – cancel all active subscriptions
- `found <initial_amount>` – create a company named `<username> company`
- `add <company_name> <username>` – authorize a member to manage your company
- `sendco <company_name> <recipient> <amount>` – send bits from a company account

### Natural Language Commands (`!n`)

You can use natural language to perform actions by using the `!n` command.
The system will use a Google Gemini AI model to understand your request and translate it into one or more standard ECKOBits commands.

**Format:** `!n [your request]`

**Examples:**
- `!n send 20 bits to rothorius`
- `!n please cancel all of my subscriptions and then found a company for me with 500 bits`
- `!n can u sub to userA for 10 daily and also send userB 25 bits from mycompany`

The AI will attempt to process your request using available commands: `s`, `sub`, `can`, `canall`, `found`, `add`, `sendco`.
It will respect usage limits and try different AI models if necessary. You will receive notifications on the outcome.
**Please ensure your Gemini API key is correctly configured in `gemini_config.py` (see Setup section) for this feature to work.**

### Cloud Requests

- `balance` – retrieve your balance and ensure you have an account
- `get_preferences` / `set_preferences` – manage user preferences
- `give` – send bits to another user
- `search` – view another user's balance
- `leaderboard` – list the top balances
- `notifications` – fetch your notifications

### Backups

The server keeps the latest ten backups in the `backups/` directory, saving every ten minutes automatically.
Backups are also pushed to the remote GitHub repository defined in `data.py`.
Only new changes are committed and the remote retains the most recent 20 backups.

## Roadmap

Planned improvements for future releases:

- Better administration tools
- Web dashboard for viewing balances and statistics
- More robust logging and error handling
- Localization support
- Enhanced security for cloud interactions

## Acknowledgements

This project uses the open-source `scratchattach` library. Development has been refined with help from **OpenAI Codex**, which improved parts of the codebase and documentation.
The natural language processing feature utilizes Google's Gemini models.
