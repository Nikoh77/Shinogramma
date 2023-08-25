# ShinotifyTB (Telegram Bot)
![Create-a-Telegram-Bot](https://github.com/Nikoh77/ShinotifyTB/assets/7826178/cd9f5403-3d4c-47b7-b360-2fdcbff6b58b)
This BOT has been created to manage Shinobi CCTV (more info at https://shinobi.video) through Telegram.
Currently, it allows listing the states present on the server and activating them. Technically, it can do much more, but for now, it's sufficient for my needs.\
ShinotifyTB can run on any computer with Python 3 and an internet connection. It doesn't require specific skills or knowledge, nor does it need port forwarding or special configurations on the router.\
When started for the first time, it will ask you to enter the necessary data for its operation, namely:
1) Telegram API key, which BotFather will provide you when you create your bot.
2) Shinobi API key, which you can generate directly in your user area.
3) Shinobi group key, found at the top in the Shinobi account settings.
4) Shinobi port number, usually 8080, but depending on the environment, it could also be 443, 80, or other.

In addition to the mandatory parameters, there are some optional ones, such as chat_id.
Using chat_id, you can restrict the usage of the bot to only the Telegram users you desire, such as you and your family members, so that no one else can manipulate your things ;-)\
The IDs should be entered in the config.ini file as follows:
chat_id = 6588899, 77778888, 888888887
## Installation:
Just install python-telegram-bot with ```pip install python-telegram-bot```\
clone this repo with ```git clone https://github.com/Nikoh77/ShinotifyTB.git```\
and start it with ```cd ShinotifyTB && python3 main.py```

I highly recommend a server installation, meaning the bot runs as a service rather than a user application. If you're a Linux user, I suggest installing it without a desktop environment and configuring it as a service managed by systemd, but this goes beyond the scope of this writing.


For any questions, you can find me on the official Shinobi Discord server (if I don't respond, please ping me).
Lastly, please report any malfunctions or bugs.\Feel free to expand my code with new features or simply clean it up and/or make it more efficient. If you do so, create a pull request, and I'll be happy to accept it.
