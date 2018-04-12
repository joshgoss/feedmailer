import argparse
import feedparser

import constants
import database

def handle_add(conn, args):
    results = database.find_feeds(conn, url=args.url)

    if len(results):
        print("ERROR: A feed already exists with that url.")
        return

    data = feedparser.parse(args.url)

    if data.bozo:
        print('ERROR: Unable to add an invalid feed location.')
        return

    database.create_feed(conn,
                         url=args.url,
                         title = args.title or data['feed']['title'],
                         digest = args.digest,
                         max_age = args.max_age)

def handle_list(conn, args):
    feeds = database.find_feeds(conn)

    for f in feeds:
        feed_id = f[0]
        title = f[1]

        print("%d) %s" % (feed_id, title))

def run_cli(**kwargs):
    parser = argparse.ArgumentParser(prog=constants.APP_NAME, description="Deliver feeds by email")

    subparsers = parser.add_subparsers(help='commands', dest='command')

    # Add command
    parser_add = subparsers.add_parser('add', help='Add a new feed')
    parser_add.add_argument('url', type=str, help='Location of rss feed')
    parser_add.add_argument('--title', dest='title', help='Specify custom title for feed')
    parser_add.add_argument('--max-age', type=int, dest='max_age', help='Max age of entries to fetch in days')

    parser_add.add_argument(
        '--digest',
        action='store_true',
        dest='digest',
        help='Send items as a digest instead of individually'
    )

    parser_add.set_defaults(title=None, digest=False, max_age=None)

    # List command
    parser_list = subparsers.add_parser('list', help='List all feeds')

    # Remove command
    parser_remove = subparsers.add_parser('remove', help='Remove a feed')
    parser_remove.add_argument('feed_id', type=int, help="id of feed")

    # Refresh command
    parser_refresh = subparsers.add_parser('refresh', help='Fetch latest articles and store them for mailing')
    parser_refresh.add_argument('feed_id', type=int, nargs='?', help='id of feed')

    args = parser.parse_args()

    # Deliver command
    parser_deliver = subparsers.add_parser('deliver', help='Email latest articles')
    parser_deliver.add_argument('feed_id', type=int, nargs='?', help='id of feed')

    args = parser.parse_args()

    if args.command == 'add':
        handle_add(kwargs['conn'], args)
    elif args.command == 'list':
        handle_list(kwargs['conn'], args)
    elif args.command == 'remove':
        return
    elif args.command == 'deliver':
        return
    elif args.command == 'refresh':
        return
    else:
        parser.print_help()
