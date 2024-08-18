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
AUTHORIZED_USERS = list(map(int, os.getenv('AUTHORIZED_USERS', '').split(',')))
    
# Function to check if the user is authorized
def is_authorized(user_id):
    print(f"User ID: {user_id}")  # This will print the user ID to your console or logs
    return user_id in AUTHORIZED_USERS

# Command to add multiple users
async def add_user(update: Update, context):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /adduser username1 username2 ...")
        return

    usernames = context.args
    emby_success = []
    jellyfin_success = []
    jellyseerr_success = []

    for username in usernames:
        password = username  # Automatically use the username as the password

        emby_result = jellyfin_result = jellyseerr_result = True

        if EMBY_API_KEY and EMBY_URL:
            try:
                emby_result = await create_emby_user(username, password)
                if emby_result:
                    emby_success.append(username)
            except Exception as e:
                emby_result = False

        if JELLYFIN_API_KEY and JELLYFIN_URL:
            try:
                jellyfin_result = await create_jellyfin_user(username, password)
                if jellyfin_result:
                    jellyfin_success.append(username)
            except Exception as e:
                jellyfin_result = False

        if JELLYSEERR_API_KEY and JELLYSEERR_URL and jellyfin_result:
            try:
                jellyseerr_result = await import_jellyfin_users_to_jellyseerr(username)
                if jellyseerr_result:
                    jellyseerr_success.append(username)
            except Exception as e:
                jellyseerr_result = False

    messages = []
    if emby_success:
        messages.append(f"Following Emby users created successfully:\n{' '.join(emby_success)}")
    if jellyfin_success:
        messages.append(f"Following Jellyfin users created successfully:\n{' '.join(jellyfin_success)}")
    if jellyseerr_success:
        messages.append(f"Following Jellyseerr users imported successfully:\n{' '.join(jellyseerr_success)}")

    await update.message.reply_text("\n".join(messages))

# Command to delete multiple users
async def del_user(update: Update, context):
    if not is_authorized(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /deluser username1 username2 ...")
        return

    usernames = context.args
    emby_success = []
    jellyfin_success = []
    jellyseerr_success = []

    for username in usernames:
        emby_result = jellyfin_result = jellyseerr_result = True

        if EMBY_API_KEY and EMBY_URL:
            try:
                emby_result = await delete_emby_user(username)
                if emby_result:
                    emby_success.append(username)
            except Exception as e:
                emby_result = False

        if JELLYFIN_API_KEY and JELLYFIN_URL:
            try:
                jellyfin_result = await delete_jellyfin_user(username)
                if jellyfin_result:
                    jellyfin_success.append(username)
            except Exception as e:
                jellyfin_result = False

        if JELLYSEERR_API_KEY and JELLYSEERR_URL:
            try:
                jellyseerr_result = await delete_jellyseerr_user(username)
                if jellyseerr_result:
                    jellyseerr_success.append(username)
            except Exception as e:
                jellyseerr_result = False

    messages = []
    if emby_success:
        messages.append(f"Following Emby users deleted successfully:\n{' '.join(emby_success)}")
    if jellyfin_success:
        messages.append(f"Following Jellyfin users deleted successfully:\n{' '.join(jellyfin_success)}")
    if jellyseerr_success:
        messages.append(f"Following Jellyseerr users deleted successfully:\n{' '.join(jellyseerr_success)}")

    await update.message.reply_text("\n".join(messages))

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
