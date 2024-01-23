import logging
from httpQueryUrl import queryUrl
import m3u8  # type: ignore
import humanize
import json
import time
import io
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logger = logging.getLogger(name=__name__)


class Monitor:
    def __init__(self, update, context, chatId, baseUrl, port, apiKey, groupKey, mid):
        self.update = update
        self.context = context
        self.CHAT_ID = chatId
        self.BASEURL = baseUrl
        self.PORT = port
        self.API_KEY = apiKey
        self.GROUP_KEY = groupKey
        self.MID = mid
        self.url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/monitor/{self.GROUP_KEY}/{self.MID}"
        self.query = update.callback_query

    async def getsnapshot(self):
        data = await queryUrl(context=self.context, chat_id=self.CHAT_ID, url=self.url)
        if data:
            data = data.json()
            if json.loads(data[0]["details"])["snap"] == "1":
                await self.query.answer("Cooking your snapshot...\U0001F373")
                baseurl = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/jpeg/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}/s.jpg"
                avoidcacheurl = str(object=int(time.time()))
                url = baseurl + "?" + avoidcacheurl
                await self.context.bot.send_photo(chat_id=self.chat_id, photo=url)
                return True
            else:
                await self.query.answer(
                    text="Jpeg API not active on this monitor \u26A0\ufe0f",
                    show_alert=True,
                )
                logger.info(msg="Jpeg API not active on this monitor")
                return False

    async def getstream(self):
        data = await queryUrl(context=self.context, chat_id=self.chat_id, url=self.url)
        if data:
            data = data.json()
            streamTypes = ["hls", "mjpeg", "flv", "mp4"]
            streamType = json.loads(data[0]["details"])["stream_type"]
            if streamType in streamTypes:
                if streamType == "hls":
                    url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/hls/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}/s.m3u8"
                elif streamType == "mjpeg":
                    url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/mjpeg/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}"
                elif streamType == "flv":
                    url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/flv/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}/s.flv"
                elif streamType == "mp4":
                    url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/mp4/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}/s.mp4"
                playlist = m3u8.M3U8()
                playlist.add_playlist(playlist=url)
                vfile = io.StringIO(initial_value=playlist.dumps())
                thumbnail_file = open(file="images/shinthumbnail.jpeg", mode="rb")
                avoidcacheurl = str(object=int(time.time()))
                await self.context.bot.send_document(
                    chat_id=self.chat_id,
                    document=vfile,
                    filename=f"stream" + avoidcacheurl + ".m3u8",
                    protect_content=False,
                    thumbnail=thumbnail_file,
                )
                vfile.close()
                buttons = [[InlineKeyboardButton(text="link", url=url)]]
                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await self.update.effective_message.reply_text(
                    "With IOS use the link below, otherwise above file will be fine",
                    reply_markup=reply_markup,
                )
            else:
                logger.info(
                    msg="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg..."
                )
                await self.context.bot.send_message(
                    chat_id=self.chat_id,
                    text="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg... \u26A0\ufe0f",
                )

    async def getvideo(self, index=None, operation=None, more=False):
        tag = "video"
        url = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/videos/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}"
        method = "get"
        data = None
        debug = True
        videoList = await queryUrl(
            context=self.context,
            chat_id=self.chat_id,
            url=url,
            method=method,
            data=data,
            debug=debug,
        )
        if videoList:
            if index == None:
                videoList = videoList.json().get("videos")
                buttons = []
                for index, video in enumerate((videoList)):
                    start_time = datetime.fromisoformat(video.get("time"))
                    start = humanize.naturaltime(value=start_time)
                    if video["objects"]:
                        objects = video["objects"]
                    if video["status"] == 1:
                        start = start.upper()
                        objects = objects.upper()
                    CallBack = f"{tag};;{index};;{self.mid}"
                    buttons.insert(
                        0,
                        [
                            InlineKeyboardButton(
                                text=f"{start} -> {objects}", callback_data=CallBack
                            )
                        ],
                    )
                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons[-20:])
                await self.context.bot.send_message(
                    chat_id=self.chat_id,
                    text="Select one video from this limited (20) list <b>(in uppercase are new)</b>.",
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            elif operation == None:
                index = int(index)
                number = len(videoList.json().get("videos"))
                video = videoList.json().get("videos")[index]
                start_time = datetime.fromisoformat(video.get("time"))
                end_time = datetime.fromisoformat(video.get("end"))
                duration = humanize.naturaldelta(value=end_time - start_time)
                time = start_time.strftime(format="%Y-%m-%d %H:%M:%S")
                size = humanize.naturalsize(value=video.get("size"))
                fileName = video.get("filename")
                videoUrl = url + "/" + fileName
                setRead = f"{videoUrl}/status/2"
                buttons = [
                    [
                        InlineKeyboardButton(
                            text="set unread",
                            callback_data=f"{tag};;{index};;{self.mid};;unread",
                        ),
                        InlineKeyboardButton(
                            text="delete",
                            callback_data=f"{tag};;{index};;{self.mid};;delete",
                        ),
                    ]
                ]
                if index > 0:
                    buttons[0].insert(
                        0,
                        InlineKeyboardButton(
                            text="prev", callback_data=f"{tag};;{index-1};;{self.mid}"
                        ),
                    )
                if index < number - 1:
                    buttons[0].append(
                        InlineKeyboardButton(
                            text="next", callback_data=f"{tag};;{index+1};;{self.mid}"
                        )
                    )
                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                if video["status"] == 1:
                    temp = await queryUrl(
                        context=self.context,
                        chat_id=self.chat_id,
                        url=setRead,
                        method=method,
                        data=data,
                        debug=debug,
                    )
                    if temp:
                        logger.info(msg=f"Video {self.mid}->{fileName} set as read")
                        await self.query.answer("Video set as read.\U0001F373")
                try:
                    await self.context.bot.send_video(
                        chat_id=self.chat_id,
                        video=videoUrl,
                        supports_streaming=True,
                        caption=f"<b>{index+1}/{number} - {time} - {duration} - {size}</b>",
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )
                except error.TelegramError as e:
                    await self.context.bot.send_message(
                        chat_id=self.chat_id,
                        text=f"<b>{index+1}/{number} - {time} - {duration} - {size}\n{videoUrl}</b>",
                        disable_web_page_preview=False,
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )
                    logger.error(
                        msg=f"Error sending video, maybe exceed 20Mb, sending link...: \n{e}"
                    )
            else:
                index = int(index)
                video = videoList.json().get("videos")[index]
                fileName = video.get("filename")
                videoUrl = url + "/" + fileName
                setUnread = f"{videoUrl}/status/1"
                delete = f"{videoUrl}/delete"
                if operation == "unread":
                    url = setUnread
                    caption = "set as unread"
                elif operation == "delete":
                    url = delete
                    caption = "has been deleted"
                temp = await queryUrl(
                    context=self.context,
                    chat_id=self.chat_id,
                    url=url,
                    method=method,
                    data=data,
                    debug=debug,
                )
                if temp:
                    logger.info(msg=f"Video {self.mid}->{fileName} {caption}")
                    await self.query.answer(f"Video {caption}.\U0001F373")
        else:
            await self.query.answer("No videos found for this monitor...\u26A0\ufe0f")

    async def getmap(self):
        data = await queryUrl(context=self.context, chat_id=self.chat_id, url=self.url)
        if data:
            data = json.loads(data.json()[0]["details"]).get("geolocation").split(",")
            latitude = data[0]
            longitude = data[1]
            if latitude == "49.2578298" and longitude == "-123.2634732":
                await self.query.answer(
                    text="No map data for this monitor...\u26A0\ufe0f", show_alert=True
                )
            print(type(data), data)

    async def configure(self, key, value, desc=None):
        data = await queryUrl(context=self.context, chat_id=self.chat_id, url=self.url)
        if data:
            data = data.json()[0]
            details = json.loads(s=data["details"])
            if key in details.keys():
                details[key] = value
                data["details"] = details
                endpoint = f"{REQ_SHINOBI_BASE_URL['data']}:{REQ_SHINOBI_PORT['data']}/{REQ_SHINOBI_API_KEY['data']}/configureMonitor/{REQ_SHINOBI_GROUP_KEY['data']}/{self.mid}"
                method = "post"
                debug = True
                await queryUrl(
                    context=self.chat_id,
                    chat_id=self.context,
                    url=endpoint,
                    method=method,
                    data=data,
                    debug=debug,
                )
            else:
                logger.info(msg="unknown parameter")
                await self.context.bot.send_message(
                    chat_id=self.chat_id, text="Unknown parameter... \u26A0\ufe0f"
                )
                return False
