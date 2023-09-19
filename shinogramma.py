# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram.
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github 
# or donate me a coffee

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InlineQueryResultVideo, constants
from functools import wraps
from monitor import monitor
import ini_check
import logging
import requests
import inspect
import re
import json

# Defining root variables
config_file = "config.ini"
commands = []

# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
# Start decorators section
def restricted(func):
    """Restrict chat only with id in config.ini."""
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if not telegramChatId:
            print('WARN: chat_id not defined, continuing...')
            return func(update, context, *args, **kwargs)
        chat_id = update.effective_user.id
        if chat_id not in telegramChatId:
            print("Unauthorized access denied for {}.".format(chat_id))
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def send_action(action):
    """Sends `action` while processing func command."""
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            chat_id = update.effective_user.id
            await context.bot.send_chat_action(chat_id=chat_id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    return decorator
# End decorators section

# Telegram/Bot commands definition:
@restricted
@send_action(constants.ChatAction.TYPING)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Below line is to remember how to set a context but unusefull IMHO, tag system work mutch better...
    # context.user_data["originating_function"] = inspect.currentframe().f_code.co_name
    chat_id=update.effective_chat.id
    desc='Start this bot'
    tag = 'start'
    keyboard=[]
    for command in commands:
        keyboard.append([InlineKeyboardButton('/'+command['command'], callback_data=None)])
    reply_markup = ReplyKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="I'm Shinogramma Bot, and I am ready!\nGlad to serve you \u263A", reply_markup=reply_markup)
    # Below line is to remember how to update/edit a sended message
    # await update.message.reply_text("Seleziona un comando:", reply_markup=reply_markup)

@restricted
@send_action(constants.ChatAction.TYPING)    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='Where you are'
    tag = 'help'
    help_text = "Available commands are:\n"
    keyboard=[]
    for command in commands:
        help_text += f'{command["desc"]}\n'
        keyboard.append([InlineKeyboardButton('/'+command['command'], callback_data=None)])
    reply_markup = ReplyKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id,text=help_text, reply_markup=reply_markup)

@restricted
@send_action(constants.ChatAction.TYPING)
async def monitors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='List all monitors'
    tag='monitors'
    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitor/{shinobiGroupKey}"
    data= await queryUrl(chat_id, context, url)
    if data:
        monitors = []
        for i in data:
            monitors.append({'name':i['name'],'id':i['mid']})
        if monitors:
            buttons = []
            for monitor in monitors:
                buttons.append([InlineKeyboardButton(monitor['name'], callback_data=tag+';'+monitor['id'])])
            reply_markup = InlineKeyboardMarkup(buttons)
            await context.bot.send_message(chat_id=chat_id, text='Push one monitor:', reply_markup=reply_markup)
        else:
            print('No monitors found \u26A0\ufe0f')
            await context.bot.send_message(chat_id=chat_id, text='No monitors found \u26A0\ufe0f')

@restricted
@send_action(constants.ChatAction.TYPING) 
async def monitors_subcommand(update: Update, context: ContextTypes.DEFAULT_TYPE, mid):
    chat_id=update.effective_chat.id
    tag='submonitors'
    choices=['snapshot', 'stream', 'videos', 'configure']
    buttons = []
    for choice in choices:
        buttons.append([InlineKeyboardButton(choice, callback_data=tag+';'+choice+';'+mid)])
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=chat_id, text='What do you want from this monitor?', reply_markup=reply_markup)

@restricted
@send_action(constants.ChatAction.TYPING) 
async def states_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='List all states'
    tag='states'
    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitorStates/{shinobiGroupKey}"
    data= await queryUrl(chat_id, context, url)
    if data:
        states = []
        for i in data['presets']:
            states.append(i['name'])
        if states:
            buttons = []
            for state in states:
                buttons.append([InlineKeyboardButton(state, callback_data=tag+';'+state)])
            reply_markup = InlineKeyboardMarkup(buttons)
            await context.bot.send_message(chat_id=chat_id, text='Push one state to activate:', reply_markup=reply_markup)
        else:
            print('No states found \u26A0\ufe0f')
            await context.bot.send_message(chat_id=chat_id, text='No states found \u26A0\ufe0f')

