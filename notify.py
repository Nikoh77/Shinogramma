from telegram import Bot
from flask import Flask
from werkzeug.serving import ThreadedWSGIServer
import logging
import threading
import asgiref  # Required by pipreqs in the place of Flask[async]

logger = logger = logging.getLogger(name=__name__)


class HttpServer:
    """
    It's a simple http server to receive webhook calls
    """

    def __init__(
        self,
        telegramApiKey: str,
    ) -> None:
        """
        Constructor of the class.

        Arguments:
        - telegramApiKey (str): Needed to send notifications:
        """
        self.TELEGRAM_API_KEY = telegramApiKey
        # self.BOT = Bot(token=self.TELEGRAM_API_KEY)
        self.SERVER: Flask = Flask(import_name=__name__)
        self.SERVER.add_url_rule(
            rule="/send_message", view_func=self.send_message, methods=["GET"]
        )
        self.HTTPSERVER = threading.Thread(target=self.startHttpServer)

    # def startHttpServer(self) -> bool:
    #     try:
    #         http_server = ThreadedWSGIServer(host="127.0.0.1", port=5000, app=self.SERVER)
    #         http_server.serve_forever()
    #         logger.debug(msg="HTTP Serevr started")
    #         return True
    #     except Exception as e:
    #         logger.warning(
    #             msg=f"Error starting HTTP Server: {e}\n alarm notifications will not work"
    #         )
    #         return False

    # @self.SERVER.route(self, rule="/send_message", methods=["GET"])
    # async def send_message(self):
    #     # message = request.args.get("message", "Questo è un messaggio di default.")
    #     await self.BOT.send_message(chat_id=73216475, text="message")
    #     return "Messaggio inviato"

    async def send_message(self):
        # message = request.args.get("message", "Questo è un messaggio di default.")
        await self.BOT.send_message(chat_id=73216475, text="message")
        return "Messaggio inviato"

# httpServer = threading.Thread(target=startHttpServer)
