

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


def find_feeds(conn, **kwargs):
    feed_id = kwargs.get('feed_id', None)
    title = kwargs.get('title', None)
    query = "SELECT * FROM feeds WHERE feed_id = COALESCE(?, feed_id) AND title = COALESCE(?, title);"

    cur = conn.cursor()
    cur.execute(query, (feed_id, title))
    rows = cur.fetchall()
    cur.close()

    return rows

def create_feed(conn, **kwargs):
    cur = conn.cursor()
    query = "INSERT INTO feeds (title, url, digest, max_age, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);"

    cur.execute(query, (kwargs['title'], kwargs['url'], kwargs['digest'], kwargs['max_age']))
    conn.commit()
    cur.close()


def delete_feed(feed_id):
    pass
