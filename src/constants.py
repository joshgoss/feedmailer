import os
from pathlib import Path

APP_NAME = 'feed-mailer'
CONFIG_DIR = os.path.join(str(Path.home()), '.' + APP_NAME)
DB_LOCATION = os.path.join(CONFIG_DIR, 'feed-mailer.db')
CONFIG_LOCATION = os.path.join(CONFIG_DIR, 'feed-mailer.cfg')

DEFAULT_CONFIG = {
    'email': "",
    'digest': "No",
    'smtp_email': "",
    'smtp_pass': "",
    'smtp_ssl': "Yes",
    'smtp_port': "587"
}
