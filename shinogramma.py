# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram,
# right now it is possible to activate statuses but I'm working on it....
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github 
# or donate me a coffee

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from functools import wraps
import ini_check
import logging
import requests
import inspect
import re
import json
import time

# Defining root variables
config_file = "config.ini"
settings = {}
commands = []
# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if not settings.get('Telegram').get('chat_id'):
            print('WARN: chat_id not defined, continuing...')
            return func(update, context, *args, **kwargs)
        user_id = update.effective_user.id
        if user_id not in settings['Telegram']['chat_id']:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)
    return wrapped

# Telegram/Bot commands definition:
@restricted 
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Below line is to remember how to set a context but unusefull IMHO, tag system work mutch better...
    # context.user_data["originating_function"] = inspect.currentframe().f_code.co_name
    desc='Start this bot'
    tag = 'start'
    keyboard=[]
    for command in commands:
        keyboard.append([InlineKeyboardButton('/'+command['command'], callback_data=None)])
    reply_markup = ReplyKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm Shinotify Bot, and I am ready!\nGlad to serve you \u263A", reply_markup=reply_markup)
    # Below line is to remember how to update/edit a sended message
    # await update.message.reply_text("Seleziona un comando:", reply_markup=reply_markup)

@restricted    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc='Where you are'
    tag = 'help'
    help_text = "Available commands are:\n"
    for command in commands:
        help_text += f'{command["desc"]}\n'
    await context.bot.send_message(chat_id=update.effective_chat.id,text=help_text)

@restricted
async def monitors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc='List all monitors'
    tag='monitors'
    url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitor/{settings['Shinobi']['group_key']}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
        return
    else:
        print(f'OK, done \U0001F44D')
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')
        response = response.json()
        monitors = []
        for i in response:
            monitors.append({'name':i['name'],'id':i['mid']})
        if monitors:
            buttons = []
            for monitor in monitors:
                buttons.append([InlineKeyboardButton(monitor['name'], callback_data=tag+';'+monitor['id'])])
            reply_markup = InlineKeyboardMarkup(buttons)
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Push one monitor:', reply_markup=reply_markup)
        else:
            print('No monitors found \u26A0\ufe0f')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='No monitors found \u26A0\ufe0f')

@restricted
async def monitors_subcommand(update: Update, context: ContextTypes.DEFAULT_TYPE, mid):
    tag='submonitors'
    choices=['snapshot', 'stream', 'videos', 'configure']
    buttons = []
    for choice in choices:
        buttons.append([InlineKeyboardButton(choice, callback_data=tag+';'+choice+';'+mid)])
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='What do you want from this monitor?', reply_markup=reply_markup)

@restricted
async def states_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc='List all states'
    tag='states'
    url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitorStates/{settings['Shinobi']['group_key']}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
        return
    else:
        print(f'OK, done \U0001F44D')
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')
        response = response.json()
        states = []
        for i in response['presets']:
            states.append(i['name'])
        if states:
            buttons = []
            for state in states:
                buttons.append([InlineKeyboardButton(state, callback_data=tag+';'+state)])
            reply_markup = InlineKeyboardMarkup(buttons)
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Push one state to activate:', reply_markup=reply_markup)
        else:
            print('No states found \u26A0\ufe0f')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='No states found \u26A0\ufe0f')

@restricted 
async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    inputdata = query.data.split(';')
    tag = inputdata[0]
    selection = inputdata[1]
    if tag=='states':
        url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitorStates/{settings['Shinobi']['group_key']}/{selection}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
            return
        else:
            print(f'OK, {selection} done \U0001F44D')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')
    elif tag=='monitors':
        # Below line is to remember how to delete a message after tapped on
        # await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        await monitors_subcommand(update, context, selection)
    elif tag=='submonitors':
        if selection=='snapshot':
            url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitor/{settings['Shinobi']['group_key']}/{inputdata[2]}"
            response = requests.get(url)
            if response.status_code != 200:
                print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
                return
            else:
                print(f'OK, done \U0001F44D')
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, server touched... \U0001F44D')
                response = response.json()
                data = json.loads(response[0]['details'])
                snap = int()
                if data.get('snap')=='1':
                    await query.answer("Cooking your snapshot...\U0001F373")
                    baseurl = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/jpeg/{settings['Shinobi']['group_key']}/{inputdata[2]}/s.jpg"
                    avoidcacheurl = str(int(time.time()))
                    url = baseurl+'?'+avoidcacheurl
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=url)
                else:
                    key = 'snap'
                    value = '1'
                    desc = 'Jpeg API for snapshots'
                    await query.answer("Jpeg API not active")
                    await configuremonitor_subcommand(update, context, inputdata[2], key, value, desc)
        elif selection=='stream':
            url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitor/{settings['Shinobi']['group_key']}/{inputdata[2]}"
            response = requests.get(url)
            if response.status_code != 200:
                print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
                return
            else:
                print(f'OK, done \U0001F44D')
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')
                response = response.json()
                data = json.loads(response[0]['details'])
                #snap = int(data.get('snap'))
                #if snap:
                #    await query.answer("Cooking your snapshot...\U0001F373")
                url = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/hls/{settings['Shinobi']['group_key']}/{inputdata[2]}/s.m3u8"
                print(url)
                await context.bot.send_video(chat_id=update.effective_chat.id, video=url, supports_streaming=True)
        elif selection=='videos':
            pass
        elif selection=='configure':
            pass
    elif tag=='configuremonitor':
        endpoint = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/configureMonitor/{settings['Shinobi']['group_key']}/{selection}"
        queryurl = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitor/{settings['Shinobi']['group_key']}/{selection}"
        print(queryurl)
        response = requests.get(queryurl)
        if response.status_code != 200:
            print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
            return
        else:
            print(f'OK, server touched... \U0001F44D')
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')
            response = response.json()
            #print(response)
            data = response[0]
            #print(json.dumps(data, indent=4))
            for element in response:
                if 'details' in element:
                    print('elemento trovato')
                    for key in element:
                        print(key, ':', element.get(key), type(element.get(key)))
                    
            if 'details' in data:
                details = json.loads(data['details'])
                key = inputdata[2]
                value = inputdata[3]
                details[key] = value
                data['details'] = json.dumps(details)
                response = requests.post(endpoint, data=str(data))
                if response.status_code != 200:
                    print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
                    await context.bot.send_message(chat_id=update.effective_chat.id, text='Error something went wrong, request error \u26A0\ufe0f')
                    return
                else:
                    print(f'OK, done \U0001F44D')
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'OK, done \U0001F44D')

def disAssebleMonitor():
    pass

def reAssebleMonitor():
    pass

@restricted
async def configuremonitor_subcommand(update: Update, context: ContextTypes.DEFAULT_TYPE, mid: None, key: None, value: None, desc: None):
    tag='configuremonitor'
    button=[[InlineKeyboardButton('OK', callback_data=tag+';'+mid+';'+key+';'+value+';'+desc)]]
    reply_markup = InlineKeyboardMarkup(button)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Do you want set {desc} to {value}?', reply_markup=reply_markup)

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
            settings = ini_check.settings
            application = ApplicationBuilder().token(settings['Telegram']['api_key']).build()
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

