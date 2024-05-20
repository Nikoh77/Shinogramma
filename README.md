# Shinogramma
![head](https://github.com/Nikoh77/Shinogramma/assets/7826178/8ce40f79-014d-4289-9ebb-987ef0b2352a)

This software (aka bot) is intended as a client to conveniently control Shinobi DVS (Digital Video Server, more info at https://shinobi.video) through Telegram, right now it is possible to activate states, take snapshots, watch monitors streaming and stored videos, and manage them.
Shinogramma can run on any computer with Python 3 and an internet connection.\
It doesn't require specific skills or knowledge, nor does it need port forwarding or special configurations on the router <b>so with Shinogramma you can keep secure your local environment closing all incoming ports!</b>

## Notifications system:
Now Shinogramma integrates a complete notification system via Telegram, so it's possible to avoid configuring it on Shinobi.\
You only need to enable event notifications via webhook in your account settings on the Shinobi interface; the URL will be:
`http://SHINOGRAMMA-IP:5001/notifier/?message={{INNER_EVENT_INFO}}`\
Please replace the IP address with the actual one; the port can be changed through the appropriate parameter in the configuration file (more information can be found on this page).\
Shinogramma will be listening on that endpoint for POST and GET requests; to receive images with GET notifications, you also need to enable the JPG API in the settings of each monitor (so I recommend choosing POST).\
This notification system seems to perform much better than the one integrated in Shinobi, but the choice is yours.
## Commands:
Shinogramma is always under development, although it already works very well and has many functions, so commands and things he can do can increase, also maybe with your help; a good place to start is the /help command\
Let's say that with him, you'll be able to take real-time snapshots, view recorded or live videos, modify monitors, and activate states.\
Shinogramma is not intended to replace the web interface; the real goal is to have an immediate tool for control and quick configurations, such as turning on intruder detection when leaving home and turning it off when returning in a simply way and saving time.
## Installation:
Clone this repo with ```git clone https://github.com/Nikoh77/Shinogramma.git```\
(Optional but recommended...) Create a virtual environment\
Just install required modules with ```pip install -r requirements.txt```\
and start it with ```cd Shinogramma/src && python3 shinogramma.py```

An executable version in a single file for Linux is also available in "Releases" area (and bin folder).\
I'm looking for someone to take care of releases for Windows and Mac OS, basically they will just have to compile the new releases with nuitka.

I highly recommend a server deployment, meaning the bot runs as a service rather than a user application. If you're a Linux user, I suggest a distro without desktop environment and configuring it as a service managed by systemd, but this goes beyond the scope of this writing.

## Configuration Parameters
Shinogramma must be executed via terminal.
When started for the first time, it will ask you to enter the necessary data for its operation, namely:
1) Telegram API key, which BotFather will provide you when you create your bot.
2) Shinobi API key, which you can generate directly in your Shinobi user area.
3) Shinobi group key, found at the top in the Shinobi account settings.
4) Shinobi base URL, the web address of your panel, like https://www.example.com/myshinobi
5) Shinobi port number, usually 8080, but depending on the environment, it could also be 443, 80, or other.

In addition to the mandatory parameters, there are some optional ones, such as chat_id.
Using chat_id, you can restrict the usage of the bot to only the Telegram users you desire, such as you and your family members, so that no one else can manipulate your things ;-)\
The IDs should be entered in the config.ini file as follows:
chat_id = 6588899, 77778888, 888888887

Below is the list of settings for each section, with correct formatting and possible values:\
```
[TELEGRAM]
chat_id - optional but recommended - please provide a value for this setting; do not leave it empty, otherwise anyone will be able to interact with your bot and see your cameras. Specifies who can interact with the bot. If more than one, enclose the IDs in square brackets.
api_key - required - the API key of your bot.

[SHINOBI]
api_key - required - the API key of your Shinobi instance.
group_key - required - the group key of the user in Shinobi you want to control.
base_url - required - the access URL to the web UI of your Shinobi.
port - required - default: 8080 - the port number to complete the address.

[SHINOGRAMMA]
loglevel - optional - default: info - the debug level of the app. If you encounter issues, try changing it to debug.
persistence - optional - default: false - old buttons in the chat with the bot will remain functional even after the bot restarts. This consumes more system resources.
webhook_server - optional - default: false - set to true (or 1) to enable event notifications.
webhook_port - optional - default: 5001 - the port for the endpoint (webhook) where Shinogramma listens for event notifications sent by your Shinobi (requires enabling webhook notifications).
```

