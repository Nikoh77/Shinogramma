import logging
from httpQueryUrl import queryUrl
import inspect
import m3u8  # type: ignore
import time
import io
from datetime import datetime
import humanize
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error

logger = logging.getLogger(name=__name__)

class Monitor:
    def __init__(
        self, update, context, chatId, baseUrl, port, apiKey, groupKey, mid
    ) -> None:
        self.UPDATE = update
        self.CONTEXT = context
        self.CHAT_ID = chatId
        self.BASEURL = baseUrl
        self.PORT = port
        self.API_KEY = apiKey
        self.GROUP_KEY = groupKey
        self.MID = mid
        self.url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/monitor/{self.GROUP_KEY}/{self.MID}"
        self.SUBSTREAM_CHANNEL = 1
        self.query = update.callback_query

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
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = data.json()
            if dataInJson[0]["details"]["stream_type"] == "useSubstream":
                logger.debug(msg="This monitor is set to use substream...")
                subStreamActive = dataInJson[0]["subStreamActive"]
                logger.debug(msg=f"substream active: {subStreamActive}")
                if not subStreamActive:
                    activated = await queryUrl(
                        url=f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/toggleSubstream/{self.GROUP_KEY}/{self.MID}"
                    )
                    if activated and "ok" in activated.json().keys() and activated.json()["ok"]:
                        logger.debug(msg=f"Substream activated")
                    else:
                        logger.error(msg=f"Error activating substream")
                        await self.query.answer(
                            text="Error activating substream \u26A0\ufe0f", show_alert=True
                        )
                        return False
            streams = dataInJson[0]["streams"]
            if not streams:
                logger.info(msg="No streams found for this monitor...")
                await self.CONTEXT.bot.send_message(
                    chat_id=self.CHAT_ID,
                    text="No streams found for this monitor...\u26A0\ufe0f"
                )
            elif len(streams) == 1:
                streamUrl = f"{self.BASEURL}{streams[0]}"
                try:
                    logger.debug(msg=f"Only one stream found, sending it: {streamUrl}")
                    pList = m3u8.M3U8()
                    pList.add_playlist(playlist=streamUrl)
                    vFile = io.StringIO(initial_value=pList.dumps())
                    thumbnailFile = open(file="images/shinthumbnail.jpeg", mode="rb")
                    avoidCacheUrl = str(object=int(time.time()))
                    buttons = [[InlineKeyboardButton(text="link", url=streamUrl)]]
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                    await self.CONTEXT.bot.send_document(
                        caption="With IOS use the link below, otherwise above file will be fine",
                        chat_id=self.CHAT_ID,
                        document=vFile,
                        filename=f"stream" + avoidCacheUrl + ".m3u8",
                        protect_content=False,
                        thumbnail=thumbnailFile,
                        reply_markup=reply_markup,
                    )
                    vFile.close()
                    return True
                except Exception as e:
                    if isinstance(e, error.TelegramError):
                        logger.error(msg=f"Python Telegram Bot error in {HERE.f_code.co_name}:\n {e}")
                    else:
                        logger.error(msg=f"Error in {HERE.f_code.co_name}:\n {e}")
            else:
                logger.info(msg="More than one stream found, still not supported yet...")
                await self.CONTEXT.bot.send_message(
                    chat_id=self.CHAT_ID,
                    text="More than one stream found, still not supported yet...\u26A0\ufe0f",
                )
        else:
            logger.error(msg="Error something went wrong requesting monitor stream data to Shinobi...")
        return False

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
