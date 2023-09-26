# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram.
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github 
# or donate me a coffee

from telegram.ext import (ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackContext, CallbackQueryHandler, ConversationHandler, filters)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InlineQueryResultVideo, constants
from functools import wraps
from monitor import monitor
from httpQueryUrl import queryUrl
import ini_check
import logging
import inspect
import re

# Defining root variables
config_file = "config.ini"
commands = []
confParam, confParamVal = range(2)

# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Start decorators section
def restricted(func):
    """Restrict chat only with id in config.ini."""
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if not telegramChatId:
            return func(update, context, *args, **kwargs)
        chat_id = update.effective_user.id
        if chat_id not in telegramChatId:
            print("Unauthorized, access denied for {}.".format(chat_id))
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

# Start Telegram/Bot commands definition (ALL must be decorated with restricted):
@restricted
@send_action(constants.ChatAction.TYPING)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='Start this bot'
    tag = 'start'
    keyboard=[]
    for command in commands:
        keyboard.append([InlineKeyboardButton('/'+command['command'], callback_data=None)])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="choose the command")
    await context.bot.send_message(chat_id=chat_id, text="I'm Shinogramma Bot, and I am ready!\nGlad to serve you \u263A", reply_markup=reply_markup)

@restricted
@send_action(constants.ChatAction.TYPING)    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    logger.info(f'test logger with chat_id {chat_id}')
    desc='Where you are'
    tag = 'help'
    help_text = "Available commands are:\n"
    keyboard=[]
    for command in commands:
        help_text += f'{command["desc"]}\n'
        keyboard.append([InlineKeyboardButton('/'+command['command'], callback_data=None)])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="choose the command")
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
# End Telegram/Bot commands definition:

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

@send_action(constants.ChatAction.TYPING) 
async def callback_handler(update: Update, context: CallbackContext):
    chat_id=update.effective_chat.id
    query = update.callback_query
    inputdata = query.data.split(';')
    tag=inputdata[0]
    if tag=='states':
        url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitorStates/{shinobiGroupKey}/{inputdata[1]}"
        data= await queryUrl(chat_id, context, url)
        if data:
            await query.answer('OK, done \U0001F44D')
    elif tag=='monitors':
        await monitors_subcommand(update, context, inputdata[1])
    elif tag=='submonitors':
        mid=inputdata[2]
        thisMonitor=monitor(context, chat_id, shinobiBaseUrl, shinobiPort, shinobiApiKey, shinobiGroupKey, mid)
        #data=await queryUrl(chat_id, context, thisMonitor.url)
        if inputdata[1]=='snapshot':
            if not await thisMonitor.getsnapshot(context, chat_id, query):
                key = 'snap'
                value = '1'
                desc = 'Jpeg API for snapshots'
                # start config procedure to enable snap...
        elif inputdata[1]=='stream':
            stream=await thisMonitor.getstream(context, chat_id)
            if stream!=None:
                buttons=[[InlineKeyboardButton('link', url=stream)]]
                reply_markup = InlineKeyboardMarkup(buttons)
                await update.effective_message.reply_text("With IOS use the link below, otherwise above file will be fine", reply_markup=reply_markup)
        elif inputdata[1]=='videos':
            await context.bot.send_message(chat_id=chat_id, text='Sorry, it\'s not yet possible to see videos but I am working on... \u26A0\ufe0f')
        elif inputdata[1]=='configure':
            context.user_data['from']=inputdata[1]
            context.user_data['monitor']=thisMonitor
            await update.effective_message.reply_text("Which parameter do you want to change?")

async def handleTextConfigure(update: Update, context: CallbackContext):
    user_text = update.message.text
    logger.info(f"User wrote: {user_text}")
    if 'from' in context.user_data:
        if context.user_data['from']=='configure':
            context.user_data['from']='handle'
            context.user_data['key']=user_text
            await update.effective_message.reply_text("Which value do you want to assign?")
        elif context.user_data['from']=='handle':
            context.user_data.pop('from')
            thisMonitor=context.user_data['monitor']
            context.user_data.pop('monitor')
            key=context.user_data['key']
            context.user_data.pop('key')
            value=user_text
            chat_id=update.effective_chat.id
            await thisMonitor.configure(context, chat_id, key, value)

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
            
            callback_query_handler = CallbackQueryHandler(callback_handler)
            text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handleTextConfigure)
            handlers=[callback_query_handler, text_handler]
            # Below commandHandlers for commands are autogenerated parsing command functions
            for command in commands:
                handlers.append(CommandHandler(f'{command["command"]}', command["func"]))
            application.add_handlers(handlers)
            print('ShinogrammaBot Up and running')
            application.run_polling(drop_pending_updates=True)
        else:
            print('INI file missed, please provide one.')

