"""
This is a simple settings config parser, importer and filler module by Nikoh version 1.0.0
On main/calling module, the required data for running this software, are defined
as a global scope constants.
It is important to follow this syntax defining the constants:

REQ_SECTION_OPTION: dict = {"data": None, "typeOf": type}


For example, if you want to have following data in the configuration file:

[BANANAS]
number_of = 10
color = green

We need to add the following constants in the main module:

REQ_BANANAS_NUMBER_OF: dict = {"data": None, "typeOf": int}
REQ_BANANAS_COLOR: dict = {"data": None, "typeOf": str}

When starting, settings will ask the user to enter the number and color of bananas...

It is important to note that the value of 'data' key of all these constants is updated
at runtime from None to values read from the configuration file by buildSettings function.
Starting from these constants the variable `neededSettings` is created with this function
that you must call in the main module, after the constants definition:

for i in list(globals().keys()):
    if i.startswith("REQ_"):
        section = i.split(sep="_")[1]
        option = i.replace("REQ_" + section + "_", "").lower()
        if section not in neededSettings.keys():
            neededSettings.update({section: []})
        neededSettings[section].append(
            {
                "name": option,
                "data": globals()[i].get("data"),
                "typeOf": globals()[i].get("typeOf"),
            }
        )

This done, you can instantiate the class like this:

settings = IniSettings(neededSettings=neededSettings, configFile=CONFIG_FILE)

and finally, as you want, you can call the iniRead method to read the settings from the config file:

if not buildSettings(data=settings.iniRead()):
    logger.critical(msg="Error building and or retrieving settings from config file, exiting...")
    raise SystemExit

where buildSettings is a function that you must define in the main module to fill and replace values of
global scope variables with the values read from the config file:

def buildSettings(data) -> bool:
    if data:
        for i, v in data:
            varName = "REQ_" + i.upper()
            if varName in globals().keys():
                globals()[varName].update({"data": v})
            else:
                varName = i.upper()
                globals()[varName] = v
        return True
    return False

An attempt will be made to convert the data to the type indicated in the constant, so
the string '10' entered by the user will become an integer.

This module also provide you for Url and IP classes; If you want to use them, you
must import these classes from this module and use as a typeOf:

from settings import IniSettings, Url, IP

Is important to know that if initial data is not None this will be the default value for this costant
and settings will not ask the user to enter this data, but if you also provide same option on the config file
the default data will be overwritten.
"""

import configparser
import logging
from typing import Any
from urllib.parse import urlparse
import ipaddress
from pathlib import Path

logger = logging.getLogger(name=__name__)


class Url(str):
    def __new__(cls, value):
        return super(Url, cls).__new__(cls=cls, object=value)

