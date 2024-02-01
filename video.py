from ast import arg
import logging
import inspect
from httpQueryUrl import queryUrl
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, error
from datetime import datetime
import humanize

logger = logger = logging.getLogger(name=__name__)


class Video:
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
        self.url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/videos/{self.GROUP_KEY}/{self.MID}"
        self.query = update.callback_query

    async def getVideo(self, index=None, operation=None) -> bool:
        HERE = inspect.currentframe()
        assert HERE is not None
        tag = HERE.f_code.co_name  # type: ignore
        url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/videos/{self.GROUP_KEY}/{self.MID}"
        videoList = await queryUrl(url=url)
        if videoList:
            videoListInJson = videoList.json().get("videos")
            try:
                if index is not None:
                    if operation == None:
                        if await self.videoListOperation(
                            videoListInJson=videoListInJson,
                            index=index,
                            tag=tag,
                            url=url,
                        ):
                            return True
                    else:
                        if await self.videoDoOperation(
                            videoListInJson=videoListInJson,
                            index=index,
                            url=url,
                            operation=operation,
                        ):
                            return True
            except Exception as e:
                if isinstance(e, error.TelegramError):
                    logger.error(msg=f"PTB error in {HERE.f_code.co_name}:\n {e}")
                else:
                    raise e
            return True
        else:
            logger.error(msg="Error something went wrong requesting videos")
        return False

    async def videoListOperation(
        self, videoListInJson: list, index: int, tag: str, url: str
    ) -> bool:
        number = len(videoListInJson)
        video = videoListInJson[index]
        objects = video["objects"]
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
                    logger.error(msg="Error something went wrong setting read status")
                    await self.query.answer(
                        "Error something went wrong setting read status... \u26A0\ufe0f"
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
                caption=f"<b>{index+1}/{number} - {time} - {duration} - {size}\ndetected objects: {objects}</b>",
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
                text=f"<b>{index+1}/{number} - {time} - {duration} - {size}\ndetected objects: {objects}\n{videoUrl}</b>",
                disable_web_page_preview=False,
                reply_markup=reply_markup,
                parse_mode="HTML",
            ):
                logger.debug(msg=f"Link to Video {self.MID}->{fileName} sent")
                return True
        return False

    async def videoDoOperation(
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
