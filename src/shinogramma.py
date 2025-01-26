# This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram.
# I am Nikoh (nikoh@nikoh.it), if you think this bot is useful please consider helping me improving it on github
# or donate me a coffee

import asyncio
# from re import S
import signal
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
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    constants,
)
from telegram.constants import ParseMode
from functools import wraps
import colorlog
import logging
import inspect
from typing import Callable, Any
from httpQueryUrl import queryUrl
from notify import WebhookServer
from settings import IniSettings, Url, IP, LogLevel
from monitor import Monitor, SubStream
from pathlib import Path
from video import Video
# import socket
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
    "notify",
]
CONFIG_FILE: Path = Path("config.ini")
APPLICATION: Application | None = None  # The Bot
SERVERAPI: WebhookServer | None = None  # The Webhook Server
"""
Below required and optional data for running this software defined as a global scope
constant.
This constant is passed to the `settings` class; more info on the settings.py file.
"""
SETTINGS: dict[str, dict[str, object | dict[str, Any]]] = {
    "TELEGRAM": {
        "CHAT_ID": {"data": None, "typeOf": list, "required": False},
        "API_KEY": {"data": None, "typeOf": str, "required": True},
    },
    "SHINOBI": {
        "API_KEY": {"data": None, "typeOf": str, "required": True},
        "GROUP_KEY": {"data": None, "typeOf": str, "required": True},
        "BASE_URL": {"data": None, "typeOf": Url, "required": True},
        "PORT": {"data": 8080, "typeOf": int, "required": True},
    },
    "SHINOGRAMMA": {
        # log level chosen in the config file is applied after settings are loaded
        # so if you want to debug how settings are loaded you must change LOGLEVEL here also
        "LOGLEVEL": {"data": "info", "typeOf": LogLevel, "required": False},
        "PERSISTENCE": {"data": False, "typeOf": bool, "required": False},
        "BANS": {"data": None, "typeOf": dict, "required": False},
    },
    "WEBHOOK": {"INCLUDE": WebhookServer},
    "MONITOR": {"INCLUDE": Monitor},
}
# Defining root variables
commands: list = []
confParam, confParamVal = range(2)
shutdownEvent = asyncio.Event()
activeSubstreams: list[dict[str, SubStream | int | str | None]] = []

# Start logging
logger = colorlog.getLogger(name=__name__)
file_handler = logging.FileHandler(filename="shinogramma.log")
console_handler = logging.StreamHandler()

logging.basicConfig(
    format="[%(levelname)-8s] %(asctime)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="%",
    handlers=[file_handler, console_handler],
)

formatter = colorlog.ColoredFormatter(
    fmt="%(log_color)s[%(levelname)-8s] %(blue)s %(asctime)s %(name)s %(reset)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
    log_colors={
        "TRACE": "bold_cyan",
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "bold_red",
        "CRITICAL": "bold_red,bg_white",
    },
)

console_handler.setFormatter(fmt=formatter)


def setLogLevel() -> None:
    currentLevel = logging.getLevelName(level=logger.getEffectiveLevel())
    if "SHINOGRAMMA" in SETTINGS:
        if isinstance(SETTINGS["SHINOGRAMMA"]["LOGLEVEL"], dict):
            setLevel = str(object=SETTINGS["SHINOGRAMMA"]["LOGLEVEL"]["data"]).upper()
            if setLevel != None and setLevel != currentLevel:
                getattr(
                    logger,
                    logging.getLevelName(level=logger.getEffectiveLevel()).lower(),
                )(
                    f"switching from log level {logging.getLevelName(level=logger.getEffectiveLevel())}"
                )
                logger.setLevel(level=setLevel)
                currentLevel = logging.getLevelName(
                    level=logger.getEffectiveLevel()
                ).lower()
                getattr(logger, currentLevel)(
                    msg=f"to level {logging.getLevelName(level=logger.getEffectiveLevel())}"
                )
                for module in MODULES_LOGGERS:
                    logging.getLogger(name=module).setLevel(level=setLevel)

