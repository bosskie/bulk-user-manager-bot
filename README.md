
# **Bulk Add/Delete Emby, Jellyfin, and Jellyseer Users Using TelegramBot**

![](https://github.com/user-attachments/assets/4904b18e-0b38-43a6-9487-086b09764059)

## **Overview**

This Telegram bot allows you to bulk add/delete users across Emby, Jellyfin, and Jellyseerr services.
- New user is created across **Emby** - **Jellyfin** - **Jellyseerr**
- password for all these will be the username. If you create a user `ABC` password will be `ABC`
- Only For Emby, The user configuration is copied from a existing user you specify in `.env` file.

## **Setup Instructions**

> ### **Prerequisites**
> - Python 3.7+
> - Telegram bot token — from [BotFather](https://core.telegram.org/bots#botfather)
> - API keys and URLs for Emby, Jellyfin, and Jellyseerr

### **[a] - Create a `.env` File**
Create a `.env` file in the same directory as your script with the following content:

```plaintext
TELEGRAM_API_TOKEN=your-telegram-api-token
EMBY_API_KEY=your-emby-api-key
JELLYFIN_API_KEY=your-jellyfin-api-key
JELLYSEERR_API_KEY=your-jellyseerr-api-key
EMBY_URL=http://your-emby-server:8096
JELLYFIN_URL=http://your-jellyfin-server:8096
JELLYSEERR_URL=http://your-jellyseerr-server:5055
SETTINGS_USER=settings  # Name of the emby user to copy settings from.
```

Replace the placeholder values with your actual tokens, API keys, and server URLs.

### **[b] - Install Required Python Libraries**
Install the required Python libraries using pip:

```bash
pip install python-telegram-bot requests python-dotenv
```

### **[c] - Create a New Telegram Bot and add commands**

1. **Open Telegram and Start a Chat with BotFather**
   - Search for `@BotFather` in Telegram and start a chat with it.

2. **Create a New Bot**
   - Type `/newbot` and press Enter.
   - Follow the prompts to:
     - **Name your bot**: Choose a name that will be visible to users.
     - **Choose a username**: It must end with "bot" (e.g., `MyAwesomeBot` or `MyAwesomeBotBot`).

3. **Copy the API Token**
   - After creating the bot, BotFather will provide an API token. **Copy this token**; you’ll need to paste it in `.env`

4. **Define Commands with BotFather**
   - In the chat with BotFather, type `/setcommands` and press Enter.
   - Select your newly created bot.
   - When prompted, add the following commands:
     ```text
     adduser - Add a new user
     deluser - Delete an existing user
     ```
   - Press Enter to confirm.

5. **Commands Overview**
    - **Create Multiple Users**:
    - Command: `/adduser <username1> <username2> ...`
    - Automatically copies settings from the "settings" user in Emby.
   
    - **Delete Multiple Users**:
    - Command: `/deluser <username1> <username2> ...`
    - Deletes users from Emby, Jellyfin, and Jellyseerr.

### **[d] - Bot Script:**
> **CLICK TO TOGGLE** the script
<details>
<summary>Telegram bot script: ⬇️ </summary>

```python
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
EMBY_API_KEY = os.getenv('EMBY_API_KEY')
JELLYFIN_API_KEY = os.getenv('JELLYFIN_API_KEY')
JELLYSEERR_API_KEY = os.getenv('JELLYSEERR_API_KEY')
EMBY_URL = os.getenv('EMBY_URL')
JELLYFIN_URL = os.getenv('JELLYFIN_URL')
JELLYSEERR_URL = os.getenv('JELLYSEERR_URL')
SETTINGS_USER = os.getenv('SETTINGS_USER', 'settings')  # Default to 'settings' if not set

# Command to add multiple users
async def add_user(update: Update, context):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /adduser 'username1' 'username2' ...")
        return

    usernames = context.args
    failed_users = []

    for username in usernames:
        password = username  # Automatically use the username as the password

        emby_result = await create_emby_user(username, password)
        jellyfin_result = await create_jellyfin_user(username, password)

        if emby_result and jellyfin_result:
            jellyseerr_result = await import_jellyfin_users_to_jellyseerr(username)
            if not jellyseerr_result:
                failed_users.append(username)
        else:
            failed_users.append(username)

    if not failed_users:
        await update.message.reply_text(f"All users created successfully in Emby, Jellyfin, and Jellyseerr.")
    else:
        await update.message.reply_text(f"Failed to create or import the following users: {', '.join(failed_users)}")

# Command to delete multiple users
async def del_user(update: Update, context):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /deluser 'username1' 'username2' ...")
        return

    usernames = context.args
    failed_users = []

    for username in usernames:
        emby_result = await delete_emby_user(username)
        jellyfin_result = await delete_jellyfin_user(username)
        jellyseerr_result = await delete_jellyseerr_user(username)

        if not (emby_result and jellyfin_result and jellyseerr_result):
            failed_users.append(username)

    if not failed_users:
        await update.message.reply_text(f"All users deleted successfully from Emby, Jellyfin, and Jellyseerr.")
    else:
        await update.message.reply_text(f"Failed to delete the following users: {', '.join(failed_users)}")

# Function to create Emby user with copied settings from 'settings' user
async def create_emby_user(username, password):
    # Get the 'settings' user's ID
    settings_user_id = None
    settings_url = f"{EMBY_URL}/emby/Users"
    headers = {'X-Emby-Token': EMBY_API_KEY}
    response = requests.get(settings_url, headers=headers)
    if response.status_code != 200:
        return False

    users = response.json()
    for user in users:
        if user['Name'].lower() == SETTINGS_USER.lower():
            settings_user_id = user['Id']
            break

    if not settings_user_id:
        return False

    # Create a new user with settings copied from the 'settings' user
    user_data = {
        'Name': username,
        'Password': password,
        'PasswordResetRequired': False,  # Indicate that the user does not need to reset the password
        'CopyFromUserId': settings_user_id,
        'UserCopyOptions': ["UserPolicy", "UserConfiguration"]
    }

    create_user_url = f"{EMBY_URL}/emby/Users/New"
    response = requests.post(create_user_url, headers=headers, json=user_data)

    if response.status_code != 200:
        return False

    # Setting the password separately if needed
    password_url = f"{EMBY_URL}/emby/Users/{response.json()['Id']}/Password"
    password_data = {
        "CurrentPw": "",  # No current password, since it's a new user
        "NewPw": password
    }
    password_response = requests.post(password_url, headers=headers, json=password_data)

    return password_response.status_code == 204

# Function to create Jellyfin user
async def create_jellyfin_user(username, password):
    url = f"{JELLYFIN_URL}/Users/New"
    headers = {'X-MediaBrowser-Token': JELLYFIN_API_KEY, 'Content-Type': 'application/json'}
    data = {'Name': username, 'Password': password}
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

# Function to delete Emby user
async def delete_emby_user(username):
    # Get the user's ID first
    url = f"{EMBY_URL}/emby/Users"
    headers = {'X-Emby-Token': EMBY_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return False

    users = response.json()
    user_id = None
    for user in users:
        if user['Name'].lower() == username.lower():
            user_id = user['Id']
            break

    if not user_id:
        return False

    # Delete the user
    url = f"{EMBY_URL}/emby/Users/{user_id}"
    response = requests.delete(url, headers=headers)
    return response.status_code == 204

# Function to delete Jellyfin user
async def delete_jellyfin_user(username):
    # Get the user's ID first
    url = f"{JELLYFIN_URL}/Users"
    headers = {'X-MediaBrowser-Token': JELLYFIN_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return False

    users = response.json()
    user_id = None
    for user in users:
        if user['Name'].lower() == username.lower():
            user_id = user['Id']
            break

    if not user_id:
        return False

    # Delete the user
    url = f"{JELLYFIN_URL}/Users/{user_id}"
    response = requests.delete(url, headers=headers)
    return response.status_code == 204

# Function to delete Jellyseerr user
async def delete_jellyseerr_user(username):
    # Get the user's ID first
    url = f"{JELLYSEERR_URL}/api/v1/user"
    headers = {'X-Api-Key': JELLYSEERR_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return False

    data = response.json()
    users = data.get('results', [])

    # Check if the response contains the expected user data
    if isinstance(users, list):  # Assuming users is a list of dictionaries
        user_id = None
        for user in users:
            if isinstance(user, dict) and user.get('jellyfinUsername', '').lower() == username.lower():
                user_id = user['id']
                break

        if not user_id:
            return False

        # Delete the user
        url = f"{JELLYSEERR_URL}/api/v1/user/{user_id}"
        response = requests.delete(url, headers=headers)

        # Check for success status codes (204 or 200)
        if response.status_code in [200, 204]:
            return True
        else:
            print(f"Unexpected status code when deleting Jellyseerr user: {response.status_code}")
            return False
    else:
        print("Unexpected response format:", users)
        return False

# Function to import Jellyfin users into Jellyseerr
async def import_jellyfin_users_to_jellyseerr(new_username):
    # First, get the list of Jellyfin users
    url = f"{JELLYSEERR_URL}/api/v1/settings/jellyfin/users"
    headers = {'X-Api-Key': JELLYSEERR_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return False

    users = response.json()
    new_user = None

    # Find the newly created user by username
    for user in users:
        if user['username'].lower() == new_username.lower():
            new_user = user
            break

    if not new_user:
        return False

    # Import the new user into Jellyseerr
    import_url = f"{JELLYSEERR_URL}/api/v1/user/import-from-jellyfin"
    import_data = {'jellyfinUserIds': [new_user['id']]}
    import_response = requests.post(import_url, headers=headers, json=import_data)

    return import_response.status_code == 201

# Main function
def main():
    application = Application.builder().token(TELEGRAM_API_TOKEN).build()

    application.add_handler(CommandHandler('adduser', add_user))
    application.add_handler(CommandHandler('deluser', del_user))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
```
source: ..emby user config api.. https://emby.media/community/index.php?/topic/127981-create-a-new-user-with-emby-api/
</details>

### **[e] - Running the Bot for testing**
Run the bot using Python:

```bash
python3 telegram_bot.py
```

The bot will start and be ready. 

You can now type /adduser or /deluser in your Telegram bot chat to check.
It should return this message `Usage: /adduser 'username1' 'username2' ...`

## Setting up Systemd service as a background service (Recommended)
To ensure the bot runs automatically and reliably on your Linux system, we set it up as a `systemd` service. This allows the bot to start on boot, restart automatically on failure, and be easily managed through system commands.
### **1. Setting Up the Bot as a Systemd Service**

#### **1.1. Creating the Systemd Service File**

- **Create the service file** at `/etc/systemd/system/telegram_bot.service`:

   ```bash
   sudo nano /etc/systemd/system/telegram_bot.service
   ```

- **Add the following content** to the service file:

   ```python
   [Unit]
   Description=Telegram Bot Service
   After=network.target

   [Service]
   User=your_user # your user 
   WorkingDirectory=/path/to/your/script # where your telegram_bot.py script is located
   ExecStart=/path/to/your/venv/bin/python3 /path/to/your/script/telegram_bot.py # command that runs in short 'python3 telegram_bot.py'
   Restart=always
   EnvironmentFile=/path/to/your/script/.env # create .env where your telegram_bot.py script is

   [Install]
   WantedBy=multi-user.target
   ```

> What to change in service file ?
>    - **User**: Replace `your_user` with the username under which the service should run.
>    - **WorkingDirectory**: Set the working directory where your script resides.
>    - **ExecStart**: The command to start your bot, pointing to the Python interpreter in your virtual environment.
>    - **EnvironmentFile**: The path to your `.env` file containing environment variables.

#### **2.2. Enabling and Starting the Service**

1. **Reload systemd** to recognize the new service:

   ```bash
   sudo systemctl daemon-reload
   ```

2. **Enable the service** to start on boot:

   ```bash
   sudo systemctl enable telegram_bot.service
   ```

3. **Start the service immediately**:

   ```bash
   sudo systemctl start telegram_bot.service
   ```

4. **Check the service status** to ensure it’s running correctly:

   ```bash
   sudo systemctl status telegram_bot.service
   ```

#### **2.3. Managing the Service**

- **Stop the service**:

  ```bash
  sudo systemctl stop telegram_bot.service
  ```

- **Restart the service**:

  ```bash
  sudo systemctl restart telegram_bot.service
  ```

- **View logs**:

  ```bash
  sudo journalctl -u telegram_bot.service
  ```

---
## **Conclusion**

By setting up the Telegram bot as a `systemd` service with environment variables loaded from a `.env` file, you ensure a reliable, automated solution that runs consistently across system reboots. The bot can now efficiently manage multiple users in Emby, Jellyfin, and Jellyseerr, making it a powerful tool for server administrators.
