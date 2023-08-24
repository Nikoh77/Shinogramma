# This Bot is intended to control ShinobiCCTV, at this moment it is possible to activate states but I am working on....
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github 
# or donate me a coffee with Paypal
# ToDo: if "chat_id" in INI file is populated implement control that the bot should only respond to authorized ids

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import ini_check
import logging
import requests
import json

# Defining root variables
config_file = "config.ini"
settings = {}
# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
    url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitorStates/{settings['Shinobi']['group_key']}"
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
        url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitorStates/{settings['Shinobi']['group_key']}/{state}"
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
    needed = {'Telegram':['api_key'],'Shinobi':['api_key','group_key','url','port']}
    result = ini_check.iniCheck(needed,config_file)
    if result:
        settings = ini_check.settings
        application = ApplicationBuilder().token(settings['Telegram']['api_key']).build()
        
        start_handler = CommandHandler('start', start_command)
        help_handler = CommandHandler('help', help_command)
        states_handler = CommandHandler('states', states_command)
        callback_query_handler = CallbackQueryHandler(callback_handler)
        
        application.add_handlers([start_handler, help_handler, states_handler, callback_query_handler])
        
        application.run_polling()
    else:
        print('INI file missed, please provide one.')

