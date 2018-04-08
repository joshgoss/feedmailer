import argparse


def handle_list():
    pass

def handle_add(**kwargs):
    pass

def handle_remove(feed_id):
    pass

def handle_refresh(feed_id):
    pass

def handle_deliver(feed_id):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="feed-mailer", description="Deliver feeds by email")

    subparsers = parser.add_subparsers(help='commands', dest='command')

    # Add command
    parser_add = subparsers.add_parser('add', help='Add a new feed')
    parser_add.add_argument('url', type=str, help='Location of rss feed')
    parser_add.add_argument('--title', help='Specify custom title for feed')

    parser_add.add_argument(
        '--digest',
        action='store_true',
        dest='digest',
        help='Send items as a digest instead of individually'
    )

    parser_add.set_defaults(digest=False)

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
        handle_add(**vars(args))
    elif args.command == 'list':
        handle_list()
    elif args.command == 'remove':
        handle_remove(args.feed_id)
    elif args.command == 'deliver':
        handle_deliver(args.feed_id)
    elif args.command == 'refresh':
        handle_refresh(args.feed_id)
    else:
        parser.print_help()