class IP(ipaddress._BaseAddress):
    def __new__(cls, value):
        return super(IP, cls).__new__(cls=cls)

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
            "telegram": [{"name": "api_key", "typeOf": str, "data": None}],
            "shinobi": [
                {"name": "api_key", "typeOf": bool, "data": True},
                {"name": "group_key", "typeOf": str, "data": None},
                {"name": "base_url", "typeOf": str, "data": None},
                {"name": "port", "typeOf": int, "data": 8080},
                {"name": "userIdes", "typeOf": list, "data": [11,56,9]},
            ],
        }
        - configFile (Path): The path to config file.
            Default is None.

        Note: first key is the section, then a list of dictionaries with the name of the
        option, the type of the option and the default value.
        If you need you can add optional data in the config file just adding options or/and sections
        in the config file, the class will read them and check their type.
        All optional data (for witch type of is not specified) will be read as string
        and if isdigit() is applicable without errors will be converted to int.
        Is not possible to have a list as optional data; if you need it you must add a
        required data with typeOf list.
        """
        self._neededSettings = neededSettings
        self._configFile = configFile
        self._config = configparser.ConfigParser(
            inline_comment_prefixes=("#", ";"),
            comment_prefixes=("#", ";"),
            empty_lines_in_values=False,
            allow_no_value=False,
        )
        if not self._iniCheck(settings=self._neededSettings):
            raise SystemExit

    def _iniCheck(self, settings) -> bool:
        try:
            self._config.read(filenames=self._configFile)
            logger.info(msg='Ok found settings.ini, analyzing...')
            for section in settings:
                for option in settings[section]:
                    if option["data"] == None:
                        if not self._config.has_option(section=section, option=option["name"]):
                            try:
                                value = input(f"Required {section} {option['name']} not found in your settings file, please insert it: ")
                            except Exception as e:
                                logger.error(
                                    msg=f"Error asking input in console: {e}; please add it and restart..."
                                )
                                return False
                            if self._verifyTypeOf(value=value, typeOf=option["typeOf"], name=option["name"]) == None:
                                logger.error(
                                    msg=f"TypeOf check failed in {section} {option['name']} {value}"
                                )
                                return False
                            if not self._config.has_section(section=section):
                                self._config.add_section(section=section)
                            self._config.set(
                                    section=section,
                                    option=option["name"],
                                    value=str(object=value),
                                )
            logger.info(msg="INI check terminated")
            with open(file=self._configFile, mode="w") as configfile:
                self._config.write(fp=configfile)
            return True
        except Exception as error:
            logger.error(msg=f"An error {error} occurred finding or loading or parsing settings")
            return False

    def iniRead(self) -> tuple[Any, ...] | bool | None:
        """
        Read all (required and optional) data from the configuration file, checking their type.
        """
        returnedSettings: dict[str, dict] = {}
        for configSection in self._config.sections():
            for configProperty in self._config.options(section=configSection):
                configValue = self._config.get(
                    section=configSection, option=configProperty
                )
                # TODO implement a check for list type (a string with comma separated values) and do something
                value: Any = None
                redundant: bool = False
                if configSection in self._neededSettings:
                    requiredList = self._neededSettings[configSection]
                    for i in requiredList:
                        if i["name"] == configProperty:
                            logger.debug(
                                msg=f"{configSection} {configProperty} found in your settings file..."
                            )
                            # checking of type and returning the converted and right value
                            result = self._verifyTypeOf(value=configValue, typeOf=i["typeOf"], name=configProperty)
                            if result is not None:
                                if result != i["data"]:
                                    value = result
                                    if i["data"] is not None:
                                        logger.debug(msg=f"{configSection} {configProperty} {value} is different from the default, overriding...")
                                else:
                                    redundant = True
                                    logger.warning(msg=f"{configSection} {configProperty} is the same as the default, resulting redundant, consider to remove it!")
                            else:
                                logger.error(msg=f"TypeOf check failed in {configSection} {configProperty} {configValue}")
                                return False
                            break
                if value is None and not redundant:
                    if configValue == "":
                        continue
                    value = configValue
                    logger.debug(
                        msg=f"{configSection} {configProperty} {value} defined in your settings file is not required, setting up as optional..."
                    )
                if not redundant:
                    if configSection not in returnedSettings:
                        returnedSettings[configSection] = {}
                    if configProperty not in returnedSettings[configSection]:
                        returnedSettings[configSection].update({configProperty: value})
        if returnedSettings:
            # print(returnedSettings)
            return self._buildSettings(settings=returnedSettings)
        return False

    def _verifyTypeOf(self, value: str, typeOf: type, name: str) -> None | Any:
        """Verify and optionally convert the type of a value."""
        if typeOf == Url:
            # if self._verifyUrl(url=value):
            #     return value
            try:
                urlparse(url=value)
                logger.debug(msg=f"URL {value} is a valid URL...")
                # return all([result.scheme, result.netloc])
                return value
            except ValueError:
                logger.error(msg=f"URL {value} is not a valid URL...")
        elif typeOf == IP:
            try:
                ipaddress.ip_address(address=value)
                logger.debug(msg=f"IP {value} is a valid IP...")
                return value
            except ValueError:
                logger.error(msg=f"IP {value} is not a valid IP...")
        elif typeOf == bool:
            if isinstance(value, bool):
                return value
            else:
                if value.lower() == "false" or value == "0":
                    return False
                elif value.lower() == "true" or value == "1":
                    return True
        elif typeOf == list:
            temp: list[Any] = value.split(sep=",")
            convertedValue = []
            for i in temp:
                if i == "":
                    continue
                elif i.isdigit():
                    convertedValue.append(int(i))
                else:
                    convertedValue.append(i)
            if len(convertedValue) > 0:
                return convertedValue
        else:
            if value != "":
                if name == "loglevel":
                    if not self._verifyLogLevel(loglevel=value):
                        return None
                convertedValue = typeOf(value)
                return convertedValue
        return None

    def _verifyUrl(self, url: str) -> bool:
        """Verify if the given URL is valid."""
        try:
            result = urlparse(url=url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _verifyLogLevel(self, loglevel) -> bool:
        all_levels = [logging.getLevelName(level=level) for level in range(0, 101)]
        if loglevel.upper() in all_levels:
            return True
        return False

    def _buildSettings(self, settings: dict) -> tuple:
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
                logger.info(msg=f"Assigning {sub_value} to global variable {variable_name}...")
                varsDict[variable_name] = sub_value
        return tuple(varsDict.items())


if __name__ == "__main__":
    raise SystemExit
