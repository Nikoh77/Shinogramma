# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram.
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github
# or donate me a coffee

from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    InlineQueryResultVideo,
    constants,
    error,
)
from functools import wraps
import colorlog
import logging
import inspect
import re
from httpQueryUrl import queryUrl
from settings import IniSettings, Url
from monitor import Monitor
from pathlib import Path


# Defining root constants
"""
Below constant is required to set the log level only for some modules directly involved by
this application and avoid seeing the debug of all modules in the tree.
If you want to see the logs of other modules at the "REQ_SHINOGRAMMA_LOGLEVEL" level add
them to the list below
"""
MODULES_LOGGERS: list[str] = ["__main__", "httpQueryUrl", "settings", "monitor"]
CONFIG_FILE: Path = Path("config.ini")
TELEGRAM_CHAT_ID: list[int] = []
"""
Below required data for running this software, are defined as a constants.
Starting from these constants the variable `neededSettings` is created; she is used by
the `settings` class. 
It is important to follow the syntax:

REQ_ + INIsection + INIoption.

For example, if you want to have following configuration in the configuration file:

[BANANAS]
number_of = 10
color = green

We need to add the following constants below:

REQ_BANANAS_NUMBER_OF: dict = {"data": None, "typeOf": int}
REQ_BANANAS_COLOR: dict = {"data": None, "typeOf": str}

When starting, settings will ask the user to enter the number and color of bananas...

It is important to note that the value of 'data' key of all these constants is updated 
at runtime from None to values read from the configuration file here, by buildSettings function.

An attempt will be made to convert the data to the type indicated in the constant, so 
the string '10' entered by the user will become an integer.

Is important to know that if initial data is not None this will be the default value for this costant
and settings will not ask the user to enter this data, but if you also provide same option on the config file
the default data will be overwritten.
"""

REQ_TELEGRAM_API_KEY: dict = {"data": None, "typeOf": str}
REQ_SHINOBI_API_KEY: dict = {"data": None, "typeOf": str}
REQ_SHINOBI_GROUP_KEY: dict = {"data": None, "typeOf": str}
REQ_SHINOBI_BASE_URL: dict = {"data": None, "typeOf": Url}
REQ_SHINOBI_PORT: dict = {"data": 8080, "typeOf": int}
REQ_SHINOGRAMMA_LOGLEVEL: dict = {"data": "info", "typeOf": str}

# Defining root variables
commands = []
confParam, confParamVal = range(2)
neededSettings: dict[str, list] = {}
# Building neededSettings
for i in list(globals().keys()):
    if i.startswith("REQ_"):
        section = i.split(sep="_")[1]
        option = i.replace("REQ_" + section + "_", "").lower()
        if section not in neededSettings.keys():
            neededSettings.update({section: []})
        neededSettings[section].append(
            {
                "name": option,
                "data": globals()[i].get("data"),
                "typeOf": globals()[i].get("typeOf"),
            }
        )

# Start logging
logger = colorlog.getLogger(name=__name__)
colorlog.basicConfig(
    format="%(log_color)s[%(levelname)-8s] %(blue)s %(asctime)s %(name)s %(reset)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "bold_red",
        "CRITICAL": "bold_red,bg_white",
    },
    secondary_log_colors={},
    style="%",
)


def setLogLevel() -> None:
    currentLevel = logging.getLevelName(level=logger.getEffectiveLevel())
    if REQ_SHINOGRAMMA_LOGLEVEL["data"].upper() != currentLevel:
        try:
            getattr(
                logger, logging.getLevelName(level=logger.getEffectiveLevel()).lower()
            )(
                f"switching from log level {logging.getLevelName(level=logger.getEffectiveLevel())}"
            )
            logger.setLevel(level=REQ_SHINOGRAMMA_LOGLEVEL["data"].upper())
            currentLevel = logging.getLevelName(
                level=logger.getEffectiveLevel()
            ).lower()
            getattr(logger, currentLevel)(
                msg=f"to level {logging.getLevelName(level=logger.getEffectiveLevel())}"
            )
            for module in MODULES_LOGGERS:
                logging.getLogger(name=module).setLevel(
                    level=REQ_SHINOGRAMMA_LOGLEVEL["data"].upper()
                )
        except Exception as e:
            logger.error(msg=f"Error setting LogLevel: {e}")


setLogLevel()
settings = IniSettings(neededSettings=neededSettings, configFile=CONFIG_FILE)


def buildSettings(data) -> bool:
    if data:
        for i, v in data:
            varName = "REQ_" + i.upper()
            if varName in globals().keys():
                globals()[varName].update({"data": v})
            else:
                varName = i.upper()
                if (
                    varName == "TELEGRAM_CHAT_ID"
                ):  # If chat_id (comma separated) are defined
                    for i in v.split(sep=","):
                        globals()[varName].append(int(i.strip()))
                else:
                    globals()[varName] = v
        return True
    return False


