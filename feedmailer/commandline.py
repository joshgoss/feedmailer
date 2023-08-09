import argparse
import configparser
from dateutil import parser
import feedparser
import html2text
import logging
import os
from pathlib import Path

from feedmailer import database, crud
from feedmailer.mailer import Mailer
from feedmailer.types import Article

APP_NAME = 'feedmailer'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
APP_DIR = os.environ.get("FEEDMAILER_APP_DIR", os.path.join(
    str(Path.home()), '.feedmailer'))
APP_CONFIG_FILE = os.path.join(APP_DIR, APP_NAME + '.cfg')
APP_LOG_FILE = os.path.join(APP_DIR, APP_NAME + '.log')
APP_DB_FILE = os.path.join(APP_DIR, APP_NAME + '.db')
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


class Session():
    def __init__(self, **kwargs):
        self.config = kwargs['config']
        self.db = kwargs['db']
        self.logger = kwargs['logger']


def init_config():
    config_parser = configparser.ConfigParser()

    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR)

    # write a default config if one does not exist yet
    if not os.path.exists(APP_CONFIG_FILE):
        config_parser.read_file(open(DEFAULT_CONFIG_FILE))

        with open(APP_CONFIG_FILE, 'w') as config:
            config_parser.write(config)

            print(
                f"A default config was created at '{APP_CONFIG_FILE}'. SMTP settings will need to be set before delivering can work.")

    config_parser.read(APP_CONFIG_FILE)

    if config_parser['DEFAULT']['content_type'] not in list(TEMPLATES.keys()):
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


def init_db():
    db = database.connect(APP_DB_FILE)
    database.setup_db(db)
    return db


def init_logger():
    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR)

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(APP_LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def init_arg_parser(session: Session):
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Deliver feeds by email"
    )

    subparsers = parser.add_subparsers(help='commands', dest='command')

    # Add command
    parser_add = subparsers.add_parser(
        'add', help='Add a new feed subscription')
    parser_add.add_argument('url', type=str, help='Location of rss feed')
    parser_add.add_argument('--title', dest='title',
                            help='Specify custom title for feed')
    parser_add.add_argument('--email', type=str, dest='email',
                            help='The email address to deliver the feed to')
    parser_add.add_argument('--desc-length', type=int, dest='desc_length',
                            help='Change max length for article descriptions')

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
        desc_length=300,
        email=session.config.get('email', None)
    )

    # List command
    parser_list = subparsers.add_parser('list', help='List all subscriptions')

    # List feeds command
    parser_list_feeds = subparsers.add_parser(
        'list-feeds', help='List all feeds')

    # Remove command
    parser_remove = subparsers.add_parser(
        'remove', help='Remove a feed subscription')
    parser_remove.add_argument(
        'subscription_id', type=int, help="id of subscription")
    # Refresh command
    parser_refresh = subparsers.add_parser(
        'refresh', help='Fetch latest articles and store them for mailing')
    parser_refresh.add_argument(
        'feed_id', type=int, nargs='?', help='id of feed')

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
def entry_to_article(entry) -> Article:
    published = None
    author = None
    h = html2text.HTML2Text()
    h.ignore_links = True

    if 'published' in entry and entry.published:
        published = parser.parse(entry.published)

    if 'author' in entry and entry.author:
        author = entry.author

    return Article(
        title=h.handle(entry.title).strip(),
        url=entry.link,
        author=author,
        description=h.handle(entry.description).strip(),
        published_at=published
    )


def add_feed(session: Session, args: argparse.Namespace):
    if not args.email:
        session.logger.error(
            "An email must be provided either within the config file or as an argument to the 'add' command.")
        return

    results = crud.find_subscriptions(
        session.db,
        url=args.url,
        email=args.email
    )

    if len(results):
        session.logger.error(
            "This feed is already being delivered to the email provided.")
        return

    data = feedparser.parse(args.url)

    if data.bozo:
        session.logger.error('Unable to add an invalid feed location.')
        return

    crud.add_subscription(session.db,
                          url=args.url,
                          title=args.title or data['feed']['title'],
                          email=args.email,
                          digest=args.digest,
                          desc_length=args.desc_length,
                          max_age=args.max_age)


