import logging
from random import choice
from httpQueryUrl import queryUrl
import inspect
import m3u8  # type: ignore
import humanize
import json
import time
import io
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error

logger = logger = logging.getLogger(name=__name__)


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
        self.query = update.callback_query

    async def getSnapshot(self) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = data.json()
            try:
                if json.loads(s=dataInJson[0]["details"])["snap"] == "1":
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
            except error.TelegramError as e:
                logger.error(msg=f"PTB error in {HERE.f_code.co_name}:\n {e}")
            else:  # if error is not of type error.TelegramError (PythonTelegramBot) raise it
                raise
        else:
            logger.error(msg="Error something went wrong requesting snapshot")
        return False

    async def getStream(self) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = data.json()
            """Defining Shinobi's streaming capabilities"""
            streamTypes: dict[str, str] = {
                "hls": "/s.m3u8",
                "mjpeg": "",
                "flv": "/s.flv",
                "mp4": "/s.mp4",
            }
            streamType = json.loads(s=dataInJson[0]["details"])["stream_type"]
            try:
                if streamType in streamTypes.keys():
                    streamUrl = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/{streamType}/{self.GROUP_KEY}/{self.MID}{streamTypes[streamType]}"
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
                else:
                    logger.info(
                        msg="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg..."
                    )
                    await self.CONTEXT.bot.send_message(
                        chat_id=self.CHAT_ID,
                        text="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg... \u26A0\ufe0f",
                    )
            except error.TelegramError as e:
                logger.error(msg=f"PTB error in {HERE.f_code.co_name}:\n {e}")
            else:  # if error is not of type error.TelegramError (PythonTelegramBot) raise it
                raise
        else:
            logger.error(msg="Error something went wrong requesting stream")
        return False

    async def getVideo(self, index=None, operation=None) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        tag = HERE.f_code.co_name  # type: ignore
        url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/videos/{self.GROUP_KEY}/{self.MID}"
        videoList = await queryUrl(url=url)
        if videoList:
            videoListInJson = videoList.json().get("videos")
            if len(videoListInJson) > 0:
                try:
                    if index == None:
                        if await self.videoFirstPass(
                            videoListInJson=videoListInJson, tag=tag
                        ):
                            return True
                    elif operation == None:
                        if await self.videoSecondPass(
                            videoListInJson=videoListInJson,
                            index=index,
                            tag=tag,
                            url=url,
                        ):
                            return True
                    else:
                        if await self.videoThirdPass(
                            videoListInJson=videoListInJson,
                            index=index,
                            url=url,
                            operation=operation,
                        ):
                            return True
                except error.TelegramError as e:
                    logger.error(msg=f"PTB error in {HERE.f_code.co_name}:\n {e}")
                except (
                    Exception
                ):  # if error is not of type error.TelegramError (PythonTelegramBot) raise it
                    raise
            else:
                logger.info(msg="No videos found for this monitor...\u26A0\ufe0f")
                await self.query.answer(
                    "No videos found for this monitor...\u26A0\ufe0f"
                )
                return True
        else:
            logger.error(msg="Error something went wrong requesting videos")
        return False

    async def videoFirstPass(self, videoListInJson: list, tag: str) -> bool:
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
                        callback_data={"tag": tag, "choice": index, "mid": self.MID},
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

    async def videoSecondPass(
        self, videoListInJson: list, index: int, tag: str, url: str
    ) -> bool:
        number = len(videoListInJson)
        video = videoListInJson[index]
        start_time = datetime.fromisoformat(video.get("time"))
        end_time = datetime.fromisoformat(video.get("end"))
        duration = humanize.naturaldelta(value=end_time - start_time)
        time = start_time.strftime("%Y-%m-%d %H:%M:%S")
        size = humanize.naturalsize(value=video.get("size"))
        fileName = video.get("filename")
        videoUrl = url + "/" + fileName
        setRead = f"{videoUrl}/status/2"
        buttons = [
            [
                InlineKeyboardButton(
                    text="set unread",
                    callback_data={
                        "tag": tag,
                        "choice": index,
                        "mid": self.MID,
                        "operation": "unread",
                    },
                ),
                InlineKeyboardButton(
                    text="delete",
                    callback_data={
                        "tag": tag,
                        "choice": index,
                        "mid": self.MID,
                        "operation": "delete",
                    },
                ),
            ]
        ]
        if index > 0:
            buttons[0].insert(
                0,
                InlineKeyboardButton(
                    text="prev",
                    callback_data={"tag": tag, "choice": index - 1, "mid": self.MID},
                ),
            )
        if index < number - 1:
            buttons[0].append(
                InlineKeyboardButton(
                    text="next",
                    callback_data={"tag": tag, "choice": index + 1, "mid": self.MID},
                )
            )
        reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        if video["status"] == 1:
            response = await queryUrl(url=setRead)
            if response:
                if response.json()["ok"]:
                    logger.debug(msg=f"Video {self.MID}->{fileName} set as read")
                    await self.query.answer("Video set as read.\U0001F373")
                else:
                    logger.error(
                        msg="Error something went wrong requesting set read status"
                    )
                    await self.query.answer(
                        "Error something went wrong requesting set read status... \u26A0\ufe0f"
                    )
            else:
                logger.error(
                    msg="Error something went wrong requesting set read status"
                )
        try:
            if await self.CONTEXT.bot.send_video(
                chat_id=self.CHAT_ID,
                video=videoUrl,
                supports_streaming=True,
                caption=f"<b>{index+1}/{number} - {time} - {duration} - {size}</b>",
                reply_markup=reply_markup,
                parse_mode="HTML",
            ):
                logger.debug(msg=f"Video {self.MID}->{fileName} sent")
                return True
        except error.TelegramError as e:
            logger.error(
                msg=f"Error sending video (maybe exceed 20Mb), continuing with link: {e}"
            )
            if await self.CONTEXT.bot.send_message(
                chat_id=self.CHAT_ID,
                text=f"<b>{index+1}/{number} - {time} - {duration} - {size}\n{videoUrl}</b>",
                disable_web_page_preview=False,
                reply_markup=reply_markup,
                parse_mode="HTML",
            ):
                logger.debug(msg=f"Link to Video {self.MID}->{fileName} sent")
                return True
        return False

    async def videoThirdPass(
        self, videoListInJson: list, index: int, url: str, operation: str
    ) -> bool:
        video = videoListInJson[index]
        fileName = video.get("filename")
        videoUrl = url + "/" + fileName
        setUnread = f"{videoUrl}/status/1"
        delete = f"{videoUrl}/delete"
        if operation == "unread":
            url = setUnread
            caption = "set as unread"
        else:
            url = delete
            caption = "has been deleted"
        response = await queryUrl(url=url)
        if response:
            if response.json()["ok"]:
                logger.debug(msg=f"Video {self.MID}->{fileName} {caption}")
                await self.query.answer(f"Video {caption}.\U0001F373")
                return True
            else:
                logger.error(msg="Error something went wrong doing things on video")
                await self.query.answer(
                    "Error something went wrong doing things on video... \u26A0\ufe0f"
                )
        else:
            logger.error(msg="Error something went wrong requesting videos")
        return False

    async def getMap(self):
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = (
                json.loads(data.json()[0]["details"]).get("geolocation").split(",")
            )
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

    async def configure(self, key, value, desc=None) -> bool:
        data = await queryUrl(url=self.url)
        if data:
            dataInJson = data.json()[0]
            details = json.loads(s=dataInJson["details"])
            if key in details.keys():
                details[key] = value
                dataInJson["details"] = details
                endpoint = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/configureMonitor/{self.GROUP_KEY}/{self.MID}"
                method = "post"
                debug = True
                await queryUrl(
                    url=endpoint,
                    method=method,
                    data=data,
                    debug=debug,
                )
                return True
            else:
                logger.info(msg="unknown parameter")
                await self.CONTEXT.bot.send_message(
                    chat_id=self.CHAT_ID, text="Unknown parameter... \u26A0\ufe0f"
                )
        else:
            logger.error(msg="Error something went wrong requesting configuration")
        return False
