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
