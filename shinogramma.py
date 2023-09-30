# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram.
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github 
# or donate me a coffee

from telegram.ext import (ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackContext, CallbackQueryHandler, ConversationHandler, filters)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InlineQueryResultVideo, constants
from functools import wraps
#from monitor import monitor
from httpQueryUrl import queryUrl
from datetime import datetime
import ini_check
import logging
import inspect
import re
import json
import time
import io
import m3u8
import humanize

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
async def states_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='List all states'
    tag='states'
    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitorStates/{shinobiGroupKey}"
    data=await queryUrl(chat_id, context, url)
    if data:
        data=data.json()
        states = []
        for i in data['presets']:
            states.append(i['name'])
        if states:
            buttons = []
            for state in states:
                buttons.append([InlineKeyboardButton(state, callback_data=tag+';;'+state)])
            reply_markup = InlineKeyboardMarkup(buttons)
            await context.bot.send_message(chat_id=chat_id, text='Select one state to activate:', reply_markup=reply_markup)
        else:
            print('No states found \u26A0\ufe0f')
            await context.bot.send_message(chat_id=chat_id, text='No states found \u26A0\ufe0f')

@restricted
@send_action(constants.ChatAction.TYPING)
async def monitors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='List all monitors'
    tag='monitors'
    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitor/{shinobiGroupKey}"
    data= await queryUrl(chat_id, context, url)
    if data:
        data=data.json()
        monitors = []
        for i in data:
            monitors.append({'name':i['name'],'id':i['mid']})
        if monitors:
            buttons = []
            for monitor in monitors:
                buttons.append([InlineKeyboardButton(monitor['name'], callback_data=tag+';;'+monitor['id']+';;'+monitor['name'])])
            reply_markup = InlineKeyboardMarkup(buttons)
            await context.bot.send_message(chat_id=chat_id, text='Select one monitor:', reply_markup=reply_markup)
        else:
            print('No monitors found \u26A0\ufe0f')
            await context.bot.send_message(chat_id=chat_id, text='No monitors found \u26A0\ufe0f')

@restricted
@send_action(constants.ChatAction.TYPING)    
async def BOTsettings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id=update.effective_chat.id
    desc='Edit shinogramma settings'
    tag='settings'
# End Telegram/Bot commands definition:

@send_action(constants.ChatAction.TYPING) 
async def monitors_subcommand(update: Update, context: ContextTypes.DEFAULT_TYPE, mid, name):
    chat_id=update.effective_chat.id
    tag='submonitors'
    choices=['snapshot', 'stream', 'videos', 'map', 'configure']
    buttons = []
    for choice in choices:
        buttons.append([InlineKeyboardButton(choice, callback_data=tag+';;'+choice+';;'+mid)])
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=chat_id, text=f'<b>{name}</b>\nWhat do you want from this monitor?', reply_markup=reply_markup, parse_mode='HTML')

@send_action(constants.ChatAction.TYPING) 
async def callback_handler(update: Update, context: CallbackContext):
    chat_id=update.effective_chat.id
    query=update.callback_query
    inputdata=query.data.split(';;')
    tag=inputdata[0]
    if tag=='states':
        url=f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitorStates/{shinobiGroupKey}/{inputdata[1]}"
        data=await queryUrl(chat_id, context, url)
        if data:
            await query.answer('OK, done \U0001F44D')
    elif tag=='monitors':
        await monitors_subcommand(update, context, inputdata[1], inputdata[2])
    elif tag=='submonitors':
        mid=inputdata[2]
        thisMonitor=monitor(update, context, chat_id, mid)
        if inputdata[1]=='snapshot':
            if not await thisMonitor.getsnapshot():
                key = 'snap'
                value = '1'
                desc = 'Jpeg API for snapshots'
                # to do: start config procedure to enable snap...
        elif inputdata[1]=='stream':
            stream=await thisMonitor.getstream()
        elif inputdata[1]=='videos':
            videos=await thisMonitor.getvideo()
        elif inputdata[1]=='configure':
            context.user_data['from']=inputdata[1]
            context.user_data['monitor']=thisMonitor
            await update.effective_message.reply_text("Which parameter do you want to change?")
        elif inputdata[1]=='map':
            geolocation=await thisMonitor.getmap()
    if tag=='video':
        mid=inputdata[2]
        thisMonitor=monitor(update, context, chat_id, mid)
        if len(inputdata)==3:
            videolist=await thisMonitor.getvideo(inputdata[1])
        if len(inputdata)==4:
            videoOp=await thisMonitor.getvideo(inputdata[1], inputdata[3])

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
            await thisMonitor.configure(key, value)

