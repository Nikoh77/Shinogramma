import logging
from httpQueryUrl import queryUrl
import inspect
import time
from datetime import datetime
import humanize
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error
from typing import Any
from settings import Url

logger = logging.getLogger(name=__name__)

class Monitor:
    """
    A class representing one Shinobi monitor.
    """
    SETTINGS: dict[str, object | dict[str, Any]] = {
        "PROXY_PAGE_URL": {"data": None, "typeOf": Url, "required": True},
        "PROXY_PAGE_TIMEOUT": {"data": 6000, "typeOf": int, "required": False}, # in milliseconds
        "VERIFY_ACTIVE_LINKS_TIMEOUT": {"data": 60, "typeOf": int, "required": False}, # in seconds
    }
    def __init__(
        self, update, context, chatId, baseUrl, port, apiKey, groupKey, mid,
        name, proxyPageUrl, proxyPageTimeout, verifyActiveLinksTimeout) -> None:
        self.UPDATE = update
        self.CONTEXT = context
        self.CHAT_ID = chatId
        self.BASEURL = baseUrl
        self.PORT = port
        self.API_KEY = apiKey
        self.GROUP_KEY = groupKey
        self.MID = mid
        self.name = name
        self.proxyPageUrl = proxyPageUrl
        self.proxyPageTimeout = proxyPageTimeout
        self.verifyActiveLinksTimeout = verifyActiveLinksTimeout
        self.url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/monitor/{self.GROUP_KEY}/{self.MID}"
        self.query = update.callback_query
        self.TYPES = {
            "hls": "s.m3u8",
            "mp4": "s.mp4",
            "flv": "s.flv",
            "mjpeg": "",
        }

    async def getSnapshot(self) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = data.json()
            try:
                if dataInJson[0]["details"]["snap"] == "1":
                    await self.query.answer("Cooking your snapshot...\U0001F373")
                    baseurl = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/jpeg/{self.GROUP_KEY}/{self.MID}/s.jpg"
                    avoidCacheUrl = str(object=int(time.time()))
                    snapshotUrl = baseurl + "?" + avoidCacheUrl
                    if await self.CONTEXT.bot.send_photo(
                        chat_id=self.CHAT_ID, photo=snapshotUrl
                    ):
                        logger.debug(msg="Ok, snaphot sended...")
                        return True
                else:
                    logger.info(msg="Jpeg API not active on this monitor")
                    await self.query.answer(
                        text="Jpeg API not active on this monitor \u26A0\ufe0f",
                        show_alert=True,
                    )
            except Exception as e:
                if isinstance(e, error.TelegramError):
                    logger.error(msg=f"PTB error in {HERE.f_code.co_name}:\n {e}")
                else:
                    logger.error(msg=f"Error in {HERE.f_code.co_name}:\n {e}")
        else:
            logger.error(msg="Error something went wrong requesting snapshot")
        return False

    async def getStream(self) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        tag = HERE.f_code.co_name  # type: ignore
        data = await queryUrl(url=self.url, debug=False)
        if data:
            dataInJson = data.json()
            streams = dataInJson[0]["streams"]
            if not streams:
                logger.info(msg="No streams found for this monitor...")
                await self.CONTEXT.bot.send_message(
                    chat_id=self.CHAT_ID,
                    text="No streams found for this monitor...\u26A0\ufe0f"
                )
                return False
            streamType = dataInJson[0]["details"]["stream_type"]
            subStream = SubStream(monitor=self, verifyActiveLinksTimeout=self.verifyActiveLinksTimeout)
            if streamType == "useSubstream":
                logger.info(msg=f"Monitor {self.MID} is set to use substream...")
                await subStream.verifySubStream(data=data)
            else:
                logger.info(msg=f"Monitor {self.MID} is set to use main stream...")
                if subStream.endOfUrl not in streams:
                    streams.append(subStream.endOfUrl)
                    logger.debug(msg="Substream added to stream list...")
            buttons: list[list] = []
            for stream in streams:
                streamUrl = f"{self.BASEURL}{stream}"
                try:
                    if streamUrl.endswith(self.TYPES["hls"]) and self.proxyPageUrl:
                        logger.debug(msg=f"Stream found: {streamUrl}, sending to proxy page: {self.proxyPageUrl}")
                        url = f"{self.proxyPageUrl}?timeout={self.proxyPageTimeout}&url={streamUrl}"
                        if stream == subStream.endOfUrl:
                            buttons.append(
                                [
                                    InlineKeyboardButton(
                                        text=f"{len(buttons)+1} ACTIVATE {self.name} substream",
                                        callback_data={
                                            "tag": tag,
                                            "subStream": subStream,
                                        },
                                    )
                                ]
                            )
                        else:
                            buttons.append(
                                [
                                    InlineKeyboardButton(
                                        text=f"{len(buttons)+1} PLAY {self.name} main stream",
                                        url=url,
                                    )
                                ]
                            )
                    else:
                        logger.debug(
                            msg=("Stream found but not HLS, "
                                "sending link to use with an external player like"
                                f"VLC: {streamUrl}"
                            )
                        )
                        if stream == subStream.endOfUrl:
                            buttons.append(
                                [
                                    InlineKeyboardButton(
                                        text=f"{len(buttons)+1} ACTIVATE {self.name} substream",
                                        callback_data={
                                            "tag": tag,
                                            "subStream": subStream,
                                        },
                                    )
                                ]
                            )
                        else:
                            buttons.append(
                                [
                                    InlineKeyboardButton(
                                        text=f"{len(buttons)+1} PLAY {self.name} main stream",
                                        url=streamUrl,
                                    )
                                ]
                            )
                except Exception as e:
                    if isinstance(e, error.TelegramError):
                        logger.error(msg=f"Python Telegram Bot error in {HERE.f_code.co_name}:\n {e}")
                    else:
                        logger.error(msg=f"Error in {HERE.f_code.co_name}:\n {e}")
                    return False
            reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await self.CONTEXT.bot.send_message(
                chat_id=self.CHAT_ID,
                text=f"List of available streams for {self.name}:",
                reply_markup=reply_markup,
            )
        else:
            logger.error(msg="Error something went wrong requesting monitor stream data to Shinobi...")
            return False
        return True

    async def getVideo(self, index=None) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        tag = HERE.f_code.co_name  # type: ignore
        url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/videos/{self.GROUP_KEY}/{self.MID}"
        videoList = await queryUrl(url=url)
        if videoList:
            videoListInJson = videoList.json().get("videos")
            if len(videoListInJson) > 0:
                if index == None:
                    buttons: list = []
                    for index, video in enumerate(iterable=(videoListInJson)):
                        start_time = datetime.fromisoformat(video.get("time"))
                        start = humanize.naturaltime(value=start_time)
                        if video["objects"]:
                            objects = video["objects"]
                            videoText = f"{start} -> {objects}"
                        else:
                            videoText = f"{start}"
                        if video["status"] == 1:
                            videoText = videoText.upper()
                        buttons.insert(
                            0,
                            [
                                InlineKeyboardButton(
                                    text=videoText,
                                    callback_data={
                                        "tag": tag,
                                        "choice": index,
                                        "mid": self.MID,
                                    },
                                )
                            ],
                        )
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons[-20:])
                    await self.CONTEXT.bot.send_message(
                        chat_id=self.CHAT_ID,
                        text="Select one video from this limited (20) list <b>(in uppercase are new)</b>.",
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )
                    return True
            else:
                logger.info(msg="No videos found for this monitor...\u26A0\ufe0f")
                await self.query.answer(
                    "No videos found for this monitor...\u26A0\ufe0f"
                )
        return False

    async def getMap(self):
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = (data.json()[0]["details"]).get("geolocation").split(",")
            latitude = dataInJson[0]
            longitude = dataInJson[1]
            if latitude == "49.2578298" and longitude == "-123.2634732":
                await self.query.answer(
                    text="No map data for this monitor...\u26A0\ufe0f", show_alert=True
                )
            print(type(data), data)
        else:
            await self.CONTEXT.bot.send_message(
                chat_id=self.CHAT_ID,
                text="Error something went wrong, request error-->connection \u26A0\ufe0f",
            )
            return False

    async def configure(self, key, value) -> bool:
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = data.json()[0]
            details = dataInJson["details"]
            if key in details.keys():
                details[key] = value
                dataInJson["details"] = details
                endpoint = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/configureMonitor/{self.GROUP_KEY}/{self.MID}?data="
                method = "put"
                debug = True
                response = await queryUrl(
                    url=endpoint,
                    method=method,
                    data=dataInJson,
                    debug=debug,
                )
                if response:
                    if response.json()["ok"]:
                        logger.debug(msg=f"{self.MID}->{key} now configured with: {value}")
                        await self.query.answer("Video set as read.\U0001F373")
                        return True
                    else:
                        logger.error(
                            msg=f"Error something went wrong configuring {self.MID} monitor"
                        )
                        await self.query.answer(
                            f"Error something went wrong configuring {self.MID} monitor... \u26A0\ufe0f"
                        )
                else:
                    logger.error(msg="Error something went wrong requesting configuration")
            else:
                logger.error(msg="unknown parameter")
                await self.CONTEXT.bot.send_message(
                    chat_id=self.CHAT_ID, text="Unknown parameter... \u26A0\ufe0f"
                )
        else:
            logger.error(msg="Error something went wrong requesting configuration")
        return False