@restricted
@send_action(constants.ChatAction.TYPING) 
async def callback_handler(update: Update, context: CallbackContext):
    chat_id=update.effective_chat.id
    query = update.callback_query
    inputdata = query.data.split(';')
    tag = inputdata[0]
    if tag=='states':
        url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitorStates/{shinobiGroupKey}/{inputdata[1]}"
        data= await queryUrl(chat_id, context, url)
        if data:
            await query.answer('OK, done \U0001F44D')
    elif tag=='monitors':
        # Below line is to remember how to delete a message after tapped on
        # await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        await monitors_subcommand(update, context, inputdata[1])
    elif tag=='submonitors':
        mid=inputdata[2]
        thisMonitor=monitor(shinobiBaseUrl, shinobiPort, shinobiApiKey, shinobiGroupKey, mid)
        if inputdata[1]=='snapshot':
            if not await thisMonitor.getsnapshot(context, chat_id, query):
                key = 'snap'
                value = '1'
                desc = 'Jpeg API for snapshots'
                await query.answer("Jpeg API not active on this monitor \u26A0\ufe0f")
                await configuremonitor_subcommand(update, context, thisMonitor.mid, key, value, desc)
        elif inputdata[1]=='stream':
            await thisMonitor.getstream(context, chat_id, query)
        elif inputdata[1]=='videos':
            await context.bot.send_message(chat_id=chat_id, text='Sorry, it\'s not yet possible to see videos but I am working on... \u26A0\ufe0f')
        elif inputdata[1]=='configure':
            #test=await thisMonitor.likExportedMonitor('snap', '1')
            #print(json.dumps(test, indent=3))
            #await configuremonitor_subcommand(update, context, mid, key, value, desc)
            await context.bot.send_message(chat_id=chat_id, text='Sorry, it\'s not possible to configure monitors, It\'s not something I can fix without Shinobi\'s dev help... \u26A0\ufe0f')
    elif tag=='configuremonitor':
        mid=inputdata[1]
        key=inputdata[2]
        value=inputdata[3]
        desc=inputdata[4]
        thisMonitor=monitor(shinobiBaseUrl, shinobiPort, shinobiApiKey, shinobiGroupKey, mid)
        await thisMonitor.configure(context, chat_id, query, key, value, desc)

@restricted
@send_action(constants.ChatAction.TYPING)
async def configuremonitor_subcommand(update: Update, context: ContextTypes.DEFAULT_TYPE, mid: None, key: None, value: None, desc: None):
    chat_id=update.effective_chat.id
    tag='configuremonitor'
    button=[[InlineKeyboardButton('OK', callback_data=tag+';'+mid+';'+key+';'+value+';'+desc)]]
    reply_markup = InlineKeyboardMarkup(button)
    await context.bot.send_message(chat_id=chat_id, text=f'Do you want set {desc} to {value}?', reply_markup=reply_markup)

async def queryUrl(chat_id, context, url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
        await context.bot.send_message(chat_id=chat_id, text='Error something went wrong, request error \u26A0\ufe0f')
        return False
    else:
        print(f'OK, request done \U0001F44D')
        return response.json()

if __name__ == '__main__':
    needed = {'Telegram':['api_key'],'Shinobi':['api_key','group_key','url','port']}
    result = ini_check.iniCheck(needed,config_file)
    frame = inspect.currentframe()
    command_functions = [obj for name, obj in frame.f_globals.items() if inspect.isfunction(obj) and name.endswith("_command")]
    for function in command_functions:
        command=function.__name__.split('_')[0]
        name=function.__name__
        code=inspect.getsource(function)
        pattern = r'desc\s*=\s*["\'](.*?)["\']'
        desc=re.search(pattern, code)
        if not desc:
            print(f'WARN: {function.__name__} function has no description...')
            break
        else:
            data={'func':function, 'name':name, 'command':command, 'desc':'/'+command+' - '+desc.group(1)}
            commands.append(data)
            if command_functions.index(function)<len(command_functions)-1:
                continue
        if result:
            global telegramApiKey
            global shinobiApiKey
            global shinobiBaseUrl
            global shinobiPort
            global shinobiGroupKey
            global telegramChatId
            telegramApiKey=ini_check.settings.get('Telegram').get('api_key')
            shinobiApiKey=ini_check.settings.get('Shinobi').get('api_key')
            shinobiBaseUrl=ini_check.settings.get('Shinobi').get('url')
            shinobiPort=ini_check.settings.get('Shinobi').get('port')
            shinobiGroupKey=ini_check.settings.get('Shinobi').get('group_key')
            telegramChatId=ini_check.settings.get('Telegram').get('chat_id')
            
            application = ApplicationBuilder().token(telegramApiKey).build()
            # CommandHandlers for commands are autogenerated parsing command functions
            callback_query_handler = CallbackQueryHandler(callback_handler)
            handlers=[callback_query_handler]
            for command in commands:
                handlers.append(CommandHandler(f'{command["command"]}', command["func"]))
            application.add_handlers(handlers)
            print('ShinogrammaBot Up and running')
            application.run_polling()

        else:
            print('INI file missed, please provide one.')

