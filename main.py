# This Bot is intended to control ShinobiCCTV, at this moment it is possible to activate states but I am working on....
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github 
# or donate me a coffee with Paypal
# ToDo: if "chat_id" in INI file is populated implement control that the bot should only respond to authorized ids

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import logging
import requests
import json
import configparser
import os

# Defining root variables
config_file = "config.ini"
dataIni = {}

# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def clean_config_value(value):
    # Remove comments after '#' character
    return value.split("#")[0].strip()

def iniExistence():
    if os.path.exists(config_file): 
        # Create a ConfigParser object
        config = configparser.ConfigParser()
        config.read(config_file)
        # Read INI file
        for section in config.sections():
            options = config.items(section)
            data = {}
            for option, value in options:
                cleaned_value = clean_config_value(value)
                data[option] = cleaned_value
            dataIni[section] = data
        #printJson(dataIni, "INI settings") # Only for debug purpouse, enable line below to stamp stdout ini settings
        return(True)
    else:
        print(f"Config file '{config_file}' not found.")
        return(False)
    
        # Telegram/Bot commands definition:
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm Shinotify Bot, and I am ready!\nGlad to serve you \u263A")
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "Available commands are:\n"
    help_text += "/start - Start this bot\n"
    help_text += "/states - List all states\n"
    help_text += "/help - Where you are\n"
    await context.bot.send_message(chat_id=update.effective_chat.id,text=help_text)

async def states_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"{dataIni['Shinobi']['url']}:{dataIni['Shinobi']['port']}/{dataIni['Shinobi']['api_key']}/monitorStates/{dataIni['Shinobi']['group_key']}"
    response = requests.get(url).json()
    states = []
    for i in response['presets']:
        states.append(i['name'])
    #printJson(states) # Only for debug purpouse, enable line below to stamp stdout ini settings
    if states:
        buttons = []
        for state in states:
            buttons.append([InlineKeyboardButton(state, callback_data=state)])
        #keyboard = [command_options]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Push one state to activate:', reply_markup=reply_markup)
    else:
        print('No states found \u26A0\ufe0f')
        await context.bot.send_message(chat_id=update.effective_chat.id, text='No states found \u26A0\ufe0f')

async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    state = query.data
    if state:
        url = f"{dataIni['Shinobi']['url']}:{dataIni['Shinobi']['port']}/{dataIni['Shinobi']['api_key']}/monitorStates/{dataIni['Shinobi']['group_key']}/{state}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f'something went wrong, request error \u26A0\ufe0f')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'something went wrong, request error \u26A0\ufe0f')
        else:
            print(f'OK, done \U0001F44D')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')
    else:
        print(f'No states found \u26A0\ufe0f')
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'No states found \u26A0\ufe0f')
    
def printJson(value, text = 'nothing'):
    json_output = json.dumps(value, indent=4)
    print(f"\n{text} (JSON output):")
    print(json_output)

if __name__ == '__main__':
    if iniExistence():
        application = ApplicationBuilder().token(dataIni['Telegram']['api_key']).build()
        
        start_handler = CommandHandler('start', start_command)
        help_handler = CommandHandler('help', help_command)
        states_handler = CommandHandler('states', states_command)
        callback_query_handler = CallbackQueryHandler(callback_handler)
        
        application.add_handlers([start_handler, help_handler, states_handler, callback_query_handler])
        
        application.run_polling()
    else:
        print('INI file missed, please provide one.')

