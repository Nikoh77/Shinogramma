"""
This is a simple settings config parser, importer and filler module by Nikoh version 1.0.0
On main/calling module, the required data for running this software, are defined
as a global scope constants.
It is important to follow this syntax defining the constants:

SET_SECTION_OPTION: dict = {"data": None, "typeOf": type, "required": True/False}


For example, if you want to have following data in the configuration file:

[BANANAS]
number_of = 10
color = green

We need to add the following constants in the main module:

SET_BANANAS_NUMBER_OF: dict = {"data": None, "typeOf": int, "required": True}
SET_BANANAS_COLOR: dict = {"data": None, "typeOf": str, "required": True}

When starting, settings will ask the user to enter the number and color of bananas...

It is important to note that the value of 'data' key of all these constants is updated
at runtime from None to values read from the configuration file by buildSettings function.
Starting from these constants the dictionary `neededSettings` is created with this function
that you must call in the main module, after the constants definition:

{i: globals()[i] for i in globals().keys() if i.startswith("SET_")}

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
            if i in globals().keys():
                globals()[i].update({"data": v["data"]})
        return True
    return False

An attempt will be made to convert the data to the type indicated in the constant, so
the string '10' entered by the user will become an integer.

This module also provide you for Url, LogLevel, IP and TustList classes; If you want to use them, you
must import these classes from this module and use as a typeOf:

from settings import IniSettings, Url, IP, LogLevel, TrustList

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
import json
import socket

logger = logging.getLogger(name=__name__)


class IP:
    def __init__(self, ip: str):
        self._ip: ipaddress.IPv4Address | ipaddress.IPv6Address = self._verify(ip=ip)

    def __str__(self) -> str:
        return str(object=self._ip)

    def __repr__(self) -> str:
        return str(object=self._ip)

    def __eq__(self, other):
        if isinstance(other, str):
            return self._ip == other
        return False

    def _verify(self, ip) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        return ipaddress.ip_address(address=ip)

    @property
    def ip(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        return self._ip

    @ip.setter
    def ip(self, value: str):
        self._ip = self._verify(ip=value)


class Url:
    def __init__(self, url):
        self._url, self.ip = self._verify(url=url)

    def __str__(self) -> str:
        # return self._url
        return f"{self._url}"

    def __repr__(self) -> str:
        return f"{self._url}"

    def __eq__(self, other):
        if isinstance(other, str):
            return self._url == other
        return False

    def _verify(self, url: str) -> tuple[str, IP]:
        if not self.is_ip(address=url) and not url.isdigit():
            parsed = urlparse(url=url)
            if parsed.scheme == "":
                hostname = parsed.path
            else:
                hostname = parsed.netloc
            if hostname is not None:
                temp = socket.gethostbyname(hostname)
                if temp:
                    ip = IP(ip=temp)
                    return (url, ip)
        raise ValueError(f"Unable to resolve URL {url}")

    def is_ip(self, address):
        try:
            ipaddress.ip_address(address=address)
            return True
        except ValueError:
            return False

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._level, self.ip = self._verify(url=value)


class TrustList(dict):
    def __init__(self, trustlist: str):
        super().__init__(self._verify(trustlist=trustlist))

    def _verify(self, trustlist: str):
        try:
            trustlistDict = json.loads(s=trustlist)
        except json.JSONDecodeError:
            raise TypeError("trustlist must be a valid JSON string")
        if not isinstance(trustlistDict, dict):
            raise TypeError("trustlist must be a flat dictionary")
        returnedDict: dict[str, Url | IP] = {}
        for key, value in trustlistDict.items():
            temp: Url | IP | None = None
            if not isinstance(key, str) and not isinstance(value, str):
                raise TypeError("The Name of server in trustlist and his Url (or IP) must be strings")
            try:
                temp = IP(ip=value)
            except Exception:
                try:
                    temp = Url(url=value)
                except Exception as e:
                    logger.warning(msg=f"Error with URL in trustlist: {value}, error: {str(object=e)}")
            finally:
                if temp:
                    returnedDict[key] = temp
        if returnedDict:
            return returnedDict
        return {}

    @property
    def trustlist(self):
        return self

    @trustlist.setter
    def trustlist(self, value):
        self.clear()
        self.update(self._verify(trustlist=value))


class LogLevel:
    def __init__(self, level: str):
        self._level = self._verify(level=level.upper())

    def __str__(self) -> str:
        return self._level

    def __repr__(self) -> str:
        return self._level

    def __eq__(self, other):
        if isinstance(other, str):
            return self._level == other.upper()
        return False

    def _verify(self, level):
        if level not in [logging.getLevelName(level=level) for level in range(0, 101)]:
            raise ValueError(f"Invalid log level: {level}")
        return level

    @property
    def level(self):
        return self._level.upper()

    @level.setter
    def level(self, value):
        self._level = self._verify(level=value.upper())


class IniSettings:
    """
    This class object is a simple settings config parser, importer and filler.
    """
    def __init__(
        self,
        neededSettings: dict[str, dict[str, Any]],
        configFile: Path,
    ) -> None:
        """
        Constructor of the class.

        Arguments:
        - neededSettings (dict[str, list]): The required data, like this:
        neededSettings: dict[str, dict[str, Any]] = {
            "SET_TELEGRAM_APIKEY": {"data": "726f7dff3U", "typeOf": str, "required": True},
            "SET_GAMESERVERS_INTERFACE": {"data": "127.0.0.1", "typeOf": IP, "required": True},
            "SET_GAMESERVERS_MAX": {"data": None, "typeOf": int, "required": False}
        }
        - configFile (Path): The path to config file.
            Default is None.
        """
        self._neededSettings = neededSettings
        self._configFile = configFile
        self._config = configparser.ConfigParser(
            inline_comment_prefixes=("#", ";"),
            comment_prefixes=("#", ";"),
            empty_lines_in_values=False,
            allow_no_value=False,
        )
        if not self._iniCheck():
            raise SystemExit

    def _iniCheck(self) -> bool:
        try:
            self._config.read(filenames=self._configFile)
            logger.info(msg='Ok found settings.ini, analyzing...')
            for settingName, settingValue in self._neededSettings.items():
                section = settingName.split(sep="_")[1]
                option = "_".join(settingName.split(sep="_")[2:]).lower()
                if settingValue["data"] == None and settingValue["required"] == True:
                    if not self._config.has_option(section=section, option=option):
                        try:
                            value = input(f"Required {section} {option} not found in your settings file, please insert it: ")
                        except Exception as e:
                            logger.error(
                                msg=f"Error asking input in console: {e}; please add it and restart..."
                            )
                            return False
                        if self._verifyTypeOf(value=value, typeOf=settingValue["typeOf"], name=option) == None:
                            logger.error(
                                msg=f"TypeOf check failed in {section} {option} {value}"
                            )
                            return False
                        if not self._config.has_section(section=section):
                            self._config.add_section(section=section)
                        self._config.set(
                                section=section,
                                option=option,
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
        for configSection in self._config.sections():
            for configProperty, configValue in self._config.items(section=configSection):
                var = f"SET_{configSection.upper()}_{configProperty.upper()}"
                if var in self._neededSettings:
                    logger.debug(
                        msg=f"{configSection} {configProperty} found in your settings file..."
                    )
                    # checking of type and returning the converted and right value
                    result = self._verifyTypeOf(value=configValue, typeOf=self._neededSettings[var]["typeOf"], name=configProperty)
                    if result is not None:
                        if result != self._neededSettings[var]["data"]:
                            if self._neededSettings[var]["data"] is not None:
                                logger.debug(msg=f"{configSection} {configProperty} {configValue} is different from the default, overriding...")
                            self._neededSettings[var]["data"] = result
                        else:
                            logger.warning(msg=f"{configSection} {configProperty} is the same as the default, resulting redundant, consider to remove it!")
                    else:
                        logger.error(msg=f"TypeOf check failed in {configSection} {configProperty} {configValue}")
                        return False
                else:
                    logger.warning(msg=f"Unknow {configSection} {configProperty} found in your settings file, ignoring...")
        if self._neededSettings:
            return tuple(self._neededSettings.items())
        return False

    def _verifyTypeOf(self, value: str, typeOf: type, name: str) -> None | Any:
        """Verify and optionally convert the type of a value."""
        try:
            convertedValue: Any
            if typeOf == bool:
                if isinstance(value, bool):
                    return value
                else:
                    if value.lower() == "false" or value == "0":
                        return False
                    elif value.lower() == "true" or value == "1":
                        return True
            elif typeOf == list:
                convertedValue = []
                for i in value.split(sep=","):
                    if i == "":
                        continue
                    elif i.isdigit():
                        convertedValue.append(int(i))
                    else:
                        convertedValue.append(i)
                if len(convertedValue) > 0:
                    return convertedValue
            elif typeOf == dict:
                convertedValue = json.loads(s=value)
                return convertedValue
            else:
                if value != "":
                    return typeOf(value)
        except Exception as e:
            logger.error(msg=f"Error verifyng {name} or converting to {typeOf}: {e}")
        return None

if __name__ == "__main__":
    raise SystemExit
