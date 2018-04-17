import argparse
import feedparser

from dateutil import parser
import database

# convert feedparser entry to db schema of an article
def __entry_to_article(entry):
    published_utc = None

    if 'published' in entry and entry.published:
        published = parser.parse(entry.published)
        published_utc = published.utcnow()

    return {
        'title': entry.title,
        'url': entry.link,
        'author': None,
        'description': entry.description,
        'published_at': published_utc
    }

    return article

def __handle_add(conn, args):
    results = database.find_subscriptions(conn, url=args.url, email=args.email)

    if len(results):
        print("ERROR: This feed is already being delivered to the email provided.")
        return

    data = feedparser.parse(args.url)

    if data.bozo:
        print('ERROR: Unable to add an invalid feed location.')
        return

    database.add_subscription(conn,
                              url=args.url,
                              title=args.title or data['feed']['title'],
                              email=args.email,
                              digest=args.digest,
                              max_age=args.max_age)


def __handle_list(conn, args):
    subscriptions = database.find_subscriptions(conn)

    if not len(subscriptions):
        print("No subscriptions added yet")
        return

    for s in subscriptions:
        print("%d. \"%s\" -> %s" % (s['subscription_id'], s['title'], s['email']))


def __handle_list_feeds(conn, args):
    feeds = database.find_feeds(conn)

    if not len(feeds):
        print('No feeds added yet. Feeds are automatically created through subscriptions.')

    for f in feeds:
        print("%d. \"%s\"" % (f['feed_id'], f['title']))


def __handle_remove(conn, subscription_id):
    subscription = database.find_subscription_by_id(conn, subscription_id)

    if not subscription:
        print("ERROR: No subscription found with that id.")
        return

    database.remove_subscription(conn, subscription_id)


def __handle_refresh_feed(conn, feed_id):
    feed = database.find_feed_by_id(conn, feed_id)
    if not feed:
        print("No feed exists with that id.")
        return

    data = feedparser.parse(feed['url'])

    articles = list(map((lambda a: __entry_to_article(a)), data.entries))
    num_added = database.refresh_articles(conn, feed_id, articles)

    if num_added > 0:
        print("Found %d new article(s) for '%s'" % (num_added, feed['title']))
    else:
        print("No new articles found for '%s'." % feed['title'])

    return num_added


def __handle_refresh_all(conn):
    feeds = database.find_feeds(conn)
    num_added = 0

    for f in feeds:
        data = feedparser.parse(f['url'])
        articles = list(map((lambda a: __entry_to_article(a)), data.entries))
        num_added = database.refresh_articles(conn, f['feed_id'], articles)
        num_added += __handle_refresh_feed(conn, f['feed_id'])

    print("%d new articles found in total" % num_added)

    return num_added


def run_cli(**kwargs):
    parser = argparse.ArgumentParser(prog=kwargs['app_name'], description="Deliver feeds by email")

    subparsers = parser.add_subparsers(help='commands', dest='command')

    # Add command
    parser_add = subparsers.add_parser('add', help='Add a new feed subscription')
    parser_add.add_argument('url', type=str, help='Location of rss feed')
    parser_add.add_argument('--title', dest='title', help='Specify custom title for feed')
    parser_add.add_argument('--max-age', type=int, dest='max_age', help='Max age of entries to fetch in days')
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
        email=kwargs['email']
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

    args = parser.parse_args()

    # Deliver command
    parser_deliver = subparsers.add_parser('deliver', help='Email latest articles')
    parser_deliver.add_argument('subscription_id', type=int, nargs='?', help='id of subscription')

    args = parser.parse_args()

    if args.command == 'add':
        __handle_add(kwargs['conn'], args)
    elif args.command == 'list':
        __handle_list(kwargs['conn'], args)
    elif args.command == 'list-feeds':
        __handle_list_feeds(kwargs['conn'], args)
    elif args.command == 'remove':
        __handle_remove(kwargs['conn'], args.subscription_id)
    elif args.command == 'deliver':
        return
    elif args.command == 'refresh':
        if args.feed_id:
            __handle_refresh_feed(kwargs['conn'], args.feed_id)
        else:
            __handle_refresh_all(kwargs['conn'])
    else:
        parser.print_help()
