# This module is needed by the main and takes care of the control and generation of the ShinotifyTB configuration file through input requests.

import configparser
import logging
from typing import Any
from urllib.parse import urlparse
from pathlib import Path

logger = logger = logging.getLogger(name=__name__)


class Url(str):
    def __new__(cls, value):
        return super(Url, cls).__new__(cls, object=value)


class IniSettings:
    """
    This class object is a simple settings config parser, importer and filler.
    """

    def __init__(
        self,
        neededSettings: dict[str, list],
        configFile: Path,
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
            Default is None.
        """

        self.__neededSettings = neededSettings
        self.__configFile = configFile
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
                logger.info(
                    msg=f"Needed section {section} does not exist in your INI file, creating..."
                )
                self.__config.add_section(section=section)
            for option in self.__neededSettings[section]:
                if self.__config.has_option(section=section, option=option["name"]):
                    logger.info(msg=f"Ok, {section} {option['name']} found.")
                else:
                    if option["data"] is None:
                        value = input(f"Please insert the {section} {option['name']}: ")
                    else:
                        logger.info(msg=f"{section} {option['name']} not found, assuming default...")
                        value = option["data"]
                        if self.__verifyTypeOf(
                            value=value, typeOf=option["typeOf"], name=option["name"]
                        ):
                            self.__config.set(
                                section=section, option=option["name"], value=value
                            )
                        else:
                            logger.error(
                                msg=f"TypeOf check failed in {section}->{option['name']}->{value}"
                            )
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
            # if section not in self.__neededSettings.keys():
            #     self.__neededSettings[section] = []
            data: dict = {}
            options = self.__config.items(section=section)
            for option, value in options:
                if value and value != "":
                    for optionInNeeded in self.__neededSettings[section]:
                        if optionInNeeded["name"] == option:
                            convertedValue = self.__verifyTypeOf(
                                value=value,
                                typeOf=optionInNeeded["typeOf"],
                                name=optionInNeeded["name"],
                            )
                            if convertedValue:
                                data[option] = convertedValue
                            else:
                                logger.error(
                                    msg=f"TypeOf check failed in {section}->{option}->{value}"
                                )
                                return False
                        else:
                            data[option] = value
                settings[section] = data
        if settings:
            return self.__buildSettings(settings=settings)
        return False

    def __verifyTypeOf(self, value: str, typeOf: type, name: str) -> bool | str:
        """Verify and optionally convert the type of a value."""
        try:
            if typeOf == Url:
                if self.__verifyUrl(url=value):
                    return value
            else:
                if name == "loglevel":
                    if not self.__verifyLogLevel(loglevel=value):
                        return False
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

    def __verifyLogLevel(self, loglevel) -> bool:
        all_levels = [logging.getLevelName(level=level) for level in range(0, 101)]
        if loglevel.upper() in all_levels:
            return True
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
                logger.info(msg=f"Assigning global variable {variable_name}...")
                varsDict[variable_name] = sub_value
        return tuple(varsDict.items())


if __name__ == "__main__":
    raise SystemExit
