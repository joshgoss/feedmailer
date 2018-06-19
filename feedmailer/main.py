import configparser
import os
from pathlib import Path

from feedmailer import cmd
from feedmailer import database

APP_NAME='feedmailer'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USER_CONFIG_DIR = os.path.join(str(Path.home()), '.' + APP_NAME)
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, 'feedmailer.cfg')
USER_DB_FILE = os.path.join(USER_CONFIG_DIR, 'feedmailer.db')
DEFAULT_CONFIG_FILE = os.path.join(DATA_DIR, 'defaults.cfg')


class ConfigError(Exception):
    pass


class Session:
    def __init__(self, **kwargs):
        # database connection
        self.app_name = APP_NAME,
        self.db = kwargs['db']
        # default configuration
        self.config = kwargs['config']

def __parse_config(config):
    return {
        'email': config['DEFAULT']['email'],
        'digest': config['DEFAULT'].getboolean('digest'),
        'smtp_email': config['DEFAULT']['smtp_email'],
        'smtp_ssl': config['DEFAULT'].getboolean('smtp_ssl'),
        'smtp_password': config['DEFAULT']['smtp_password'],
        'smtp_port': config['DEFAULT'].getint('smtp_port')
    }

if not os.path.exists(USER_CONFIG_DIR):
    os.makedirs(USER_CONFIG_DIR)

config = configparser.ConfigParser()
config.read_file(open(DEFAULT_CONFIG_FILE))
config.read(USER_CONFIG_FILE)

# write a default config if one does not exist yet
if not os.path.exists(USER_CONFIG_FILE):
    with open(USER_CONFIG_FILE, 'w') as config_file:
        config.write(config_file)

        print("A default config was created at '%s'. SMTP settings will need to be set before delivering can work." % USER_CONFIG_FILE)

conn = database.connect(USER_DB_FILE)
session = Session(config=__parse_config(config), db=conn)

database.setup_db(session.db)
cmd.run(session)

session.db.close()
