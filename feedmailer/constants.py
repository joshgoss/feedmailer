import os
from pathlib import Path

APP_NAME='feedmailer'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USER_CONFIG_DIR = os.path.join(str(Path.home()), '.' + APP_NAME)
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, 'feedmailer.cfg')
USER_DB_FILE = os.path.join(USER_CONFIG_DIR, 'feedmailer.db')
DEFAULT_CONFIG_FILE = os.path.join(DATA_DIR, 'defaults.cfg')
DEFAULT_SENDER_NAME = 'Feed Mailer'

CONTENT_TYPES = ['text', 'html']

TEMPLATES = {
    'text': {
        'article_template': os.path.join(DATA_DIR, 'article.txt.jinja'),
        'digest_template': os.path.join(DATA_DIR, 'digest.txt.jinja'),
        'content_type': 'plain'
    },
    'html': {
         'article_template': os.path.join(DATA_DIR, 'article.html.jinja'),
        'digest_template': os.path.join(DATA_DIR, 'digest.html.jinja'),
        'content_type': 'html'
    }
}
