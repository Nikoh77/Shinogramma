import requests
import logging

# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def queryUrl(context, chat_id, url, method='get', data=None, debug=False):
        methods=['get','post','put','delete']
        if method in methods:
            http_method = getattr(requests, method)
            try:
                if method==('get' or 'delete'):
                    response = http_method(url)
                else:
                    response = http_method(url, json=data)   
                if response.status_code != 200:
                    logger.info(f'Error {response.status_code} something went wrong, request error.')
                    return False
                else:
                    logger.info('OK, request done.')
                    if debug:
                        print(response.text) # for debug purposes only, to be deleted
                    return response.json()
            except requests.exceptions.RequestException as e:
                await context.bot.send_message(chat_id=chat_id, text='Error something went wrong, request error-->connection \u26A0\ufe0f')
                logger.critical(f'Error something went wrong, request-->connection error: \n{e}')
                return False
        else:            
            print(f'Invalid method: {method}')
            return False
if __name__ == '__main__':
    pass