# Start decorators section
def restricted(func):
    """Restrict chat only with id(es) defined in config.ini"""

    @wraps(wrapped=func)
    def wrapped(update, context, *args, **kwargs):
        if len(TELEGRAM_CHAT_ID) == 0:
            return func(update, context, *args, **kwargs)
        chat_id = update.effective_user.id
        if chat_id not in TELEGRAM_CHAT_ID:
            print("Unauthorized, access denied for {}.".format(chat_id))
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(wrapped=func)
        async def command_func(update, context, *args, **kwargs):
            chat_id = update.effective_user.id
            await context.bot.send_chat_action(chat_id=chat_id, action=action)
            return await func(update, context, *args, **kwargs)

        return command_func

    return decorator


# End decorators section


# Start Telegram/Bot commands definition (ALL must be decorated with restricted):
@restricted
@send_action(action=constants.ChatAction.TYPING)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        desc = "Start this bot"
        tag = "start"
        keyboard = []
        for command in commands:
            keyboard.append(
                [InlineKeyboardButton("/" + command["command"], callback_data=None)]
            )
        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="choose the command",
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text="I'm Shinogramma Bot, and I am ready!\nGlad to serve you \u263A",
            reply_markup=reply_markup,
        )


@restricted
@send_action(action=constants.ChatAction.TYPING)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        logger.info(msg=f"test logger with chat_id {chat_id}")
        desc = "Where you are"
        tag = "help"
        help_text = "Available commands are:\n"
        keyboard = []
        for command in commands:
            help_text += f'{command["desc"]}\n'
            keyboard.append(
                [InlineKeyboardButton("/" + command["command"], callback_data=None)]
            )
        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="choose the command",
        )
        await context.bot.send_message(
            chat_id=chat_id, text=help_text, reply_markup=reply_markup
        )


@restricted
@send_action(action=constants.ChatAction.TYPING)
async def states_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        desc = "List all states"
        tag = "states"
        url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/monitorStates/{REQ_SHINOBI_GROUP_KEY['data']}"
        data = await queryUrl(url=url)
        if data:
            data = data.json()
            states = []
            for i in data["presets"]:
                states.append(i["name"])
            if states:
                buttons = []
                for state in states:
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=state, callback_data=tag + ";;" + state
                            )
                        ]
                    )
                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Select one state to activate:",
                    reply_markup=reply_markup,
                )
            else:
                print("No states found \u26A0\ufe0f")
                await context.bot.send_message(
                    chat_id=chat_id, text="No states found \u26A0\ufe0f"
                )


@restricted
@send_action(action=constants.ChatAction.TYPING)
async def monitors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        desc = "List all monitors"
        tag = "monitors"
        url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/monitor/{REQ_SHINOBI_GROUP_KEY['data']}"
        data = await queryUrl(url=url)
        if data:
            data = data.json()
            monitors = []
            for i in data:
                monitors.append({"name": i["name"], "id": i["mid"]})
            if monitors:
                buttons = []
                for monitor in monitors:
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=monitor["name"],
                                callback_data=tag
                                + ";;"
                                + monitor["id"]
                                + ";;"
                                + monitor["name"],
                            )
                        ]
                    )
                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Select one monitor:",
                    reply_markup=reply_markup,
                )
            else:
                print("No monitors found \u26A0\ufe0f")
                await context.bot.send_message(
                    chat_id=chat_id, text="No monitors found \u26A0\ufe0f"
                )


@restricted
@send_action(action=constants.ChatAction.TYPING)
async def BOTsettings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        desc = "Edit shinogramma settings"
        tag = "settings"


# End Telegram/Bot commands definition:


@send_action(action=constants.ChatAction.TYPING)
async def monitors_subcommand(
    update: Update, context: ContextTypes.DEFAULT_TYPE, mid, name
):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        tag = "submonitors"
        choices = ["snapshot", "stream", "videos", "map", "configure"]
        buttons = []
        for choice in choices:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=choice, callback_data=tag + ";;" + choice + ";;" + mid
                    )
                ]
            )
        reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"<b>{name}</b>\nWhat do you want from this monitor?",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


