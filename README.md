# Shinogramma
![Shinogramma](https://github.com/Nikoh77/ShinotifyTB/assets/7826178/24a15ed6-09ab-4267-91a2-484198f4abaf)
### The development of Shinogramma is at a standstill, unfortunately I am not able to move forward, I implemented the code to configure monitors through conversation/chat, now I only need Shinobi's dev help to have it working; I have tried in every way but I have not yet succeeded. I don't know if the problem is in Shinobi's API or in my skills (which are certainly not excellent) in any case this is the "status quo", so I'm looking for help to proceed with development....

This software (aka bot) is intended as a client to conveniently control Shinobi CCTV (more info at https://shinobi.video) through Telegram, right now it is possible to activate states, take snapshots and see monitor's streaming but I'm still working on it....\
Shinogramma can run on any computer with Python 3 and an internet connection.\
It doesn't require specific skills or knowledge, nor does it need port forwarding or special configurations on the router.
## Commands:
Shinogramma is in development status so commands and things he can do can increase, a good place to start is the /help command\
Let's say that with him, you'll be able to take real-time snapshots, view recorded or live videos, modify monitors, and activate states.\
Shinogramma is not intended to replace the web interface; the real goal is to have an immediate tool for control and quick configurations, such as turning on intruder detection when leaving home and turning it off when returning.
## Installation:
Just install python-telegram-bot with ```pip install python-telegram-bot```\
In the same way install requests and m3u8 modules\
clone this repo with ```git clone https://github.com/Nikoh77/Shinogramma.git```\
and start it with ```cd Shinogramma && python3 shinogramma.py```\
### or execute install.sh (after giving him exec rights)
When started for the first time, it will ask you to enter the necessary data for its operation, namely:
1) Telegram API key, which BotFather will provide you when you create your bot.
2) Shinobi API key, which you can generate directly in your user area.
3) Shinobi group key, found at the top in the Shinobi account settings.
4) Shinobi port number, usually 8080, but depending on the environment, it could also be 443, 80, or other.

In addition to the mandatory parameters, there are some optional ones, such as chat_id.
Using chat_id, you can restrict the usage of the bot to only the Telegram users you desire, such as you and your family members, so that no one else can manipulate your things ;-)\
The IDs should be entered in the config.ini file as follows:
chat_id = 6588899, 77778888, 888888887

I highly recommend a server installation, meaning the bot runs as a service rather than a user application. If you're a Linux user, I suggest installing it without a desktop environment and configuring it as a service managed by systemd, but this goes beyond the scope of this writing.


For any questions, you can find me on the official Shinobi Discord server (if I don't respond, please ping me).
Lastly, please report any malfunctions or bugs.\Feel free to expand my code with new features or simply clean it up and/or make it more efficient. If you do so, create a pull request, and I'll be happy to accept it.
