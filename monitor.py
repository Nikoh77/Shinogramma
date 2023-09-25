import requests
import json
import time
import m3u8
import io
import inspect

class monitor:
    def __init__(self, shinobiBaseUrl, shinobiPort, shinobiApiKey, shinobiGroupKey, mid):
        self.shinobiBaseUrl=shinobiBaseUrl
        self.shinobiPort=shinobiPort
        self.shinobiApiKey=shinobiApiKey
        self.shinobiGroupKey=shinobiGroupKey
        self.mid=mid

    def query(self, url=None, method='get', data=None):
        methods=['get','post','put','delete']
        if url==None:
            url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/monitor/{self.shinobiGroupKey}/{self.mid}"
        if method in methods:
            
        if method.lower() == 'get':
            response = requests.get(url)
        elif method.lower() == 'post':
            response = requests.post(url, json=data)
        elif method.lower() == 'put':
            response = requests.put(url, json=data)
        elif method.lower() == 'delete':
            response = requests.delete(url)
        else:
            print(f'Invalid method: {method}')
            return None
        if response.status_code != 200:
            print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
            return None
        else:
            print(f'OK, request done \U0001F44D')
            if inspect.stack()[1][3]=='configure':
                print(response.text) # for debug purposes only, to be deleted
            return response.json()

    async def getsnapshot(self, context, chat_id, query):
        data=self.query()
        if data:
            if json.loads(data[0]['details'])['snap']=='1':
                await query.answer("Cooking your snapshot...\U0001F373")
                baseurl = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/jpeg/{self.shinobiGroupKey}/{self.mid}/s.jpg"
                avoidcacheurl = str(int(time.time()))
                url = baseurl+'?'+avoidcacheurl
                await context.bot.send_photo(chat_id=chat_id, photo=url)
                return True
            else:
                return False

    async def getstream(self, context, chat_id):
        data=self.query()
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
                try:
                    await context.bot.send_message(chat_id=chat_id, text=url)
                    await context.bot.send_document(chat_id=chat_id, document=vfile, filename=f'stream'+avoidcacheurl+'.m3u8', protect_content=False, thumbnail=thumbnail_file)
                finally:
                    vfile.close()
            else:
                print('If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg...')
                await context.bot.send_message(chat_id=chat_id, text="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg... \u26A0\ufe0f")
            
    async def getvideo(self, context, chat_id):
        await context.bot.send_message(chat_id=chat_id, text="Not yet implemented... \u26A0\ufe0f")
                
    async def configure(self, context, chat_id, key, value, desc=None):
        data=self.query()
        if data:
            data=json.loads(data[0]['details'])
            if key in data.keys():
                data[key]=value
                endpoint = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/configureMonitor/{self.shinobiGroupKey}/{self.mid}"
                test=self.query(endpoint, 'post', data)
                await context.bot.send_message(chat_id=chat_id, text=('request was sent succesfully to your server but '+ \
                                                                    'the parameter will not be modified; I tried everything but I '+ \
                                                                    "couldn\'t get it to work, it's not something I can solve on my own..... \u26A0\ufe0f"))
            else:
                print('unknown parameter')
                await context.bot.send_message(chat_id=chat_id, text="Unknown parameter... \u26A0\ufe0f")
            return False
