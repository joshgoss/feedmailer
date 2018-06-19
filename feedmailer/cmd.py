import argparse
import feedparser
import html2text
import smtplib
from email.message import EmailMessage
from email.headerregistry import Address
from jinja2 import Template

from feedmailer import constants, database


class Mailer:
    def __init__(self, **kwargs):
        self.host = kwargs['host']
        self.user = kwargs['user']
        self.password = kwargs['password']
        self.auth = kwargs['auth']
        self.ssl = kwargs['ssl']
        self.port = kwargs['port']
        self.to_email = kwargs['to_email']


    def send(self, subject, content):
        constructor = smtplib.SMTP

        if self.ssl:
            constructor = smtplib.SMTP_SSL

        with constructor(self.host) as s:
            if self.auth:
                s.login(self.user, self.password)

            msg = EmailMessage()
            msg['From'] = Address(constants.DEFAULT_SENDER_NAME, self.user)
            msg['To'] = Address('', self.to_email)
            msg['Subject'] = subject

            msg.set_content(content)
            s.send_message(msg)


# convert feedparser entry to db schema of an article
def __entry_to_article(entry):
    published = None
    author = None
    h = html2text.HTML2Text()
    h.ignore_links = True

    if 'published' in entry and entry.published:
        published = entry.published

    if 'author' in entry and entry.author:
        author = entry.author

    return {
        'title': h.handle(entry.title).strip(),
        'url': entry.link,
        'author': author,
        'description': h.handle(entry.description).strip(),
        'published_at': published
    }


def __handle_add(session, args):
    if not args.email:
        print("ERROR: An email must be provided either within the config file or as an argument to the 'add' command." )
        return

    results = database.find_subscriptions(session.db, url=args.url, email=args.email)

    if len(results):
        print("ERROR: This feed is already being delivered to the email provided.")
        return

    data = feedparser.parse(args.url)

    if data.bozo:
        print('ERROR: Unable to add an invalid feed location.')
        return

    database.add_subscription(session.db,
                              url=args.url,
                              title=args.title or data['feed']['title'],
                              email=args.email,
                              digest=args.digest,
                              max_age=args.max_age)


def __handle_list(session, args):
    subscriptions = database.find_subscriptions(session.db)

    if not len(subscriptions):
        print("No subscriptions added yet")
        return

    for s in subscriptions:
        print("%d. \"%s\" -> %s" % (s['subscription_id'], s['title'], s['email']))


def __handle_list_feeds(session, args):
    feeds = database.find_feeds(session.db)

    if not len(feeds):
        print('No feeds added yet. Feeds are automatically created through subscriptions.')

    for f in feeds:
        print("%d. \"%s\"" % (f['feed_id'], f['title']))


def __handle_remove(session, subscription_id):
    subscription = database.find_subscription_by_id(session.db, subscription_id)

    if not subscription:
        print("ERROR: No subscription found with that id.")
        return

    database.remove_subscription(session.db, subscription_id)


def __handle_refresh_feed(session, feed_id):
    feed = database.find_feed_by_id(session.db, feed_id)
    if not feed:
        print("No feed exists with that id.")
        return

    data = feedparser.parse(feed['url'])

    articles = list(map((lambda a: __entry_to_article(a)), data.entries))
    num_added = database.refresh_articles(session.db, feed_id, articles)

    if num_added > 0:
        print("Found %d new article(s) for '%s'" % (num_added, feed['title']))
    else:
        print("No new articles found for '%s'." % feed['title'])

    return num_added


def __handle_refresh_all(session):
    feeds = database.find_feeds(session.db)
    num_added = 0

    for f in feeds:
        data = feedparser.parse(f['url'])
        articles = list(map((lambda a: __entry_to_article(a)), data.entries))
        num_added += database.refresh_articles(session.db, f['feed_id'], articles)

    print("%d new articles found in total" % num_added)

    return num_added



def __handle_deliver_subscription(session, subscription_id):
    subscription = database.find_subscription_by_id(session.db, subscription_id)
    config = session.config

    if not subscription:
        print("No subscription exists with that id")
        return

    articles = database.find_articles_for_delivery(session.db, subscription_id)

    database.set_attempted_delivery_at(session.db, subscription_id)

    mailer = Mailer(
        host = config['smtp_host'],
        port = config['smtp_port'],
        user = config['smtp_user'],
        password = config['smtp_password'],
        auth = config['smtp_auth'],
        ssl = config['smtp_ssl'],
        to_email = subscription['email']
    )

    if not articles:
        print("No articles to deliver")
        return

    if not subscription['digest']:
        with open(constants.TXT_ARTICLE_TEMPLATE) as f:
            template = Template(f.read())

            for a in articles:
                subject = subscription['title'] + ' - ' + a['title']

                content = template.render(article=a)

                mailer.send(
                    subject = subject[:80],
                    content = content
                )
    else:
        with open(constants.TXT_DIGEST_TEMPLATE) as f:
            template = Template(f.read())

            content = template.render(articles=articles, feed_title=subscription['title'])

            mailer.send(
                subscription['title'] + 'Digest',
                content
            )


def __handle_deliver_all(session):
    pass


def run(session):
    parser = argparse.ArgumentParser(prog=session.app_name, description="Deliver feeds by email")

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
        email=session.config.get('email', None)
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
    parser_deliver = subparsers.add_parser('deliver', help='Email latest articles')
    parser_deliver.add_argument('subscription_id', type=int, nargs='?', help='id of subscription')

    args = parser.parse_args()

    if args.command == 'add':
        __handle_add(session, args)
    elif args.command == 'list':
        __handle_list(session, args)
    elif args.command == 'list-feeds':
        __handle_list_feeds(session, args)
    elif args.command == 'remove':
        __handle_remove(session, args.subscription_id)
    elif args.command == 'deliver':
        if args.subscription_id:
            __handle_deliver_subscription(session, args.subscription_id)
        else:
            __handle_deliver_all(session)
    elif args.command == 'refresh':
        if args.feed_id:
            __handle_refresh_feed(session, args.feed_id)
        else:
            __handle_refresh_all(session)
    else:
        parser.print_help()
