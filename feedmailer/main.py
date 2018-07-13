import configparser
import os

from feedmailer import cmd, constants, database


class ConfigError(Exception):
    pass


class Session:
    def __init__(self, **kwargs):
        self.app_name = constants.APP_NAME,
        self.db = kwargs['db']
        # default configuration
        self.config = kwargs['config']

def __parse_config(config):
    if config['DEFAULT']['content_type'] not in constants.CONTENT_TYPES:
        raise ConfigError("Invalid content_type provided")

    return {
        'email': config['DEFAULT']['email'],
        'content_type': config['DEFAULT']['content_type'],
        'digest': config['DEFAULT'].getboolean('digest'),
        'smtp_user': config['DEFAULT']['smtp_user'],
        'smtp_host': config['DEFAULT']['smtp_host'],
        'smtp_auth': config['DEFAULT'].getboolean('smtp_auth'),
        'smtp_ssl': config['DEFAULT'].getboolean('smtp_ssl'),
        'smtp_password': config['DEFAULT']['smtp_password'],
        'smtp_port': config['DEFAULT'].getint('smtp_port')
    }


if not os.path.exists(constants.USER_CONFIG_DIR):
    os.makedirs(constants.USER_CONFIG_DIR)

config = configparser.ConfigParser()
config.read_file(open(constants.DEFAULT_CONFIG_FILE))

# write a default config if one does not exist yet
if not os.path.exists(constants.USER_CONFIG_FILE):
    with open(constants.USER_CONFIG_FILE, 'w') as config_file:
        config.write(config_file)

        print("A default config was created at '%s'. SMTP settings will need to be set before delivering can work." % constants.USER_CONFIG_FILE)

config.read(constants.USER_CONFIG_FILE)

conn = database.connect(constants.USER_DB_FILE)
session = Session(config=__parse_config(config), db=conn)

database.setup_db(session.db)
cmd.run(session)

session.db.close()