setLogLevel()
# Start decorators section
def restricted(func):
    """Restrict chat only with id(es) defined in config.ini"""
    @wraps(wrapped=func)
    async def wrapped(update, context, *args, **kwargs):
        if update is not None and context is not None:
            chat_id = update.effective_user.id
            assert isinstance(SETTINGS["TELEGRAM"]["CHAT_ID"], dict)
            if len(SETTINGS["TELEGRAM"]["CHAT_ID"]["data"]) > 0:
                if chat_id not in SETTINGS["TELEGRAM"]["CHAT_ID"]["data"]:
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
            if isinstance(SETTINGS["SHINOBI"]["BASE_URL"], dict):
                base_url = SETTINGS["SHINOBI"]["BASE_URL"]["data"]
            if isinstance(SETTINGS["SHINOBI"]["PORT"], dict):
                port = SETTINGS["SHINOBI"]["PORT"]["data"]
            if isinstance(SETTINGS["SHINOBI"]["API_KEY"], dict):
                api_key = SETTINGS["SHINOBI"]["API_KEY"]["data"]
            if isinstance(SETTINGS["SHINOBI"]["GROUP_KEY"], dict):
                group_key = SETTINGS["SHINOBI"]["GROUP_KEY"]["data"]
            url = f"{base_url}:{port}/{api_key}/monitorStates/{group_key}"
            data = await queryUrl(url=url)
            if data:
                dataInJson = data.json()
                states = []
                if SETTINGS["SHINOGRAMMA"]["BANS"] and isinstance(SETTINGS["SHINOGRAMMA"]["BANS"], dict):
                    for i in dataInJson["presets"]:
                        var = f"state_{i['name']}"
                        if (
                            var in SETTINGS["SHINOGRAMMA"]["BANS"]["data"].keys()
                            and SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]
                        ):
                            try:
                                if chat_id in SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]:
                                    continue
                            except TypeError as e:
                                if chat_id == SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]:
                                    continue
                            except Exception as e:
                                logger.error(msg=f"Error verifyng BANS for states: {e}")
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
            if isinstance(SETTINGS["SHINOBI"]["BASE_URL"], dict):
                base_url = SETTINGS["SHINOBI"]["BASE_URL"]["data"]
            if isinstance(SETTINGS["SHINOBI"]["PORT"], dict):
                port = SETTINGS["SHINOBI"]["PORT"]["data"]
            if isinstance(SETTINGS["SHINOBI"]["API_KEY"], dict):
                api_key = SETTINGS["SHINOBI"]["API_KEY"]["data"]
            if isinstance(SETTINGS["SHINOBI"]["GROUP_KEY"], dict):
                group_key = SETTINGS["SHINOBI"]["GROUP_KEY"]["data"]
            url = f"{base_url}:{port}/{api_key}/monitor/{group_key}"
            data = await queryUrl(url=url)
            if data:
                dataInJson = data.json()
                monitors = []
                if isinstance(SETTINGS["SHINOGRAMMA"]["BANS"], dict):
                    for i in dataInJson:
                        var = f"mid_{i['mid']}"
                        if (
                            var in SETTINGS["SHINOGRAMMA"]["BANS"]["data"].keys()
                            and SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]
                        ):
                            try:
                                if chat_id in SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]:
                                    continue
                            except TypeError as e:
                                if chat_id == SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]:
                                    continue
                            except Exception as e:
                                logger.error(msg=f"Error verifyng BANS for monitors: {e}")
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
        if isinstance(SETTINGS["SHINOGRAMMA"]["BANS"], dict):
            if (
                "settings" in SETTINGS["SHINOGRAMMA"]["BANS"]["data"].keys()
                and SETTINGS["SHINOGRAMMA"]["BANS"]["data"]["settings"]
            ):
                authorized = True
                try:
                    if chat_id in SETTINGS["SHINOGRAMMA"]["BANS"]["data"]["settings"]:
                        authorized = False
                except TypeError as e:
                    if chat_id == SETTINGS["SHINOGRAMMA"]["BANS"]["data"]["settings"]:
                        authorized = False
                except Exception as e:
                    logger.error(msg=f"Error verifyng BANS for states: {e}")
                if authorized:
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
        if isinstance(SETTINGS["SHINOGRAMMA"]["BANS"], dict):
            for choice in choices:
                var = f"do_{choice}"
                if (
                    var in SETTINGS["SHINOGRAMMA"]["BANS"]["data"].keys()
                    and SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]
                ):
                    try:
                        if chat_id in SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]:
                            continue
                    except TypeError as e:
                        if chat_id == SETTINGS["SHINOGRAMMA"]["BANS"]["data"][var]:
                            continue
                    except Exception as e:
                        logger.error(msg=f"Error verifyng BANS for monitors subcommand: {e}")
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
    if len(buttons) > 0:
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
                if isinstance(SETTINGS["SHINOBI"]["BASE_URL"], dict):
                    base_url = SETTINGS["SHINOBI"]["BASE_URL"]["data"]
                if isinstance(SETTINGS["SHINOBI"]["PORT"], dict):
                    port = SETTINGS["SHINOBI"]["PORT"]["data"]
                if isinstance(SETTINGS["SHINOBI"]["API_KEY"], dict):
                    api_key = SETTINGS["SHINOBI"]["API_KEY"]["data"]
                if isinstance(SETTINGS["SHINOBI"]["GROUP_KEY"], dict):
                    group_key = SETTINGS["SHINOBI"]["GROUP_KEY"]["data"]
                callbackFullData: dict = query.data
                logger.debug(msg=f"Callback received: {callbackFullData}")
                tag = callbackFullData.get("tag")
                mid = callbackFullData.get("mid", None)
                choice = callbackFullData.get("choice", None)
                operation = callbackFullData.get("operation", None)
                if tag == "states_command":
                    url = f"{base_url}:{port}/{api_key}/monitorStates/{group_key}/{choice}"
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
                    if isinstance(SETTINGS["MONITOR"]["PROXY_PAGE_URL"], dict):
                        proxyPageUrl = SETTINGS["MONITOR"]["PROXY_PAGE_URL"]["data"]
                    if isinstance(SETTINGS["MONITOR"]["TIMEOUT"], dict):
                        timeout = SETTINGS["MONITOR"]["TIMEOUT"]["data"]
                        thisMonitor = Monitor(
                            update=update,
                            context=context,
                            chatId=chat_id,
                            baseUrl=base_url,
                            port=port,
                            apiKey=api_key,
                            groupKey=group_key,
                            mid=mid,
                            proxyPageUrl=proxyPageUrl,
                            timeout=timeout
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
                elif tag == "getStream":
                    subStream: SubStream = callbackFullData.get("subStream", None)
                    try:
                        if not await subStream.verifySubStream():
                            if not await subStream.activateSubStream():
                                logger.error(msg="Error activating substream.")
                                await query.answer(
                                    text=f"Error activating substream. \u26A0\ufe0f",
                                    show_alert=True,
                                )
                                return
                            logger.debug(msg="Substream activate successfully, sending link...")
                            await query.answer(
                                text=f"Substream activate successfully, sending link... \u26A0\ufe0f",
                                show_alert=True,
                            )
                        else:
                            logger.debug(msg="Substream already active, sending link...")
                            await query.answer(
                                text=f"Substream already active, sending link... \u26A0\ufe0f",
                                show_alert=True,
                            )
                        message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=f'<a href="{subStream.completeUrl}">Click to play</a>',
                        parse_mode=ParseMode.HTML,
                        )
                        if not activeSubstreams:
                            activeSubstreams.append({
                                "message_id": message.message_id,
                                "sub_stream": subStream,
                                "sub_url": subStream.completeUrl
                            })
                        else:
                            for activeSubstream in activeSubstreams:
                                present = False
                                if subStream.completeUrl == activeSubstream["sub_url"]:
                                    present = True
                                    break
                            if not present:
                                activeSubstreams.append({
                                    "message_id": message.message_id,
                                    "sub_stream": subStream,
                                    "sub_url": subStream.completeUrl
                                })
                        print(activeSubstreams)
                    except Exception as e:
                        logger.error(msg=f"Error activating substream: {e}")

                elif tag == "getVideo":
                    thisVideo = Video(
                        update=update,
                        context=context,
                        chatId=chat_id,
                        baseUrl=base_url,
                        port=port,
                        apiKey=api_key,
                        groupKey=group_key,
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
                        shutdownEvent.set()
                        # raise SystemExit
                        # await appShutdown()
                        # os.kill(os.getpid(), signal.SIGINT)


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
        # Required by pipreqs in the place of python-telegram-bot[callback-data]
        import cachetools  # type: ignore
    except ImportError:
        logger.critical(msg="Cachetools module not found")
        return False
    assert isinstance(SETTINGS["SHINOGRAMMA"]["PERSISTENCE"], dict)
    if SETTINGS['SHINOGRAMMA']['PERSISTENCE']["data"]:
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
    if APPLICATION:
        APPLICATION.add_handlers(handlers=handlers)
        return True
    return False


def startWithPersistence() -> Application:
    assert isinstance(SETTINGS["TELEGRAM"]["API_KEY"], dict)
    myPersistenceInput = PersistenceInput(
        bot_data=False, chat_data=False, user_data=False, callback_data=True
    )
    myPersistence = PicklePersistence(
        filepath=".persistence", store_data=myPersistenceInput
    )
    logger.info(msg="Starting with persistence")
    application = (
        ApplicationBuilder()
        .token(token=SETTINGS['TELEGRAM']['API_KEY']["data"])
        .persistence(persistence=myPersistence)
        .arbitrary_callback_data(arbitrary_callback_data=True)
        .build()
    )
    return application


def startWithoutPersistence() -> Application:
    assert isinstance(SETTINGS["TELEGRAM"]["API_KEY"], dict)
    logger.info(msg="Starting without persistence")
    application = (
        ApplicationBuilder()
        .token(token=SETTINGS['TELEGRAM']['API_KEY']["data"])
        .arbitrary_callback_data(arbitrary_callback_data=True)
        .build()
    )
    return application


def notifyServerStart() -> None:
    if isinstance(SETTINGS["TELEGRAM"]["CHAT_ID"], dict):
        chat_id = SETTINGS["TELEGRAM"]["CHAT_ID"]["data"]
    if isinstance(SETTINGS["SHINOGRAMMA"]["BANS"], dict):
        bans = SETTINGS["SHINOGRAMMA"]["BANS"]["data"]
    if isinstance(SETTINGS["SHINOBI"]["BASE_URL"], dict):
        base_url = SETTINGS["SHINOBI"]["BASE_URL"]["data"]
    if isinstance(SETTINGS["SHINOBI"]["PORT"], dict):
        shinobiPort = SETTINGS["SHINOBI"]["PORT"]["data"]
    if isinstance(SETTINGS["SHINOBI"]["API_KEY"], dict):
        api_key = SETTINGS["SHINOBI"]["API_KEY"]["data"]
    if isinstance(SETTINGS["SHINOBI"]["GROUP_KEY"], dict):
        group_key = SETTINGS["SHINOBI"]["GROUP_KEY"]["data"]
    if isinstance(SETTINGS["WEBHOOK"]["WEBHOOKS"], dict):
        webhooks = SETTINGS["WEBHOOK"]["WEBHOOKS"]["data"]
    if isinstance(SETTINGS["WEBHOOK"]["REQUESTS_RATE_LIMIT"], dict):
        requestsRateLimit = SETTINGS["WEBHOOK"]["REQUESTS_RATE_LIMIT"]["data"]
    if isinstance(SETTINGS["WEBHOOK"]["PORT"], dict):
        port = SETTINGS["WEBHOOK"]["PORT"]["data"]
    list1: list = chat_id
    if "to_notify" in bans.keys():
        if isinstance(bans["to_notify"], list):
            list2 = bans["to_notify"]
        else:
            list2 = [bans["to_notify"]]
        toNotify = [item for item in list1 if item not in list2]
    else:
        toNotify = list1
    global SERVERAPI
    SERVERAPI = WebhookServer(
        baseUrl=base_url,
        shinobiPort=shinobiPort,
        shinobiApiKey=api_key,
        groupKey=group_key,
        webhooks=webhooks,
        port=port,
        requestsRateLimit=requestsRateLimit,
        toNotify=toNotify,
        application=APPLICATION,
    )

async def starter(app: Application) -> None:
    loop = asyncio.get_event_loop()
    taskList: list[asyncio.tasks.Task] = []
    await app.initialize()
    await app.start()
    if app.updater:
        taskList.append(asyncio.create_task(coro=app.updater.start_polling(drop_pending_updates=True), name="Polling"))
    if SERVERAPI:
        task = await SERVERAPI.runServer()
        if task:
            taskList.append(task)
            attempt: int = 0
            while not SERVERAPI.isRunning():
                attempt += 1
                if attempt > 10:
                    logger.error(msg="Webhook server not ready, start Shinogramma whitout it")
                    break
                await asyncio.sleep(delay=1)
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(
            sig=getattr(signal, signame),
            callback=lambda: asyncio.create_task(coro=appShutdown(), name="Shutdown"),
        )
    if await shutdownEvent.wait():
        await appShutdown()

async def appShutdown() -> None:
    if shutdownEvent.is_set():
        logger.info(msg="ShinogrammaBot shutting down")
        if SERVERAPI:
            if SERVERAPI.isRunning():
                await SERVERAPI.stopServer()
        if APPLICATION:
            if APPLICATION.updater:
                await APPLICATION.updater.stop()
                await APPLICATION.stop()
                await APPLICATION.shutdown()
    else:
        shutdownEvent.set()


if __name__ == "__main__":
    mySettings = IniSettings(neededSettings=SETTINGS, configFile=CONFIG_FILE)
    if not mySettings.iniRead():
        logger.critical(
            msg="Error building and/or retrieving settings from config file, exiting..."
        )
        raise SystemExit
    setLogLevel()
    assert isinstance(SETTINGS["TELEGRAM"]["CHAT_ID"], dict)
    if not len(SETTINGS['TELEGRAM']['CHAT_ID']["data"]) > 0:
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
    if APPLICATION:
        assert isinstance(SETTINGS["WEBHOOK"]["SERVER"], dict)
        if SETTINGS["WEBHOOK"]["SERVER"]["data"]:
            from notify import WebhookServer
            notifyServerStart()
        asyncio.run(main=starter(app=APPLICATION))
    logger.info(msg="ShinogrammaBot terminated")