class monitor:
    def __init__(self, update, context, chat_id, mid):
        self.update=update
        self.context=context
        self.chat_id=chat_id
        self.mid=mid
        self.url=f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/monitor/{shinobiGroupKey}/{mid}"
        self.query=update.callback_query

    async def getsnapshot(self):
        data=await queryUrl(self.context, self.chat_id, self.url)
        if data:
            data=data.json()
            if json.loads(data[0]['details'])['snap']=='1':
                await self.query.answer("Cooking your snapshot...\U0001F373")
                baseurl = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/jpeg/{shinobiGroupKey}/{self.mid}/s.jpg"
                avoidcacheurl = str(int(time.time()))
                url = baseurl+'?'+avoidcacheurl
                await self.context.bot.send_photo(chat_id=self.chat_id, photo=url)
                return True
            else:
                await self.query.answer(text="Jpeg API not active on this monitor \u26A0\ufe0f", show_alert=True)
                logger.info('Jpeg API not active on this monitor')
                return False

    async def getstream(self):
        data=await queryUrl(self.context, self.chat_id, self.url)
        if data:
            data=data.json()
            streamTypes=['hls','mjpeg','flv','mp4']
            streamType=json.loads(data[0]['details'])['stream_type']
            if streamType in streamTypes:
                if streamType=='hls':
                    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/hls/{shinobiGroupKey}/{self.mid}/s.m3u8"
                elif streamType=='mjpeg':
                    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/mjpeg/{shinobiGroupKey}/{self.mid}"
                elif streamType=='flv':
                    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/flv/{shinobiGroupKey}/{self.mid}/s.flv"
                elif streamType=='mp4':
                    url = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/mp4/{shinobiGroupKey}/{self.mid}/s.mp4"
                playlist=m3u8.M3U8()
                playlist.add_playlist(url)
                vfile=io.StringIO(playlist.dumps())
                thumbnail_file = open('images/shinthumbnail.jpeg', 'rb')
                avoidcacheurl = str(int(time.time()))
                await self.context.bot.send_document(chat_id=self.chat_id, document=vfile, filename=f'stream'+avoidcacheurl+'.m3u8', protect_content=False, thumbnail=thumbnail_file)
                vfile.close()
                buttons=[[InlineKeyboardButton('link', url=url)]]
                reply_markup = InlineKeyboardMarkup(buttons)
                await self.update.effective_message.reply_text("With IOS use the link below, otherwise above file will be fine", reply_markup=reply_markup)
            else:
                logger.info('If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg...')
                await self.context.bot.send_message(chat_id=self.chat_id, text="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg... \u26A0\ufe0f")
            
    async def getvideo(self, index=None, operation=None):
        tag='video'
        url=f'{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/videos/{shinobiGroupKey}/{self.mid}'
        method='get'
        data=None
        debug=False
        videoList=await queryUrl(self.context, self.chat_id, url, method, data, debug)
        if videoList:
            if index==None:
                videoList=videoList.json().get('videos')
                buttons=[]
                for index,video in enumerate(videoList):
                    start_time=datetime.fromisoformat(video.get('time'))
                    start=humanize.naturaltime(start_time)
                    if video['status']==1:
                        start=start.upper()
                    CallBack=f'{tag};;{index};;{self.mid}'
                    buttons.append([InlineKeyboardButton(start, callback_data=CallBack)])
                reply_markup = InlineKeyboardMarkup(buttons)
                await self.context.bot.send_message(chat_id=self.chat_id, text="Select one video <b>(in uppercase are new)</b>.", reply_markup=reply_markup, parse_mode='HTML')
            elif operation==None and index!=None:
                index=int(index)
                number=len(videoList.json().get('videos'))
                video=videoList.json().get('videos')[index]
                start_time=datetime.fromisoformat(video.get('time'))
                end_time=datetime.fromisoformat(video.get('end'))
                duration=humanize.naturaldelta(end_time-start_time)
                time=start_time.strftime("%Y-%m-%d %H:%M:%S")
                size=humanize.naturalsize(video.get('size'))
                fileName=video.get('filename')
                videoUrl=url+'/'+fileName
                setRead=f'{videoUrl}/status/2'
                buttons=[
                    [
                    InlineKeyboardButton('set unread', callback_data=f'{tag};;{index};;{self.mid};;unread'),
                    InlineKeyboardButton('delete', callback_data=f'{tag};;{index};;{self.mid};;delete')
                    ]
                ]
                if index>0:
                    buttons[0].insert(0, InlineKeyboardButton('prev', callback_data=f'{tag};;{index-1};;{self.mid}'))
                if index<number-1:
                    buttons[0].append(InlineKeyboardButton('next', callback_data=f'{tag};;{index+1};;{self.mid}'))
                reply_markup = InlineKeyboardMarkup(buttons)
                if video['status']==1:
                    temp=await queryUrl(self.context, self.chat_id, setRead, method, data, debug)
                    if temp:
                        logger.info(f'Video {self.mid}->{fileName} set as read')
                        await self.query.answer("Video set as read.\U0001F373")
                await self.context.bot.send_video(chat_id=self.chat_id, video=videoUrl, supports_streaming=True, caption=f'<b>{index+1}/{number} - {time} - {duration} - {size}</b>', reply_markup=reply_markup, parse_mode='HTML')
            else:
                index=int(index)
                video=videoList.json().get('videos')[index]
                fileName=video.get('filename')
                videoUrl=url+'/'+fileName
                setUnread=f'{videoUrl}/status/1'
                delete=f'{videoUrl}/delete'
                if operation=='unread':
                    url=setUnread
                    caption='set as unread'
                elif operation=='delete':
                    url=delete
                    caption='has been deleted'
                temp=await queryUrl(self.context, self.chat_id, url, method, data, debug)
                if temp:
                    logger.info(f'Video {self.mid}->{fileName} {caption}')
                    await self.query.answer(f'Video {caption}.\U0001F373')
    async def getmap(self):
        data=await queryUrl(self.context, self.chat_id, self.url)
        if data:
            data=json.loads(data.json()[0]['details']).get('geolocation').split(',')
            latitude=data[0]
            longitude=data[1]
            if latitude=='49.2578298' and longitude=='-123.2634732':
                await self.query.answer(text="No map data for this monitor...\u26A0\ufe0f", show_alert=True)

            print(type(data), data)
        
    async def configure(self, key, value, desc=None):
        data=await queryUrl(self.context, self.chat_id, self.url)
        if data:
            data=data.json()[0]
            details=json.loads(data['details'])
            if key in details.keys():
                details[key]=value
                data['details']=details
                endpoint = f"{shinobiBaseUrl}:{shinobiPort}/{shinobiApiKey}/configureMonitor/{shinobiGroupKey}/{self.mid}"
                method='post'
                debug=True
                await queryUrl(self.chat_id, self.context, endpoint, method, data, debug)
            else:
                logger.info('unknown parameter')
                await self.context.bot.send_message(chat_id=self.chat_id, text="Unknown parameter... \u26A0\ufe0f")
                return False

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
            logger.critical(f'WARN: {function.__name__} function has no description...')
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