def list_subscriptions(session: Session):
    subscriptions = crud.find_subscriptions(session.db)

    if not len(subscriptions):
        print("No subscriptions added yet")
        return

    for s in subscriptions:
        print(f"{s.subscription_id}. \"{s.title}\"-> {s.email}")


def list_feeds(session: Session):
    feeds = crud.find_feeds(session.db)

    if not len(feeds):
        print('No feeds added yet. Feeds are automatically created through subscriptions.')

    for f in feeds:
        print(f"{f.feed_id}. \"{f.title}\" - {f.url}")


def refresh_feed(session: Session, args: argparse.Namespace):
    feed = crud.find_feed_by_id(session.db, args.feed_id)

    if not feed:
        session.logger.error("No feed exists with that id.")
        return

    data = feedparser.parse(feed.url)

    articles = list(map((lambda a: entry_to_article(a)), data.entries))
    num_added = crud.refresh_articles(session.db, args.feed_id, articles)

    if num_added > 0:
        session.logger.info(
            f"Found {num_added} new article(s) for '{feed.title}'")
    else:
        session.logger.info(f"No new articles found for '{feed.title}'.")

    return num_added


def remove_subscription(session: Session, args: argparse.Namespace):
    subscription = crud.find_subscription_by_id(
        session.db,
        args.subscription_id
    )

    if not subscription:
        session.logger.error(
            f"No subscription found with the id of {args.subscription_id}")
        return

    crud.remove_subscription(session.db, args.subscription_id)


def refresh_feeds(session: Session):
    feeds = crud.find_feeds(session.db)
    num_added = 0

    for f in feeds:
        data = feedparser.parse(f.url)
        articles = list(map((lambda a: entry_to_article(a)), data.entries))
        num_added += crud.refresh_articles(session.db, f.feed_id, articles)

    session.logger.info(f"{num_added} new articles found in total")

    return num_added


def deliver_subscriptions(session: Session, args: argparse.Namespace):
    for subscription_id in args.subscription_ids:
        subscription = crud.find_subscription_by_id(
            session.db,
            subscription_id
        )

        config = session.config

        if not subscription:
            session.logger.error(
                f"No subscription exists with id of {subscription_id}")
            return

        articles = crud.find_articles_for_delivery(
            session.db,
            subscription_id
        )

        if not articles:
            session.logger.info(
                "No articles to deliver for subscription  {subscription_id}")
            continue

        if args.pretend:
            for a in articles:
                print(
                    f"{a.article_id}. {subscription.title} - {a.title} ({a.url})\n")
            continue

        crud.set_attempted_delivery_at(session.db, subscription_id)

        mailer = Mailer(
            host=config['smtp_host'],
            port=config['smtp_port'],
            user=config['smtp_user'],
            password=config['smtp_password'],
            auth=config['smtp_auth'],
            ssl=config['smtp_ssl'],
            to_email=subscription.email
        )

        content_type = config['content_type']

        if subscription.digest:
            mailer.send_digest(
                feed_title=subscription.title,
                articles=articles,
                content_type=content_type,
                desc_length=subscription.desc_length,
                template=TEMPLATES[content_type]['digest_template']
            )
        else:
            for a in articles:
                mailer.send_article(
                    feed_title=subscription.title,
                    article=a,
                    content_type=content_type,
                    desc_length=subscription.desc_length,
                    template=TEMPLATES[content_type]['article_template']
                )


def cli(args=None):
    session = Session(
        logger=init_logger(),
        config=init_config(),
        db=init_db()
    )

    parser = init_arg_parser(session)
    parsed_args = parser.parse_args(args)
    results = None

    if parsed_args.command == 'add':
        results = add_feed(session, parsed_args)
    elif parsed_args.command == 'list':
        results = list_subscriptions(session)
    elif parsed_args.command == 'list-feeds':
        results = list_feeds(session)
    elif parsed_args.command == 'remove':
        results = remove_subscription(session, parsed_args)
    elif parsed_args.command == 'deliver':
        results = deliver_subscriptions(session, parsed_args)
    elif parsed_args.command == 'refresh':
        if parsed_args.feed_id:
            results = refresh_feed(session, parsed_args)
        else:
            results = refresh_feeds(session)
    else:
        parser.print_help()

    session.db.close()

    return results