bans - optional - default: none - this parameters are particularly useful for restricting (banning) specific Telegram user IDs from accessing certain functions.
Below is a table detailing the possible keys within the `bans` dictionary of the configuration file:\

| Parameter         | Description |
|-------------------|-------------|
| `mid_idmonitor`   | Bans specific user IDs from accessing the specified Shinobi monitor ID. The parameter name consists of a fixed part (`mid_`) and a variable part that corresponds to the Shinobi monitor ID, e.g., `mid_99yGrfd0`. |
| `do_snapshot`     | Bans user IDs from taking snapshots. |
| `do_stream`       | Bans user IDs from streaming video. |
| `do_videos`       | Bans user IDs from accessing stored videos. |
| `do_map`          | Bans user IDs from accessing map features. |
| `do_configure`    | Bans user IDs from configuring/editing monitors. |
| `settings`        | Bans user IDs from modifying bot settings. |
| `state_statename` | Bans specific user IDs from changing the state of a defined Shinobi state, e.g., `state_livingroom_on`. The parameter name consists of a fixed part (`state_`) and a variable part that corresponds to the Shinobi state name. |
| `to_notify`       | Bans user IDs from receiving event notifications. |

Note: the syntax must respect standard json, also pay close attention to the comma at the end of each line.\

This is an example of how the bans property should look in your configuration file:
```
[SHINOGRAMMA]
bans = {
	"mid_GiHMUvAMTe": null,
	"do_snapshot": 00022000,
	"do_stream": null,
	"do_videos": null,
	"do_map": 00022000,
	"do_configure": [00022000, 00023000],
	"settings": 00023000,
	"state_Kitchen_On": null,
	"to_notify": 00023000}
```
Each of the above parameters can contain one or multiple Telegram user IDs, separated by commas, enclosed by square brackets.

## CHAT_ID Parameter
Before setting up ban lists, it's crucial to define the `CHAT_ID` parameter. This parameter determines which Telegram user IDs can interact with the bot. IDs not included in this parameter will receive no response from the bot and will be effectively ignored. Therefore, the `CHAT_ID` parameter acts as a whitelist, and the ban lists subtract IDs from this list.

### Example 1:
If `CHAT_ID` contains `447788,556699` and the ban list for `do_videos` includes `447788`, user `447788` will be banned from accessing stored videos, while user `556699` retains full access to all bot features, including videos.

### Example 2:
Consider `CHAT_ID` containing `447788,556699`, with the ban list `mid_77uHG4Ui` including `556699`, and `state_bedroom_on` including `447788`. In this case, user `447788` will not be able to activate the `bedroom_on` state (likely enabling motion detection in the bedroom), and user `556699` will not have access to the monitor with ID `77uHG4Ui`, thus being restricted from its functionalities (videos, streaming, snapshots, etc.).

## IMPORTANT NOTE:
Not defining or leaving the `CHAT_ID` parameter empty allows anyone to interact with the bot and perform any operation, subject to the restrictions imposed by the ban lists. Therefore, to avoid creating extensive ban lists to exclude every Telegram user except for a few, it's advisable to define the `CHAT_ID` field with the intended user IDs first, then tailor the access restrictions as needed.

## Contacts:
For any questions, you can find me on the official Shinobi Discord server (if I don't answer, please ping me).\
Lastly, please report any malfunctions or bugs.
Feel free to expand my code with new features or simply clean it up and/or make it more efficient. If you do so, create a pull request, and I'll be happy to accept it.

### FINAL NOTES:
I already implemented the code for:
* webhook call when an event is triggered,
* Configurable webhooks calls through the bot/chat like to open a gate or to arm an alarm system.\
* monitors configuration through conversation/chat, but I need better API documentation.


I hope to be able to release the final and complete version soon...
