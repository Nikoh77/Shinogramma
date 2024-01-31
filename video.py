import logging

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
        self.url = f"{self.BASEURL}:{self.PORT}/{self.API_KEY}/monitor/{self.GROUP_KEY}/{self.MID}"
        self.query = update.callback_query
