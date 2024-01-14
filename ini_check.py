# This module is needed by the main and takes care of the control and generation of the ShinotifyTB configuration file through input requests.

import configparser
from logging import Logger
from typing import Any, Literal

settings: dict[Any, Any] = {}
thisLogger: Logger | None


def iniCheck(needed, config_file, logger=None) -> bool:
    config = configparser.ConfigParser(
        inline_comment_prefixes=("#", ";"),
        comment_prefixes=("#", ";"),
        empty_lines_in_values=False,
        allow_no_value=False,
    )
    config.read(filenames=config_file)
    global thisLogger
    thisLogger = logger
    for section in needed:
        if not config.has_section(section=section):
            _tryLogger_(
                log=f"Needed section {section} does not existin your INI file, creating...",
                level="info",
            )
            config.add_section(section=section)
        for option in needed[section]:
            if config.has_option(section=section, option=option):
                _tryLogger_(log=f"Ok, {section} {option} found.", level="info")
            else:
                config.set(
                    section=section,
                    option=option,
                    value=input(f"Please insert the {section} {option}: "),
                )
    with open(file=config_file, mode="w") as configfile:
        config.write(fp=configfile)
    # Read INI file
    for section in config.sections():
        options = config.items(section=section)
        data: dict = {}
        for option, value in options:
            if value and value != "":  # if value != ("" and None)
                if option == "chat_id":  # If chat_id (comma separated) are defined
                    idList: list[int] = []
                    for i in value.split(sep=","):
                        if i.isdigit():
                            idList.append(int(i.strip()))  # I turn them into a list
                        else:
                            _tryLogger_(
                                log="Found a non digit value for chat_id field in your config",
                                level="warning",
                            )
                    if len(idList) > 0:
                        data[option] = idList
                else:
                    data[option] = value
            settings[section] = data
    if settings:
        if not "chat_id" in settings["telegram"]:
            _tryLogger_(log="Chat_id not defined, continuing...", level="warning")
        print(settings)
        return True
    else:
        return False


def _tryLogger_(
    log: str, level: Literal["debug", "info", "warning", "error", "critical"] = "debug"
) -> None:
    if thisLogger is not None:
        thisLogger.name = __name__
        log_method = getattr(thisLogger, level)
        log_method(log)
    else:
        print(f"Error writing log, continuing with simple print\n{log}")


if __name__ == "__main__":
    raise SystemExit
