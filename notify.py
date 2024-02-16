from fastapi import FastAPI, HTTPException
from settings import Url
from telegram.ext import ApplicationBuilder
import logging
import threading
from httpQueryUrl import queryUrl
import hashlib
import time

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
    ) -> None:
        self.app = FastAPI()
        self.APPLICATION = ApplicationBuilder().token(token=telegramApiKey).build()
        self.snapshotUrl = "".join([baseUrl, ":", str(object=port), "/", shinobiApiKey, "/jpeg/", groupKey])

        @self.app.post(path="/send_message")
        async def send_message(
            chat_id: int = 73216475,
            mid: str | None = None,
            query: str = "text",
            message: str = "messaggio di default",
        ):
            print("ciao")
            if query == "text":
                await self.APPLICATION.bot.send_message(chat_id=chat_id, text=message)
            elif query == "image":
                if not mid:
                    raise HTTPException(
                        status_code=400, detail="Percorso immagine non fornito"
                    )
                imagePath = "".join([self.snapshotUrl, "/", mid, "/s.jpg"])
                response = await queryUrl(url=imagePath)
                if response is not None:
                    md5 = self.calculate_md5(content=response.content)
                    if md5 != PLACEHOLDERMD5:
                        avoidCacheUrl = str(object=int(time.time()))
                        snapshotUrl = imagePath + "?" + avoidCacheUrl
                        await self.APPLICATION.bot.send_photo(
                            chat_id=chat_id, photo=snapshotUrl
                        )
            return {"message": "Messaggio inviato"}

    def calculate_md5(self, content) -> str:
        md5Hash = hashlib.md5()
        md5Hash.update(content)
        return md5Hash.hexdigest()

    def run_server(self):
        try:
            import uvicorn
            uvicorn.run(
                app=self.app,
                host="0.0.0.0",
                port=5001,
                log_level="trace",
            )
        except Exception as e:
            logger.warning(msg=f"Error running HTTP Server: {e}")

    def start(self):
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
