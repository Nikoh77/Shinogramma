import configparser
import json

settings = {}

def iniCheck(needed,config_file):
    config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read(config_file)
    for section in needed:
        if not config.has_section(section):
            print(f'Needed section {section} does not existin your INI file, creating...')
            config.add_section(section)
        for option in needed[section]:
            if config.has_option(section,option):
                print(f'Ok, {section} {option} found.')
            else:
                config.set(
                    section,
                    option,
                    input(f'Please insert the {section} {option}: ')
                )
    with open(config_file, 'w') as configfile:
        config.write(configfile)
    # Read INI file
    for section in config.sections():
        options = config.items(section)
        data = {}
        for option, value in options:
            data[option] = value
        settings[section] = data
    #printJson(settings, "INI settings") # Only for debug purpouse, enable line below to stamp stdout ini settings
    return True      