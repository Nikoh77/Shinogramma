from httpQueryUrl import queryUrl
import json
import time
import m3u8
import io
import logging

# Start logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class monitor:
    def __init__(self, context, chat_id, shinobiBaseUrl, shinobiPort, shinobiApiKey, shinobiGroupKey, mid):
        self.shinobiBaseUrl=shinobiBaseUrl
        self.shinobiPort=shinobiPort
        self.shinobiApiKey=shinobiApiKey
        self.shinobiGroupKey=shinobiGroupKey
        self.mid=mid
        self.url=f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/monitor/{self.shinobiGroupKey}/{self.mid}"

    async def getsnapshot(self, context, chat_id, query):
        data=await queryUrl(context, chat_id, self.url)
        if data:
            if json.loads(data[0]['details'])['snap']=='1':
                await query.answer("Cooking your snapshot...\U0001F373")
                baseurl = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/jpeg/{self.shinobiGroupKey}/{self.mid}/s.jpg"
                avoidcacheurl = str(int(time.time()))
                url = baseurl+'?'+avoidcacheurl
                await context.bot.send_photo(chat_id=chat_id, photo=url)
                return True
            else:
                await query.answer("Jpeg API not active on this monitor \u26A0\ufe0f")
                logger.info('Jpeg API not active on this monitor')
                return False

    async def getstream(self, context, chat_id):
        data=await queryUrl(context, chat_id, self.url)
        if data:
            streamTypes=['hls','mjpeg','flv','mp4']
            streamType=json.loads(data[0]['details'])['stream_type']
            if streamType in streamTypes:
                if streamType=='hls':
                    url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/hls/{self.shinobiGroupKey}/{self.mid}/s.m3u8"
                elif streamType=='mjpeg':
                    url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/mjpeg/{self.shinobiGroupKey}/{self.mid}"
                elif streamType=='flv':
                    url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/flv/{self.shinobiGroupKey}/{self.mid}/s.flv"
                elif streamType=='mp4':
                    url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/mp4/{self.shinobiGroupKey}/{self.mid}/s.mp4"
                playlist=m3u8.M3U8()
                playlist.add_playlist(url)
                vfile=io.StringIO(playlist.dumps())
                thumbnail_file = open('images/shinthumbnail.jpeg', 'rb')
                avoidcacheurl = str(int(time.time()))
                await context.bot.send_document(chat_id=chat_id, document=vfile, filename=f'stream'+avoidcacheurl+'.m3u8', protect_content=False, thumbnail=thumbnail_file)
                vfile.close()
                return url
            else:
                logger.info('If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg...')
                await context.bot.send_message(chat_id=chat_id, text="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg... \u26A0\ufe0f")
            
    async def getvideo(self, context, chat_id):
        await context.bot.send_message(chat_id=chat_id, text="Not yet implemented... \u26A0\ufe0f")
                
    async def configure(self, context, chat_id, key, value, desc=None):
        data=await queryUrl(context, chat_id, self.url)
        if data:
            data=json.loads(data[0]['details'])
            if key in data.keys():
                data[key]=value
                endpoint = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/configureMonitor/{self.shinobiGroupKey}/{self.mid}"
                method='post'
                debug=True
                await queryUrl(chat_id, context, endpoint, method, data, debug)
            else:
                logger.info('unknown parameter')
                await context.bot.send_message(chat_id=chat_id, text="Unknown parameter... \u26A0\ufe0f")
                return False
if __name__ == '__main__':
    pass
