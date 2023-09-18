import requests
import json
import time
import m3u8
import io

class monitor:
    def __init__(self, shinobiBaseUrl, shinobiPort, shinobiApiKey, shinobiGroupKey, mid):
        self.shinobiBaseUrl=shinobiBaseUrl
        self.shinobiPort=shinobiPort
        self.shinobiApiKey=shinobiApiKey
        self.shinobiGroupKey=shinobiGroupKey
        self.mid=mid
        def getdata(self):
            url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/monitor/{self.shinobiGroupKey}/{self.mid}"
            response = requests.get(url)
            if response.status_code != 200:
                print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
                return
            else:
                print(f'OK, done \U0001F44D')
                return response.json()
        self.data=getdata(self)

    async def getsnapshot(self, context, chat_id, query):
        if json.loads(self.data[0]['details'])['snap']=='1':
            await query.answer("Cooking your snapshot...\U0001F373")
            baseurl = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/jpeg/{self.shinobiGroupKey}/{self.mid}/s.jpg"
            avoidcacheurl = str(int(time.time()))
            url = baseurl+'?'+avoidcacheurl
            await context.bot.send_photo(chat_id=chat_id, photo=url)
            return True
        else:
            return False

    async def getstream(self, context, chat_id, query):
        streamTypes=['hls','mjpeg','flv','mp4']
        streamType=json.loads(self.data[0]['details'])['stream_type']
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
            try:
                await context.bot.send_document(chat_id=chat_id, document=vfile, filename='stream.m3u8', protect_content=True, thumbnail=thumbnail_file)
            finally:
                vfile.close()
        else:
            print('If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg...')
            await context.bot.send_message(chat_id=chat_id, text="If streaming exists it is an unsupported format, it should be hls, mp4 or mjpeg... \u26A0\ufe0f")
            
    async def getvideo(self, context, chat_id, query):
        pass
                
    async def configure(self, context, chat_id, query, key, value, desc):
        pass
    #     data = json.loads(self.getdata()[0]['details'])
    #     endpoint = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/configureMonitor/{self.shinobiGroupKey}/{key}"
    #     #queryurl = f"{settings['Shinobi']['url']}:{settings['Shinobi']['port']}/{settings['Shinobi']['api_key']}/monitor/{settings['Shinobi']['group_key']}/{selection}"
    #         query=disAssebleMonitor(selection)
    #         query['details']['snap'] = "1"
    #         json.dumps(query, indent=4)
    #         response = requests.post(endpoint, data=query)
    #         if response.status_code != 200:
    #             print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
    #             print(response.text)
    #             await context.bot.send_message(chat_id=chat_id, text='Error something went wrong, request error \u26A0\ufe0f')
    #             return
    #         else:
    #             print(f'OK, done \U0001F44D')
    #             print(response.text)
    #             await context.bot.send_message(chat_id=chat_id, text=f'OK, done \U0001F44D')

    # async def disAssebleMonitor(self):
    #     url = f"{self.shinobiBaseUrl}:{self.shinobiPort}/{self.shinobiApiKey}/monitor/{self.shinobiGroupKey}/{self.mid}"
    #     response = requests.get(url)
    #     if response.status_code != 200:
    #         print(f'Error {response.status_code} something went wrong, request error \u26A0\ufe0f')
    #         await context.bot.send_message(chat_id=chat_id, text='Error something went wrong, request error \u26A0\ufe0f')
    #         return
    #     else:
    #         print(f'OK, done \U0001F44D')
    #         await context.bot.send_message(chat_id=chat_id, text=f'OK, done \U0001F44D')
    #         print('disassembling monitor...')
    #         response = response.json()
    #         monitor=response[0]
    #         monitor['details']=json.loads(monitor.get('details'))
    #         print('reassembling monitor...')
    #         # Needed keys to make API query
    #         keys=['mode', 'mid', 'name', 'tags', 'type', 'protocol', 'host', 'port', 'path', 'height', 'width', 'ext', 'fps', 'details']
    #         data={}
    #         for key in keys:
    #             data[key]=monitor.get(key)
    #         return(data)
