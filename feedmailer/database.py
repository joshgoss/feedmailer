import sqlite3


def connect(location: str) -> sqlite3.Connection:
    conn = sqlite3.connect(location)

    # Return rows as a dictionary instead of as a tuple of values
    conn.row_factory = sqlite3.Row

    return conn


def get_user_version(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()

    cur.execute("PRAGMA USER_VERSION")
    results = cur.fetchone()
    cur.close()

    return results['user_version']


def setup_db(conn: sqlite3.Connection):
    version = get_user_version(conn)
    cur = conn.cursor()

    if version == 0:
        feeds_table = ("CREATE TABLE feeds ("
                       "feed_id INTEGER PRIMARY KEY NOT NULL,"
                       "title VARCHAR(75) NOT NULL,"
                       "url VARCHAR(155) UNIQUE NOT NULL,"
                       "created_at DATETIME,"
                       "updated_at DATETIME NULL,"
                       "refreshed_at DATETIME NULL"
                       ");")

        subscriptions_table = ("CREATE TABLE subscriptions("
                               "subscription_id INTEGER PRIMARY KEY NOT NULL,"
                               "email VARCHAR(155) NOT NULL,"
                               "feed_id INTEGER NOT NULL,"
                               "digest BOOLEAN DEFAULT FALSE,"
                               "attempted_delivery_at DATETIME NULL,"
                               "created_at DATETIME,"
                               "updated_at DATETIME,"
                               "FOREIGN KEY(feed_id) REFERENCES feeds(feed_id)"
                               ");")

        articles_table = ("CREATE TABLE articles("
                          "article_id INTEGER PRIMARY KEY NOT NULL,"
                          "title VARCHAR(100) NOT NULL,"
                          "url VARCHAR(200) NOT NULL,"
                          "author VARCHAR(100),"
                          "feed_id INTEGER NOT NULL,"
                          "category VARCHAR(55),"
                          "description TEXT(2000),"
                          "published_at DATETIME,"
                          "created_at DATETIME,"
                          "updated_at DATETIME,"
                          "FOREIGN KEY(feed_id) REFERENCES feeds(feed_id),"
                          "UNIQUE(feed_id, url)"
                          ");")

        cur.execute(feeds_table)
        cur.execute(subscriptions_table)
        cur.execute(articles_table)

        version += 1

    if version == 1:
        cur.execute(
            "ALTER TABLE subscriptions ADD COLUMN desc_length INTEGER DEFAULT 255")
        version += 1

    cur.execute("PRAGMA user_version={v:d}".format(v=version))

    conn.commit()
    cur.close()
