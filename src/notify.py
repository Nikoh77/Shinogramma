from settings import Url, AddressKList
from telegram.ext import Application
from telegram import InputMediaPhoto
import logging
from httpQueryUrl import queryUrl
import hashlib
import json
from quart import Quart, request, Response, abort
from urllib.parse import unquote
from typing import Any
import time
import asyncio

logger = logging.getLogger(name=__name__)
'''
When jpeg api is not enabled for a specific monitor, shinobi sends an image as
placeholder, below a constant with the value of its hash
'''
PLACEHOLDERMD5 = "2a7127c16b2389474c41bc112618462f"
localTime: float | None = None

class WebhookServer():
    """
    A class representing a web server.
    """
    # Required settings for this class, you can use "INCLUDE" in settings module
    SETTINGS: dict[str, object | dict[str, Any]] = {
        "SERVER": {"data": False, "typeOf": bool, "required": False},
        "PORT": {"data": 5001, "typeOf": int, "required": False},
        "WEBHOOKS": {"data": None, "typeOf": AddressKList, "required": False},
        "REQUESTS_RATE_LIMIT": {"data": 10, "typeOf": float, "required": False},
    }
    def __init__(
        self,
        baseUrl: Url,
        shinobiPort: int,
        shinobiApiKey: str,
        groupKey: str,
        webhooks: AddressKList,
        port: int,
        requestsRateLimit: float,
        toNotify: list,
        application,
    ) -> None:
        self.app: Quart = Quart(import_name=__name__)
        self.isRunning = False
        self.baseUrl = baseUrl
        self.shinobiPort = shinobiPort
        self.shinobiApiKey = shinobiApiKey
        self.groupKey = groupKey
        self.webhooks = webhooks
        self.port = port
        self.requestsRateLimit = requestsRateLimit
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

    async def runServer(self) -> asyncio.Task[None] | None:
        try:
            self.isRunning = True
            return asyncio.create_task(coro=self.app.run_task(host="0.0.0.0", port=self.port, debug=False), name="WebhookServer")
        except Exception as e:
            logger.warning(msg=f"Error running HTTP Server: {e}")
            return None

    async def stopServer(self):
        logger.debug(msg="Shutting down HTTP Server...")
        await self.app.shutdown()
        self.isRunning = False

    async def notifier(self) -> Response:
        global localTime
        if self.requestsRateLimit and localTime:
            if time.time() - localTime < self.requestsRateLimit:
                logger.warning(msg="Rate limit exceeded, returning 429 error code...")
                abort(code=429, description="Rate limit exceeded")
        try:
            message = unquote(string=request.query_string).lstrip("message=")
            if not message:
                logger.error(msg=f"Missing message query parameter...")
                abort(code=400, description="Missing message query parameter")
            localTime = time.time()  # anti flooding filter
            messageDict = json.loads(s=message)
            logger.debug(msg=f"Received message: {message}")
            files = await request.files
            mid = messageDict["info"].get("mid", None)
            description = messageDict["info"].get("description", None)
            title = messageDict["info"].get("title", None)
            if "eventDetails" in messageDict["info"].keys():
                reason = messageDict["info"]["eventDetails"].get("reason", None)
                matrices = messageDict["info"]["eventDetails"].get("matrices", None)
            if mid:
                url = f"{self.baseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/monitor/{self.groupKey}/{mid}"
                data = await queryUrl(url=url)
                if not data:
                    logger.warning(
                        msg=f"Error querying/getting data from {url} about monitor {mid}..."
                    )
                else:
                    dataInJson = data.json()
                    name = dataInJson[0].get("name")
                    tags: list = dataInJson[0].get("tags", "").split(",")
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
            + (f"Name: <b>{name}</b>\n" if 'name' in locals() else "")
            + (f"Reason: <b>{reason}</b>\n" if 'reason' in locals() else "")  # TODO add emoticons
        )
        if matrices:
            for matrice in matrices:
                messageToSend += (
                    (f"Matrice: <b>{matrice['id']}</b>\n" if 'id' in matrice.keys() else "")
                    + (f"Tag: <b>{matrice['tag']}</b>\n" if 'tag' in matrice.keys() else "")
                    + (f"Confidence: <b>{matrice['confidence']}</b>\n" if 'confidence' in matrice.keys() else "")
                    + (f"Is zombie: <b>{matrice['isZombie']}</b>\n" if 'isZombie' in matrice.keys() else "")
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
        # if self.webhooks:
        #     await self. webhookcalls(webhooks=self.webhooks, tags=tags)
        return Response(response="Success", status=200)

    async def webhookcalls(self, webhooks: AddressKList, tags: list) -> None:
        for tag, webhook in webhooks.items():
            if tag in tags:
                print("OK", "TAG:", tag, "WEBHOOK:", webhook)
                try:
                    await queryUrl(
                        url=f"{webhook}/alarm",
                        debug=True,
                    )
                except Exception as e:
                    logger.error(msg=f"Error calling webhook {webhook}: {e}")

            # for tag, webhook in self.webhooks.items():
            #     asyncio.create_task(
            #         coro=queryUrl(
            #             url=f"{self.webhooks[webhook]}/alarm",
            #             debug=True,
            #             timeout=20,
            #         )
            #     )

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