@send_action(action=constants.ChatAction.TYPING)
async def callback_handler(update: Update, context: CallbackContext):
    if update.effective_chat:
        chat_id = update.effective_chat.id
        query = update.callback_query
        inputdata = query.data.split(";;")
        tag = inputdata[0]
        if tag == "states":
            url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/monitorStates/{REQ_SHINOBI_GROUP_KEY['data']}/{inputdata[1]}"
            data = await queryUrl(url=url)
            if data:
                await query.answer(text="OK, done \U0001F44D")
        elif tag == "monitors":
            await monitors_subcommand(
                update=update, context=context, mid=inputdata[1], name=inputdata[2]
            )
        elif tag == "submonitors":
            mid = inputdata[2]
            thisMonitor = Monitor(
                update=update,
                context=context,
                chatId=chat_id,
                baseUrl=REQ_SHINOBI_BASE_URL["data"],
                port=REQ_SHINOBI_PORT["data"],
                apiKey=REQ_SHINOBI_API_KEY["data"],
                groupKey=REQ_SHINOBI_GROUP_KEY["data"],
                mid=mid,
            )
            if inputdata[1] == "snapshot":
                if not await thisMonitor.getSnapshot():
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Error something went wrong, requesting snapshot \u26A0\ufe0f",
                    )
                    key = "snap"
                    value = "1"
                    desc = "Jpeg API for snapshots"
                    # to do: start config procedure to enable snap...
            elif inputdata[1] == "stream":
                if not await thisMonitor.getStream():
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Error something went wrong, requesting stream \u26A0\ufe0f",
                    )
            elif inputdata[1] == "videos":
                if not await thisMonitor.getVideo():
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Error something went wrong, requesting videos \u26A0\ufe0f",
                    )
            elif inputdata[1] == "configure":
                context.user_data["from"] = inputdata[1]
                context.user_data["monitor"] = thisMonitor
                await update.effective_message.reply_text(
                    text="Which parameter do you want to change?"
                )
            elif inputdata[1] == "map":
                if not await thisMonitor.getmap():
                    pass
        elif tag == "video":
            mid = inputdata[2]
            thisMonitor = Monitor(
                update=update,
                context=context,
                chatId=chat_id,
                baseUrl=REQ_SHINOBI_BASE_URL["data"],
                port=REQ_SHINOBI_PORT["data"],
                apiKey=REQ_SHINOBI_API_KEY["data"],
                groupKey=REQ_SHINOBI_GROUP_KEY["data"],
                mid=mid,
            )
            if len(inputdata) == 3:
                index = int(inputdata[1])
                await thisMonitor.getVideo(index=index)
            if len(inputdata) == 4:
                index = int(inputdata[1])
                await thisMonitor.getVideo(index=index, operation=inputdata[3])


async def handleTextConfigure(update: Update, context: CallbackContext):
    user_text = update.message.text
    logger.info(msg=f"User wrote: {user_text}")
    if "from" in context.user_data:
        if context.user_data["from"] == "configure":
            context.user_data["from"] = "handle"
            context.user_data["key"] = user_text
            await update.effective_message.reply_text(
                text="Which value do you want to assign?"
            )
        elif context.user_data["from"] == "handle":
            context.user_data.pop("from")
            thisMonitor = context.user_data["monitor"]
            context.user_data.pop("monitor")
            key = context.user_data["key"]
            context.user_data.pop("key")
            value = user_text
            chat_id = update.effective_chat.id
            await thisMonitor.configure(key, value)


if __name__ == "__main__":
    if not buildSettings(data=settings.iniRead()):
        logger.info(
            msg="Error building and or retrieving settings from config file, exiting..."
        )
        raise SystemExit
    setLogLevel()
    if not len(TELEGRAM_CHAT_ID) > 0:
        logger.warning(
            msg="Chat_id not defined, this could be very dangerous, continuing..."
        )
    frame = inspect.currentframe()
    command_functions = [
        obj
        for name, obj in frame.f_globals.items()
        if inspect.isfunction(object=obj) and name.endswith("_command")
    ]
    for function in command_functions:
        command = function.__name__.split(sep="_")[0]
        name = function.__name__
        code = inspect.getsource(object=function)
        pattern = r'desc\s*=\s*["\'](.*?)["\']'
        desc = re.search(pattern=pattern, string=code)
        if not desc:
            logger.critical(
                msg=f"WARN: {function.__name__} function has no description..."
            )
            break
        else:
            data = {
                "func": function,
                "name": name,
                "command": command,
                "desc": "/" + command + " - " + desc.group(1),
            }
            commands.append(data)
            if command_functions.index(function) < len(command_functions) - 1:
                continue
            application = (
                ApplicationBuilder().token(token=REQ_TELEGRAM_API_KEY["data"]).build()
            )
            callback_query_handler = CallbackQueryHandler(callback=callback_handler)
            text_handler = MessageHandler(
                filters=filters.TEXT & ~filters.COMMAND,
                callback=handleTextConfigure,
            )
            handlers = [callback_query_handler, text_handler]
            # Below commandHandlers for commands are autogenerated parsing command functions
            for command in commands:
                handlers.append(
                    CommandHandler(
                        command=f'{command["command"]}', callback=command["func"]
                    )
                )
            application.add_handlers(handlers=handlers)
            print("ShinogrammaBot Up and running")
            application.run_polling(drop_pending_updates=True)
