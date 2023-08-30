import os
import subprocess
import gettext


def compile_translations(localedir):
    for language in os.listdir(localedir):
        lang_dir = os.path.join(localedir, language)
        if os.path.isdir(lang_dir):
            mo_dir = os.path.join(lang_dir, 'LC_MESSAGES')
            os.makedirs(mo_dir, exist_ok=True)
            mo_file = os.path.join(mo_dir, 'messages.mo')
            po_file = os.path.join(lang_dir, 'messages.po')
            subprocess.run(['msgfmt', '-o', mo_file, po_file])



def install_requirements():
    subprocess.check_call(['pip', 'install', '-r', 'requirements.txt'])

def main():
    # Install required packages
    install_requirements()

    # Get the user's preferred language
    language = input("Select your preferred language (en/ru): ").strip()

    # Compile translations
    localedir = os.path.join(os.path.dirname(__file__), 'locales')
    compile_translations(localedir)

    # Configure gettext for the selected language
    lang = gettext.translation('messages', localedir, languages=[language])
    lang.install()

    # Get the bot token and developer chat ID from the user
    bot_token = input(_("Enter your Telegram bot token: ")).strip()
    developer_id = input(_("Enter your developer chat ID: ")).strip()

    # Update the configuration file with the bot token and developer chat ID
    with open('bot.py', 'r') as f:
        content = f.read()
    content = content.replace('YOUR_API_TOKEN', bot_token)
    content = content.replace('YOUR_ID', developer_id)  # Replace with your developer chat ID
    with open('bot.py', 'w') as f:
        f.write(content)

    # Run the bot
    subprocess.Popen(['python3', 'bot.py'])

    print(_("Bot setup completed and bot started!"))

if __name__ == "__main__":
    main()
