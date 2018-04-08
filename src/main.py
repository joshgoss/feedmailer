import argparse
import sqlite3

##############################
# Constants
##############################

DB_LOCATION = 'feed-mailer.db'
APP_NAME = 'feed-mailer'


############################
# Database Functions
############################

def get_user_version(conn):
    cur = conn.cursor()

    cur.execute("PRAGMA USER_VERSION")
    results = cur.fetchone()
    cur.close()

    return results[0]


def setup_db(conn):
    version = get_user_version(conn) + 1
    cur = conn.cursor()

    if version == 1:
        # Create feeds table
        feeds_table = ("CREATE TABLE feeds ("
                       "feed_id INTEGER PRIMARY KEY,"
                       "title VARCHAR(75) NOT NULL,"
                       "url VARCHAR(155) UNIQUE NOT NULL,"
                       "digest BOOLEAN DEFAULT FALSE,"
                       "max_age INTEGER NULL,"
                       "created_at DATETIME,"
                       "checked_at DATETIME NULL,"
                       "delivered_at DATETIME NULL"
                       ");")

        articles_table = ("CREATE TABLE articles("
                        "articles_id INTEGER PRIMARY KEY,"
                        "title VARCHAR(100) NOT NULL,"
                        "author VARCHAR(100) NOT NULL,"
                        "feed_id INTEGER NOT NULL,"
                        "category VARCHAR(55) NOT NULL,"
                        "description TEXT(2000),"
                        "published_at DATETIME,"
                        "created_at DATETIME,"
                        "delivered_at DATETIME NULL,"
                        "FOREIGN KEY(feed_id) REFERENCES feeds(feed_id)"
                        ");")

        cur.execute(feeds_table)
        cur.execute(articles_table)
        cur.execute("PRAGMA user_version={v:d}".format(v=version))

        conn.commit()

    cur.close()


############################
# Commandline Functions
#############################
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

def run_cli(conn):
    parser = argparse.ArgumentParser(prog=APP_NAME, description="Deliver feeds by email")

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


if __name__ == "__main__":
    conn = sqlite3.connect(DB_LOCATION)

    setup_db(conn)
    run_cli(conn)

    conn.close()
