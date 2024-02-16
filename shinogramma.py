# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram.
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github
# or donate me a coffee

import asyncio
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters,
    PicklePersistence,
    PersistenceInput,
)
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    constants,
)
from functools import wraps
import colorlog
import logging
import inspect
from typing import Callable, Any
from httpQueryUrl import queryUrl
from settings import IniSettings, Url
from monitor import Monitor
from pathlib import Path
from video import Video


"""
Below constant is required to set the log level only for some modules directly involved by
this application and avoid seeing the debug of all modules in the tree.
Logs follow the settings given by their developers, if you want to raise or lower
the log level add the module to the list below
"""
MODULES_LOGGERS: list[str] = [
    "__main__",
    "httpQueryUrl",
    "settings",
    "monitor",
    "notify"
]
CONFIG_FILE: Path = Path("config.ini")
TELEGRAM_CHAT_ID: list[int] = []
APPLICATION: Application | None = None
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
REQ_SHINOGRAMMA_PERSISTENCE: dict = {"data": False, "typeOf": bool}
REQ_SHINOGRAMMA_APISERVER: dict = {"data": False, "typeOf": bool}

# Defining root variables
commands: list = []
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
    # level=logging.WARNING,
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
    # async def wrapped(update, context, *args, **kwargs):
    async def wrapped(update, context, *args, **kwargs):
        if update is not None and context is not None:
            chat_id = update.effective_user.id
            if len(TELEGRAM_CHAT_ID) > 0:
                if chat_id not in TELEGRAM_CHAT_ID:
                    logger.warning(msg=f"Unauthorized, access denied for {chat_id}.")
                    return
        else:
            chat_id = 11111
        return await func(update, context, chat_id, *args, **kwargs)
    
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


# Start Telegram/Bot commands definition (ALL must be decorated with restricted for security reasons):
@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None | str:
    if update is None and context is None and chat_id == 11111:
        desc = "Start this bot"
        return desc
    else:
        if update.effective_chat:
            tag = "start"
            keyboard: list[list[InlineKeyboardButton]] = []
            for command in commands:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="/" + command["command"], callback_data=None
                        )
                    ]
                )
            reply_markup = ReplyKeyboardMarkup(
                    keyboard=keyboard,  # type: ignore
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    input_field_placeholder="choose the command",
                )
            await context.bot.send_message(
                    chat_id=chat_id,
                    text="I'm Shinogramma Bot, and I am ready!\nGlad to serve you \u263A",
                    reply_markup=reply_markup,
                )
            # httpServer = threading.Thread(target=startHttpServer, args=("Hello", 42))
            # httpServer.start()
        return None


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None | str:
    if update is None and context is None and chat_id == 11111:
        desc = "Where you are"
        return desc
    else:
        if update.effective_chat:
            tag = "help"
            help_text = "Available commands are:\n"
            keyboard = []
            for command in commands:
                help_text += f'{command["desc"]}\n'
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="/" + command["command"], callback_data=None
                        )
                    ]
                )
            reply_markup = ReplyKeyboardMarkup(
                keyboard=keyboard,  # type: ignore
                resize_keyboard=True,
                one_time_keyboard=True,
                input_field_placeholder="choose the command",
            )
            await context.bot.send_message(
                chat_id=chat_id, text=help_text, reply_markup=reply_markup
            )
        return None


