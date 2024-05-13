from fastapi import FastAPI, HTTPException, Response, UploadFile, Request, File
from settings import Url
from telegram.ext import ApplicationBuilder
import logging
from httpQueryUrl import queryUrl
import hashlib
import json
from starlette.datastructures import UploadFile as StarletteUploadFile
from typing import List

logger = logging.getLogger(name=__name__)
'''
When jpeg api is not enabled for a specific monitor, shinobi sends an image as
placeholder, below a constant with the value of its hash
'''
PLACEHOLDERMD5 = "2a7127c16b2389474c41bc112618462f"

class WebhookServer():
    def __init__(
        self,
        telegramApiKey: str,
        baseUrl: Url,
        port: int,
        shinobiApiKey: str,
        groupKey: str,
        toNotify: list,
    ) -> None:
        self.app = FastAPI(debug=True)
        self.baseUrl = baseUrl
        self.port = port
        self.shinobiApiKey = shinobiApiKey
        self.groupKey = groupKey
        self.APPLICATION = ApplicationBuilder().token(token=telegramApiKey).build()
        self.snapshotUrl = "".join([baseUrl.url, ":", str(object=port), "/", shinobiApiKey, "/jpeg/", groupKey])
        self.toNotify = toNotify
        self.app.add_api_route(
            path="/notifier", endpoint=self.notifier, methods=["POST"]
        )
        # @self.app.middleware(middleware_type="http")
        # async def log_http_method(request: Request, call_next):
        # logger.debug(
        #     msg=f"A call just receveid, HTTP method: {request.method}"
        # )
        # response = await call_next(request)
        # return response

    # def calculate_md5(self, content) -> str:
    #     md5Hash = hashlib.md5()
    #     md5Hash.update(content)
    #     return md5Hash.hexdigest()

    def runServer(self) -> None:
        try:
            import uvicorn
            uvicorn.run(
                app=self.app,
                host="0.0.0.0",
                port=5001,
                log_config=None,
                log_level= logger.level,
            )
        except Exception as e:
            logger.warning(msg=f"Error running HTTP Server: {e}")

    # async def notifier(self, request: Request, message: str | None = None) -> Response:
    #     form = await request.form()
    #     files = [
    #         (name, file)
    #         for name, file in form.items()
    #         if isinstance(file, StarletteUploadFile)
    #     ]
    #     for name, file in files:
    #         contents = await file.read()
    #         print(f"Received file with filename {name}")
    #     print(f"Received message: {message}")
    #     return Response(content="OK", media_type="text/plain")

    async def notifier(self, request: Request, message: str | None = None) -> Response:
        if not message:
            logger.error(msg=f"Missing message query parameter...")
            raise HTTPException(
                    status_code=400, detail="Missing message query parameter"
                )
        try:
            form = await request.form()
            files = [
                (name, file)
                for name, file in form.items()
                if isinstance(file, StarletteUploadFile)
            ]
            for name, file in files:
                contents = await file.read()
                print(f"Received file with filename {name}")
            print(f"Received message: {message}")
            #     if file1:
            #         logger.info(msg=f"File received")
            if message:
                messageDict = json.loads(s=message)
            mid = messageDict["info"]["mid"]
            reason = messageDict["info"]["eventDetails"]["reason"]
            confidence = messageDict["info"]["eventDetails"]["confidence"]
            url = f"{self.baseUrl}:{self.port}/{self.shinobiApiKey}/monitor/{self.groupKey}/{mid}"
            data = await queryUrl(url=url)
            if not data:
                return Response(status_code=204)
            dataInJson = data.json()
            if not dataInJson:
                logger.warning(msg=f"Error getting data from {url} about monitor {mid}...")
                return Response(status_code=204)
            name = dataInJson[0].get("name")
        except json.JSONDecodeError:
            logger.error(
                msg=f"{message}\n is not a valid JSON object, returning 400 error code..."
            )
            raise HTTPException(
                status_code=400, detail="Message does not contain a valid JSON object"
            )
        except Exception as e:
            logger.error(msg=f"Error executing notifier func: {e}")
            return Response(status_code=204)
        messageToSend = f"Reason: <b>{reason}</b>\nName: <b>{name}</b>\nConfidence: <b>{confidence}</b>"
        for user in self.toNotify:
            await self.APPLICATION.bot.send_message(
                chat_id=user, text=messageToSend, parse_mode="HTML"
            )

        # elif query == "image":
        #     if not mid:
        #         raise HTTPException(
        #             status_code=400, detail="Percorso immagine non fornito"
        #         )
        #     imagePath = "".join([self.snapshotUrl, "/", mid, "/s.jpg"])
        #     response = await queryUrl(url=imagePath)
        #     if response is not None:
        #         md5 = self.calculate_md5(content=response.content)
        #         if md5 != PLACEHOLDERMD5:
        #             avoidCacheUrl = str(object=int(time.time()))
        #             snapshotUrl = imagePath + "?" + avoidCacheUrl
        #             await self.APPLICATION.bot.send_photo(
        #                 chat_id=chat_id, photo=snapshotUrl
        #             )
        return Response(content="OK", media_type="text/plain")
