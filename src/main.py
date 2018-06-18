import configparser
import os

import cmd
import constants
import database


class ConfigError(Exception):
    pass


class Session:
    def __init__(self, **kwargs):
        # database connection
        self.db = kwargs['db']
        # default configuration
        self.config = kwargs['config']

def __parse_config(config):
    for key in config['DEFAULT']:
        if key not in list(constants.DEFAULT_CONFIG.keys()):
            raise ConfigError("Unknown configuration key '%s'" % key)

    return {
        'email': config['DEFAULT']['email'],
        'digest': config['DEFAULT'].getboolean('digest'),
        'smtp_email': config['DEFAULT']['smtp_email'],
        'smtp_ssl': config['DEFAULT'].getboolean('smtp_ssl'),
        'smtp_port': config['DEFAULT'].getint('smtp_port')
    }


if __name__ == "__main__":
    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR)

    config = configparser.ConfigParser()
    config['DEFAULT'] = constants.DEFAULT_CONFIG

    # write a default config if one does not exist yet
    if not os.path.exists(constants.CONFIG_LOCATION):
        with open(constants.CONFIG_LOCATION, 'w') as config_file:
            config.write(config_file)

            print("A default config was created at '%s'. SMTP settings will need to be set before delivering can work." % constants.CONFIG_LOCATION)


    config.read(constants.CONFIG_LOCATION)

    conn = database.connect(constants.DB_LOCATION)
    session = Session(config=__parse_config(config), db=conn)

    database.setup_db(session.db)
    cmd.run_cli(session)

    session.db.close()
