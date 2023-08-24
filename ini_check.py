#This module is needed by the main and takes care of the control and generation of the ShinotifyTB configuration file through input requests.

import configparser

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
            if option == 'chat_id': # If chat_id (comma separated) are defined
                value = [int(id.strip()) for id in value.split(',')] # I turn them into a list
            data[option] = value
        settings[section] = data
    if settings:
        return True
    else:
        return False