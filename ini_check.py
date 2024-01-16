# This module is needed by the main and takes care of the control and generation of the ShinotifyTB configuration file through input requests.

import configparser
from logging import Logger
from typing import Any, Literal
from urllib.parse import urlparse
from pathlib import Path


class IniSettings:
    """
    This class object is a simple settings config parser, importer and filler.
    """

    def __init__(
        self,
        neededSettings: dict[str, list],
        configFile: Path,
        logger: Logger | None = None,
    ) -> None:
        """
        Constructor of the class.

        Arguments:
        - neededSettings (dict[str, list]): The required data, like this:
        neededSettings: dict[str, list] = {
            "telegram": [{"name": "api_key", "typeOf": str, "data": None, "isUrl": False}],
            "shinobi": [
                {"name": "api_key", "typeOf": str, "data": None, "isUrl": False},
                {"name": "group_key", "typeOf": str, "data": None, "isUrl": False},
                {"name": "base_url", "typeOf": str, "data": None, "isUrl": True},
                {"name": "port", "typeOf": int, "data": None, "isUrl": False},
            ],
        }
        - configFile (Path): The path to config file.
        - logger (Optional[Logger]): The logger instance from instantiating module.
            Default is None.
        """
        self.__neededSettings = neededSettings
        self.__configFile = configFile
        self.__thisLogger = logger
        self.__config = configparser.ConfigParser(
            inline_comment_prefixes=("#", ";"),
            comment_prefixes=("#", ";"),
            empty_lines_in_values=False,
            allow_no_value=False,
        )
        if not self.__iniCheck():
            raise SystemExit

    def __iniCheck(self) -> bool:
        """
        Checks if there are the required data and their integrity in the configuration file;
        this function will provide inputs for the missing data, checking their type.
        """
        self.__config.read(filenames=self.__configFile)
        for section in self.__neededSettings:
            if not self.__config.has_section(section=section):
                self.__tryLogger(
                    log=f"Needed section {section} does not existin your INI file, creating...",
                    level="info",
                )
                self.__config.add_section(section=section)
            for option in self.__neededSettings[section]:
                if self.__config.has_option(section=section, option=option["name"]):
                    self.__tryLogger(
                        log=f"Ok, {section} {option['name']} found.", level="info"
                    )
                else:
                    value = input(f"Please insert the {section} {option['name']}: ")
                    if self.__verifyTypeOf(
                        value=value, typeOf=option["typeOf"], isUrl=option["isUrl"]
                    ):
                        self.__config.set(
                            section=section, option=option["name"], value=value
                        )
                    else:
                        self.__tryLogger(log="TypeOf check failed", level="error")
                        return False
        with open(file=self.__configFile, mode="w") as configfile:
            self.__config.write(fp=configfile)
        return True

    def iniRead(self) -> bool | tuple:
        """
        Read all (required and optional) data from the configuration file, checking their type.
        """
        settings: dict[Any, Any] = {}
        for section in self.__config.sections():
            data: dict = {}
            options = self.__config.items(section=section)
            for option, value in options:
                if value and value != "":
                    for optionInNeeded in self.__neededSettings[section]:
                        if optionInNeeded["name"] == option:
                            convertedValue = self.__verifyTypeOf(
                                value=value,
                                typeOf=optionInNeeded["typeOf"],
                                isUrl=optionInNeeded["isUrl"],
                            )
                            if convertedValue:
                                data[option] = convertedValue
                            else:
                                self.__tryLogger(
                                    log=f"TypeOf check failed in {section} {option}",
                                    level="error",
                                )
                                return False
                    if option == "chat_id":  # If chat_id (comma separated) are defined
                        idList: list[int] = []
                        for i in value.split(sep=","):
                            idList.append(int(i.strip()))  # I turn them into a list
                        if len(idList) > 0:
                            data[option] = idList
                    else:
                        data[option] = value
                settings[section] = data
        if settings:
            if not "chat_id" in settings["telegram"]:
                self.__tryLogger(
                    log="Chat_id not defined, continuing...", level="warning"
                )
            return self.__buildSettings(settings=settings)
        return False

    def __verifyTypeOf(self, value: str, typeOf: type, isUrl: bool) -> bool | str:
        """Verify and optionally convert the type of a value."""
        try:
            if isUrl:
                if self.__verifyUrl(url=value):
                    return value
            else:
                convertedValue = typeOf(value)
                return convertedValue
            return False
        except ValueError:
            return False

    def __verifyUrl(self, url: str) -> bool:
        """Verify if the given URL is valid."""
        try:
            result = urlparse(url=url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def __buildSettings(self, settings: dict) -> tuple:
        """
        Construct a tuple of key-value pairs from the provided settings dictionary.

        Args:
            settings (dict): A dictionary containing configuration settings.

        Returns:
            tuple: A tuple of key-value pairs extracted from the 'settings' dictionary.

        Example:
            Given the 'settings' dictionary:
            {
                'section1': {'param1': 10, 'param2': 'value'},
                'section2': {'param3': True, 'param4': 3.14}
            }

            The function would return a tuple of key-value pairs:
            (
                ('section1_param1', 10),
                ('section1_param2', 'value'),
                ('section2_param3', True),
                ('section2_param4', 3.14)
            )

        Note:
            This function is designed to convert nested dictionaries of configuration settings
            into a flat tuple of key-value pairs. The resulting tuple is used to initialize
            global variables based on configuration data.
        """
        varsDict: dict = {}
        for key, value in settings.items():
            for sub_key, sub_value in value.items():
                variable_name = f"{key}_{sub_key}"
                variable_name = variable_name.replace(" ", "_")
                variable_name = variable_name.replace("-", "_")
                self.__tryLogger(
                    log=f"Assigning global variable {variable_name}...", level="debug"
                )
                varsDict[variable_name] = sub_value
        return tuple(varsDict.items())

    def __tryLogger(
        self,
        log: str,
        level: Literal["debug", "info", "warning", "error", "critical"] = "debug",
    ) -> None:
        """Try to log a message with the specified level using the class logger; if not available, use print.

        Args:
            log (str): The log message.
            level (str, optional): The log level (default is 'debug').
        """
        if self.__thisLogger is not None:
            self.__thisLogger.name = __name__
            log_method = getattr(self.__thisLogger, level)
            log_method(log)
        else:
            print(f"Error writing log, continuing with simple print\n{log}")


if __name__ == "__main__":
    raise SystemExit
