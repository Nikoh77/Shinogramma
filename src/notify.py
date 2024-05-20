from settings import Url
from telegram.ext import Application
from telegram import InputMediaPhoto
import logging
from httpQueryUrl import queryUrl
import hashlib
import time
import json
from quart import Quart, request, Response, abort
from urllib.parse import unquote, parse_qs

logger = logging.getLogger(name=__name__)
'''
When jpeg api is not enabled for a specific monitor, shinobi sends an image as
placeholder, below a constant with the value of its hash
'''
PLACEHOLDERMD5 = "2a7127c16b2389474c41bc112618462f"

class WebhookServer():
    def __init__(
        self,
        baseUrl: Url,
        shinobiPort: int,
        shinobiApiKey: str,
        groupKey: str,
        port: int,
        toNotify: list,
        application,
    ) -> None:
        self.app: Quart = Quart(import_name=__name__)
        self.baseUrl = baseUrl
        self.port = port
        self.shinobiPort = shinobiPort
        self.shinobiApiKey = shinobiApiKey
        self.groupKey = groupKey
        self.APPLICATION: Application = application
        self.snapshotUrl = "".join([baseUrl.url, ":", str(object=self.shinobiPort), "/", shinobiApiKey, "/jpeg/", groupKey])
        self.toNotify = toNotify
        self.app.add_url_rule(
            rule="/notifier/",
            endpoint="notifier",
            view_func=self.notifier,
            methods=["POST", "GET"],
        )

    def calculate_md5(self, content) -> str:
        md5Hash = hashlib.md5()
        md5Hash.update(content)
        return md5Hash.hexdigest()

    async def runServer(self) -> None:
        try:
            await self.app.run_task(host="0.0.0.0", port=self.port, debug=False)
        except Exception as e:
            logger.warning(msg=f"Error running HTTP Server: {e}")

    async def stopServer(self):
        logger.debug(msg="Shutting down HTTP Server...")
        await self.app.shutdown()

    async def notifier(self) -> Response:
        try:
            message = unquote(string=request.query_string).lstrip("message=")
            if not message:
                logger.error(msg=f"Missing message query parameter...")
                abort(code=400, description="Missing message query parameter")
            messageDict = json.loads(s=message)
            logger.debug(msg=f"Received message: {message}")
            files = await request.files
            mid = messageDict["info"].get("mid", None)
            description = messageDict["info"].get("description", None)
            title = messageDict["info"].get("title", None)
            if "eventDetails" in messageDict["info"].keys():
                reason = messageDict["info"]["eventDetails"].get("reason", None)
                confidence = messageDict["info"]["eventDetails"].get("confidence", None)
            if mid:
                url = f"{self.baseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/monitor/{self.groupKey}/{mid}"
                data = await queryUrl(url=url)
                if not data:
                    logger.error(
                        msg=f"Error querying/getting data from {url} about monitor {mid}..."
                    )
                    abort(
                        code=204
                    )
                dataInJson = data.json()
                name = dataInJson[0].get("name")
        except json.JSONDecodeError:
            logger.error(
                msg=f"{message}\n is not a valid JSON object, returning 400 error code..."
            )
            abort(code=400, description="Message does not contain a valid JSON object")
        except Exception as e:
            logger.error(msg=f"Error executing notifier func: {e}")
            abort(code=204)
        messageToSend = (
            "<b>WARNING:</b>\n"
            + (f"Title: <b>{title}</b>\n" if 'title' in locals() else "")
            + (f"Description: <b>{description}</b>\n" if 'description' in locals() else "")
            + (f"Reason: <b>{reason}</b>\n" if 'reason' in locals() else "")
            + (f"Name: <b>{name}</b>\n" if 'name' in locals() else "")
            + (f"Confidence: <b>{confidence}</b>\n" if 'confidence' in locals() else "")
        )
        if files:
            mediaGroup = self.mediaGroupFormatter(
                files=files, messageToSend=messageToSend
            )
            for user in self.toNotify:
                await self.APPLICATION.bot.send_media_group(
                    chat_id=user, media=mediaGroup
                )
        else:
            if mid:
                snapshotUrl = await self.getSnapshot(mid=mid)
            for user in self.toNotify:
                if "snapshotUrl" in locals().keys() and snapshotUrl is not None:
                    await self.APPLICATION.bot.send_photo(
                        chat_id=user,
                        photo=snapshotUrl,
                        caption=messageToSend,
                        parse_mode="HTML",
                    )
                else:
                    await self.APPLICATION.bot.send_message(
                        chat_id=user, text=messageToSend, parse_mode="HTML"
                    )
        return Response(response="Success", status=200)

    def mediaGroupFormatter(self, files: dict, messageToSend: str) -> list[InputMediaPhoto]:
        mediaGroup = []
        for file in files.values():
            try:
                mediaGroup.append(
                    InputMediaPhoto(
                        media=file.read(),
                        caption=messageToSend,
                        parse_mode="HTML"
                    )
                )
            except Exception as e:
                logger.debug(msg=f"Impossible to read file {file}: {e}")
        return mediaGroup

    async def getSnapshot(self, mid: str) -> str | None:
        imagePath = "".join([self.snapshotUrl, "/", mid, "/s.jpg"])
        response = await queryUrl(url=imagePath)
        if response is not None:
            md5 = self.calculate_md5(content=response.content)
            if md5 != PLACEHOLDERMD5:
                avoidCacheUrl = str(object=int(time.time()))
                snapshotUrl = imagePath + "?" + avoidCacheUrl
                return snapshotUrl
        return None