class SubStream:
    """
    A class representing a substream.
    """
    def __init__(
        self,
        monitor: Monitor,
        verifyActiveLinksTimeout: int,
    ) -> None:
        self.monitor: Monitor = monitor
        self.SUBSTREAM_CHANNEL = 1
        self.toggleUrl:str = f"{self.monitor.BASEURL}:{self.monitor.PORT}/{self.monitor.API_KEY}/toggleSubstream/{self.monitor.GROUP_KEY}/{self.monitor.MID}"
        self.kindOfStream: str | None = None
        self.endOfUrl: str | None = None
        self.completeUrl: str | None = None
        self.verifyActiveLinksTimeout: int = verifyActiveLinksTimeout

    async def verifySubStream(self, data = None) -> bool:
        if not data:
            logger.debug(msg="Requesting monitor data...")
            data = await queryUrl(url=self.monitor.url, debug=False)
        else:
            logger.debug(msg="Using provided data...")
        if data:
            dataInJson = data.json()
            self.kindOfStream = dataInJson[0]["details"]["substream"]["output"]["stream_type"]
            if self.kindOfStream and self.kindOfStream in self.monitor.TYPES.keys():
                self.endOfUrl = f"/{self.monitor.API_KEY}/{self.kindOfStream}/{self.monitor.GROUP_KEY}/{self.monitor.MID}/{self.SUBSTREAM_CHANNEL}/{self.monitor.TYPES[self.kindOfStream]}"
                self.completeUrl = f"{self.monitor.BASEURL}:{self.monitor.PORT}{self.endOfUrl}"
                if self.completeUrl.endswith(self.monitor.TYPES["hls"]) and self.monitor.proxyPageUrl:
                    self.completeUrl = f"{self.monitor.proxyPageUrl}?timeout={self.monitor.proxyPageTimeout}&url={self.completeUrl}"
                if dataInJson[0]["subStreamActive"]:
                    logger.debug(msg=f"Substream active.")
                    return True
                else:
                    logger.debug(msg=f"Substream inactive.")
            else:
                logger.error(msg="the stream is of unknown type.")
        else:
            logger.error(msg="Error something went wrong requesting monitor data.")
        return False

    async def activateSubStream(self) -> bool:
        activated = await queryUrl(
            url=self.toggleUrl,
        )
        if (
            activated
            and "ok" in activated.json().keys()
            and activated.json()["ok"]
        ):
            return True
        return False