@restricted
async def states_command(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None | str:
    if update is None and context is None and chat_id == 11111:
        desc = "List all states"
        return desc
    else:
        if update.effective_chat:
            tag = inspect.currentframe().f_code.co_name  # type: ignore
            url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/monitorStates/{REQ_SHINOBI_GROUP_KEY['data']}"
            data = await queryUrl(url=url)
            if data:
                dataInJson = data.json()
                states = []
                for i in dataInJson["presets"]:
                    states.append(i["name"])
                if len(states) > 0:
                    buttons = []
                    for state in states:
                        buttons.append(
                            [
                                InlineKeyboardButton(
                                    text=state,
                                    callback_data={
                                        "tag": tag,
                                        "choice": state,
                                    },
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
                    logger.debug(msg="No states found \u26A0\ufe0f")
                    await context.bot.send_message(
                        chat_id=chat_id, text="No states found \u26A0\ufe0f"
                    )
        return None


@restricted
async def monitors_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None | str:
    if update is None and context is None and chat_id == 11111:
        desc = "List all monitors"
        return desc
    else:
        if update.effective_chat:
            tag = inspect.currentframe().f_code.co_name  # type: ignore
            url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/monitor/{REQ_SHINOBI_GROUP_KEY['data']}"
            data = await queryUrl(url=url)
            if data:
                dataInJson = data.json()
                monitors = []
                for i in dataInJson:
                    monitors.append({"name": i["name"], "id": i["mid"]})
                if len(monitors) > 0:
                    buttons = []
                    for monitor in monitors:
                        buttons.append(
                            [
                                InlineKeyboardButton(
                                    text=monitor["name"],
                                    callback_data={
                                        "tag": tag,
                                        "mid": monitor["id"],
                                        "choice": monitor["name"],
                                    },
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
                    logger.debug(msg="No monitors found \u26A0\ufe0f")
                    await context.bot.send_message(
                        chat_id=chat_id, text="No monitors found \u26A0\ufe0f"
                    )
        return None


@restricted
async def BOTsettings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None | str:
    if update is None and context is None and chat_id == 11111:
        desc = "Edit shinogramma settings"
        return desc
    else:
        if update.effective_chat:
            tag = inspect.currentframe().f_code.co_name  # type: ignore
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="Terminate",
                        callback_data={
                            "tag": tag,
                            "choice": "terminate",
                        },
                    ),
                    InlineKeyboardButton(
                        text="Reboot",
                        callback_data={
                            "tag": tag,
                            "choice": "reboot",
                        },
                    ),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await context.bot.send_message(
                chat_id=chat_id, text="kjjhfoksj", reply_markup=reply_markup
            )
        return None


# End Telegram/Bot commands definition:


@send_action(action=constants.ChatAction.TYPING)
async def monitors_subcommand(
    update: Update, context: ContextTypes.DEFAULT_TYPE, mid, name
) -> None:
    if update.effective_chat:
        chat_id = update.effective_chat.id
        tag = inspect.currentframe().f_code.co_name  # type: ignore
        choices = ["snapshot", "stream", "videos", "map", "configure"]
        buttons = []
        for choice in choices:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=choice,
                        callback_data={
                            "tag": tag,
                            "choice": choice,
                            "mid": mid,
                        },
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
async def callback_handler(update: Update, context: CallbackContext) -> None:
    if update.effective_chat:
        chat_id = update.effective_chat.id
        query = update.callback_query
        if query is not None and query.data is not None:
            if isinstance(query.data, dict):
                callbackFullData: dict = query.data
                logger.debug(msg=f"Callback received: {callbackFullData}")
                tag = callbackFullData.get("tag")
                mid = callbackFullData.get("mid", None)
                choice = callbackFullData.get("choice", None)
                operation = callbackFullData.get("operation", None)
                if tag == "states_command":
                    url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/monitorStates/{REQ_SHINOBI_GROUP_KEY['data']}/{choice}"
                    data = await queryUrl(url=url)
                    if data:
                        await query.answer(text="OK, done \U0001F44D")
                elif tag == "monitors_command":
                    await monitors_subcommand(
                        update=update,
                        context=context,
                        mid=mid,
                        name=choice,
                    )
                elif tag == "monitors_subcommand":
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
                    if choice == "snapshot":
                        if not await thisMonitor.getSnapshot():
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="Error something went wrong, requesting snapshot \u26A0\ufe0f",
                            )
                            key = "snap"
                            value = "1"
                            desc = "Jpeg API for snapshots"
                            # to do: start config procedure to enable snap...
                    elif choice == "stream":
                        if not await thisMonitor.getStream():
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="Error something went wrong, requesting stream \u26A0\ufe0f",
                            )

                    elif choice == "configure":
                        if context.user_data is not None:
                            context.user_data["from"] = choice
                            context.user_data["monitor"] = thisMonitor
                            if update.effective_message is not None:
                                await update.effective_message.reply_text(
                                    text="Which parameter do you want to change?"
                                )
                    elif choice == "map":
                        if not await thisMonitor.getMap():
                            pass

                    elif choice == "videos":
                        if not await thisMonitor.getVideo():
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="Error something went wrong, requesting videos \u26A0\ufe0f",
                            )

                elif tag == "getVideo":
                    thisVideo = Video(
                        update=update,
                        context=context,
                        chatId=chat_id,
                        baseUrl=REQ_SHINOBI_BASE_URL["data"],
                        port=REQ_SHINOBI_PORT["data"],
                        apiKey=REQ_SHINOBI_API_KEY["data"],
                        groupKey=REQ_SHINOBI_GROUP_KEY["data"],
                        mid=mid,
                    )
                    if choice is not None:
                        index = int(choice)
                        operation = callbackFullData.get("operation", None)
                        await thisVideo.getVideo(index=index, operation=operation)
                elif tag == "BOTsettings_command":
                    if choice == "terminate":
                        await context.bot.send_message(
                            chat_id=chat_id, text="Shinogramma terminated"
                        )
                        global application
                        if APPLICATION is not None:
                            APPLICATION.stop_running()


@restricted
async def handleTextConfigure(
    update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id = None
):
    if update.effective_message is not None:
        user_text = update.effective_message.text
        logger.debug(msg=f"User wrote: {user_text}")
        if context.user_data is not None:
            if "from" in context.user_data.keys():
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
                    await thisMonitor.configure(key, value)


def parseForCommands():
    frame = inspect.currentframe()
    assert frame is not None
    command_functions = [
        obj
        for name, obj in frame.f_globals.items()
        if inspect.isfunction(object=obj) and name.endswith("_command")
    ]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop=loop)
    for function in command_functions:
        desc = loop.run_until_complete(future=function(update=None, context=None))
        command = function.__name__.split(sep="_")[0]
        name = function.__name__
        if not desc:
            logger.warning(msg=f"{function.__name__} function has no description...")
            fullDesc = "/" + command
        else:
            fullDesc = "/" + command + " - " + desc
        data = {"func": function, "name": name, "command": command, "desc": fullDesc}
        commands.append(data)
    commandJustForLog = ", ".join(c["command"] for i, c in enumerate(iterable=commands))
    logger.debug(msg=f"List of active commands: {commandJustForLog}")

def buildApp() -> bool:
    global APPLICATION
    try:
        import cachetools  # Required by pipreqs in the place of python-telegram-bot[callback-data]
    except ImportError:
        logger.critical(msg="Cachetools module not found")
        return False
    if REQ_SHINOGRAMMA_PERSISTENCE["data"]:
        APPLICATION = startWithPersistence()
    else:
        APPLICATION = startWithoutPersistence()
    callback_query_handler = CallbackQueryHandler(callback=callback_handler)
    text_handler = MessageHandler(
        filters=filters.TEXT & ~filters.COMMAND,
        callback=handleTextConfigure,
    )
    handlers = [callback_query_handler, text_handler]
    # Below commandHandlers for commands are autogenerated parsing command functions
    for command in commands:
        if isinstance(command, dict) and "command" in command and "func" in command:
            commandName: str = command["command"]
            commandFunc: Callable[..., Any] = command["func"]
            handlers.append(CommandHandler(command=commandName, callback=commandFunc))
    if APPLICATION is not None:
        APPLICATION.add_handlers(handlers=handlers)
        return True
    return False


def startWithPersistence():
    myPersistenceInput = PersistenceInput(
        bot_data=False, chat_data=False, user_data=False, callback_data=True
    )
    myPersistence = PicklePersistence(
        filepath=".persistence", store_data=myPersistenceInput
    )
    logger.info(msg="Starting with persistence")
    application = (
        ApplicationBuilder()
        .token(token=REQ_TELEGRAM_API_KEY["data"])
        .persistence(persistence=myPersistence)
        .arbitrary_callback_data(arbitrary_callback_data=True)
        .build()
    )
    return application


def startWithoutPersistence():
    logger.info(msg="Starting without persistence")
    application = (
        ApplicationBuilder()
        .token(token=REQ_TELEGRAM_API_KEY["data"])
        .arbitrary_callback_data(arbitrary_callback_data=True)
        .build()
    )
    return application

def notifyServerStart():
    SERVER = WebhookServer(
        telegramApiKey=REQ_TELEGRAM_API_KEY["data"], 
        baseUrl=REQ_SHINOBI_BASE_URL["data"],
        port=REQ_SHINOBI_PORT["data"],
        shinobiApiKey=REQ_SHINOBI_API_KEY["data"],
        groupKey=REQ_SHINOBI_GROUP_KEY["data"],
    )
    SERVER.start()

if __name__ == "__main__":
    if not buildSettings(data=settings.iniRead()):
        logger.critical(
            msg="Error building and or retrieving settings from config file, exiting..."
        )
        raise SystemExit
    setLogLevel()
    if not len(TELEGRAM_CHAT_ID) > 0:
        logger.warning(
            msg="Chat_id not defined, this could be very dangerous, continuing..."
        )
    parseForCommands()
    if not buildApp():
        logger.critical(
            msg="Error building BOT app, exiting..."
        )
        raise SystemExit
    logger.info(msg="ShinogrammaBot Up and running")
    if APPLICATION is not None:
        # if REQ_SHINOGRAMMA_APISERVER["data"]:
        #     from notify import WebhookServer
        #     notifyServerStart()
        APPLICATION.run_polling(drop_pending_updates=True)
    logger.info(msg="ShinogrammaBot terminated")
