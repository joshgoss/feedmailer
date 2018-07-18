import argparse
import configparser
from dateutil import parser
import feedparser
import html2text
import logging
import os
import sys
from pathlib import Path

from feedmailer import database
from feedmailer.mailer import Mailer

APP_NAME='feedmailer'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USER_DIR = os.path.join(str(Path.home()), '.feedmailer')
DEFAULT_CONFIG_FILE = os.path.join(DATA_DIR, 'defaults.cfg')
DEFAULT_SENDER_NAME = 'Feed Mailer'

TEMPLATES = {
    'plain': {
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


class ConfigError(Exception):
    pass


class App:
    def __init__(self,
                 name='feedmailer',
                 config_dir=USER_DIR,
                 db_name=APP_NAME + '.db',
                 log_name=APP_NAME + '.log',
                 config_name=APP_NAME + '.cfg'
    ):
        self.name = 'feedmailer'
        self.config_dir = config_dir
        self.config_name = config_name
        self.db_name = db_name
        self.log_name= log_name

        self.db = None
        self.config = None
        self.logger = None

    def __init_config(self):
        user_config_file = os.path.join(self.config_dir, self.config_name)
        config_parser = configparser.ConfigParser()

        if not os.path.exists(self.config_dir):
            self.logger.debug("Creating config directory...")
            os.makedirs(self.config_dir)

        # write a default config if one does not exist yet
        if not os.path.exists(user_config_file):
            config_parser.read_file(open(DEFAULT_CONFIG_FILE))

            with open(user_config_file, 'w') as config:
                config_parser.write(config)

                self.logger.info("A default config was created at '%s'. SMTP settings will need to be set before delivering can work." % (user_config_file,))

        config_parser.read(user_config_file)

        if config_parser['DEFAULT']['content_type'] not in list(TEMPLATES.keys()):
            self.logger.error("Invalid content type found within config")
            raise ConfigError("Invalid content_type provided")

        return {
            'email': config_parser['DEFAULT']['email'],
            'content_type': config_parser['DEFAULT']['content_type'],
            'digest': config_parser['DEFAULT'].getboolean('digest'),
            'smtp_user': config_parser['DEFAULT']['smtp_user'],
            'smtp_host': config_parser['DEFAULT']['smtp_host'],
            'smtp_auth': config_parser['DEFAULT'].getboolean('smtp_auth'),
            'smtp_ssl': config_parser['DEFAULT'].getboolean('smtp_ssl'),
            'smtp_password': config_parser['DEFAULT']['smtp_password'],
            'smtp_port': config_parser['DEFAULT'].getint('smtp_port')
        }

    def __init_db(self):
        db = database.connect(os.path.join(self.config_dir, self.db_name))
        database.setup_db(db)
        return db

    def __init_logger(self):
        logger = logging.getLogger(APP_NAME)
        logger.setLevel(logging.DEBUG)
        log_file = os.path.join(USER_DIR, self.log_name)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def __init_cmd_parser(self):
        parser = argparse.ArgumentParser(
            prog=self.name,
            description="Deliver feeds by email"
        )

        subparsers = parser.add_subparsers(help='commands', dest='command')

        # Add command
        parser_add = subparsers.add_parser('add', help='Add a new feed subscription')
        parser_add.add_argument('url', type=str, help='Location of rss feed')
        parser_add.add_argument('--title', dest='title', help='Specify custom title for feed')
        parser_add.add_argument('--email', type=str, dest='email', help='The email address to deliver the feed to')

        parser_add.add_argument(
            '--digest',
            action='store_true',
            dest='digest',
            help='Send items as a digest instead of individually'
        )

        parser_add.set_defaults(
            title=None,
            digest=False,
            max_age=None,
            email=self.config.get('email', None)
        )

        # List command
        parser_list = subparsers.add_parser('list', help='List all subscriptions')

        # List feeds command
        parser_list_feeds = subparsers.add_parser('list-feeds', help='List all feeds')

        # Remove command
        parser_remove = subparsers.add_parser('remove', help='Remove a feed subscription')
        parser_remove.add_argument('subscription_id', type=int, help="id of subscription")
        # Refresh command
        parser_refresh = subparsers.add_parser('refresh', help='Fetch latest articles and store them for mailing')
        parser_refresh.add_argument('feed_id', type=int, nargs='?', help='id of feed')

        # Deliver command
        parser_deliver = subparsers.add_parser(
            'deliver',
            help='Email latest articles'
        )

        parser_deliver.add_argument(
            'subscription_ids',
            type=int,
            nargs='+',
            help='ids of subscriptions to deliver'
        )

        parser_deliver.add_argument(
            '--pretend',
            action='store_true',
            dest='pretend',
            help='Don\'t actually mail anything, instead print out what would be delivered. Useful for debugging.'
        )

        parser_deliver.set_defaults(pretend=False)

        return parser

    # convert feedparser entry to db schema of an article
    def __entry_to_article(self, entry):
        published = None
        author = None
        h = html2text.HTML2Text()
        h.ignore_links = True

        if 'published' in entry and entry.published:
            published = parser.parse(entry.published)

        if 'author' in entry and entry.author:
            author = entry.author

        return {
            'title': h.handle(entry.title).strip(),
            'url': entry.link,
            'author': author,
            'description': h.handle(entry.description).strip(),
            'published_at': published
        }

    def __handle_add(self, args):
        if not args.email:
            self.logger.error("An email must be provided either within the config file or as an argument to the 'add' command." )
            return

        results = database.find_subscriptions(
            self.db,
            url=args.url,
            email=args.email
        )

        if len(results):
            self.logger.error("This feed is already being delivered to the email provided.")
            return

        data = feedparser.parse(args.url)

        if data.bozo:
            self.logger.error('Unable to add an invalid feed location.')
            return

        database.add_subscription(self.db,
                                  url=args.url,
                                  title=args.title or data['feed']['title'],
                                  email=args.email,
                                  digest=args.digest,
                                  max_age=args.max_age)
    def __handle_list(self):
        subscriptions = database.find_subscriptions(self.db)

        if not len(subscriptions):
            print("No subscriptions added yet")
            return

        for s in subscriptions:
            print("%d. \"%s\" -> %s" % (s['subscription_id'], s['title'], s['email']))


    def __handle_list_feeds(self):
        feeds = database.find_feeds(self.db)

        if not len(feeds):
            print('No feeds added yet. Feeds are automatically created through subscriptions.')

        for f in feeds:
            print("%d. \"%s\"" % (f['feed_id'], f['title']))


    def __handle_refresh_feed(self, args):
        feed = database.find_feed_by_id(self.db, args.feed_id)

        if not feed:
            self.logger.error("No feed exists with that id.")
            return

        data = feedparser.parse(feed['url'])

        articles = list(map((lambda a: self.__entry_to_article(a)), data.entries))
        num_added = database.refresh_articles(self.db, args.feed_id, articles)

        if num_added > 0:
            self.logger.info("Found %d new article(s) for '%s'" % (num_added, feed['title']))
        else:
            self.logger.info("No new articles found for '%s'." % feed['title'])

        return num_added

    def __handle_remove(self, args):
        subscription = database.find_subscription_by_id(
            self.db,
            args.subscription_id
        )

        if not subscription:
            self.logger.error("No subscription found with the id of %d" % (args.subscription_id,))
            return

        database.remove_subscription(self.db, args.subscription_id)

    def __handle_refresh_all(self):
        feeds = database.find_feeds(self.db)
        num_added = 0

        for f in feeds:
            data = feedparser.parse(f['url'])
            articles = list(map((lambda a: self.__entry_to_article(a)), data.entries))
            num_added += database.refresh_articles(self.db, f['feed_id'], articles)

        self.logger.info("%d new articles found in total" % num_added)

        return num_added

    def __handle_deliver_subscriptions(self, args):
        for subscription_id in args.subscription_ids:
            subscription = database.find_subscription_by_id(
                self.db,
                subscription_id
            )

            config = self.config

            if not subscription:
                self.logger.error("No subscription exists with id of %d" % subscription_id)
                return

            articles = database.find_articles_for_delivery(
                self.db,
                subscription_id
            )

            if not articles:
                self.logger.error("No articles to deliver for subscription  %d" % (subscription_id,))
                continue

            if args.pretend:
                for a in articles:
                    print(
                        "%d. %s - %s (%s)\n" %
                        (a['article_id'], subscription['title'], a['title'], a['url'])
                    )
                continue

            database.set_attempted_delivery_at(self.db, subscription_id)

            mailer = Mailer(
                host = config['smtp_host'],
                port = config['smtp_port'],
                user = config['smtp_user'],
                password = config['smtp_password'],
                auth = config['smtp_auth'],
                ssl = config['smtp_ssl'],
                to_email = subscription['email']
            )

            content_type = self.config['content_type']

            if subscription['digest']:
                mailer.send_digest(
                    feed_title = subscription['title'],
                    articles = articles,
                    content_type = self.config['content_type'],
                    template = TEMPLATES[content_type]['digest_template']
                )
            else:
                for a in articles:
                    mailer.send_article(
                        feed_title = subscription['title'],
                        article = a,
                        content_type = self.config['content_type'],
                        template = TEMPLATES[content_type]['article_template']
                    )

    def run(self, args=None):
        self.logger = self.__init_logger()
        self.config = self.__init_config()
        self.db = self.__init_db()
        parser = self.__init_cmd_parser()
        parsed_args = parser.parse_args(args)
        results = None

        if parsed_args.command == 'add':
            results = self.__handle_add(parsed_args)
        elif parsed_args.command == 'list':
            results = self.__handle_list()
        elif parsed_args.command == 'list-feeds':
            results = self.__handle_list_feeds()
        elif parsed_args.command == 'remove':
            results = self.__handle_remove(parsed_args)
        elif parsed_args.command == 'deliver':
            results = self.__handle_deliver_subscriptions(parsed_args)
        elif parsed_args.command == 'refresh':
            if parsed_args.feed_id:
                results = self.__handle_refresh_feed(parsed_args)
            else:
                results = self.__handle_refresh_all()
        else:
            parser.print_help()

        self.db.close()

        return results
