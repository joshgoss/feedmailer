import sqlite3


def connect(location):
    conn = sqlite3.connect(location)

    # Return rows as a dictionary instead of as a tuple of values
    conn.row_factory = sqlite3.Row

    return conn


def get_user_version(conn):
    cur = conn.cursor()

    cur.execute("PRAGMA USER_VERSION")
    results = cur.fetchone()
    cur.close()

    return results['user_version']


def setup_db(conn):
    version = get_user_version(conn) + 1
    cur = conn.cursor()

    if version == 1:
        # Create feeds table
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
        cur.execute("PRAGMA user_version={v:d}".format(v=version))

        conn.commit()

    cur.close()


def find_feeds(conn, **kwargs):
    feed_id = kwargs.get('feed_id', None)
    title = kwargs.get('title', None)
    url = kwargs.get('url', None)

    query = ("SELECT f.feed_id, f.title, f.url, f.refreshed_at FROM feeds f "
             "WHERE f.feed_id = COALESCE(?, f.feed_id) AND f.title = COALESCE(?, f.title) AND f.url = COALESCE(?, f.url);")

    cur = conn.cursor()
    cur.execute(query, (feed_id, title, url))
    rows = cur.fetchall()
    cur.close()

    return rows


def find_feed_by_id(conn, feed_id):
    results = find_feeds(conn, feed_id=feed_id)

    if not len(results):
        return None
    else:
        return results[0]


def find_subscriptions(conn, **kwargs):
    subscription_id = kwargs.get('subscription_id', None)
    title = kwargs.get('title', None)
    url = kwargs.get('url', None)
    email = kwargs.get('email', None)

    query = ("SELECT f.feed_id, f.title, f.url, f.refreshed_at, s.subscription_id, s.email, s.attempted_delivery_at, s.digest FROM subscriptions s "
             "INNER JOIN feeds f ON s.feed_id = f.feed_id "
             "WHERE s.subscription_id = COALESCE(?, s.subscription_id) AND f.title = COALESCE(?, f.title) AND f.url = COALESCE(?, f.url) AND s.email = COALESCE(?, email);")

    cur = conn.cursor()
    cur.execute(query, (subscription_id, title, url, email))
    rows = cur.fetchall()
    cur.close()

    return rows


def find_subscription_by_id(conn, subscription_id):
    results = find_subscriptions(conn, subscription_id=subscription_id)

    if not len(results):
        return None
    else:
        return results[0]


# Add a subscription to a feed, if the feed does not exist
# then it will be created and subscribed to
def add_subscription(conn, **kwargs):
    cur = conn.cursor()

    temp_table_sql = ("CREATE TEMP TABLE temp_subs("
                      "title VARCHAR NOT NULL,"
                      "url VARCHAR NOT NULL,"
                      "email VARCHAR NOT NULL,"
                      "digest BOOLEAN"
                      ");")
    insert_into_temp_sql = ("INSERT INTO temp_subs(title, url, email, digest)"
                            "VALUES (?, ?, ?, ?);")

    add_feed_sql = ("INSERT INTO feeds(title, url, created_at) "
                    "SELECT t.title, t.url, CURRENT_TIMESTAMP FROM temp_subs t "
                    "LEFT JOIN feeds f ON t.url = f.url "
                    "WHERE f.feed_id IS NULL;")

    add_subscription_sql = ("INSERT INTO subscriptions(feed_id, email, digest, created_at) "
                            "SELECT f.feed_id, t.email, t.digest, CURRENT_TIMESTAMP FROM temp_subs t "
                            "INNER JOIN feeds f ON t.url = f.url;")

    values = (
        kwargs['title'],
        kwargs['url'],
        kwargs['email'],
        kwargs['digest']
    )

    cur.execute(temp_table_sql)
    cur.execute(insert_into_temp_sql, values)
    cur.execute(add_feed_sql)
    cur.execute(add_subscription_sql)
    conn.commit()
    cur.close()


def remove_subscription(conn, subscription_id):
    cur = conn.cursor()
    query = "DELETE FROM subscriptions WHERE subscription_id = ?;"

    cur.execute(query, (subscription_id,))
    conn.commit()
    cur.close()


# Insert articles which do not already exist
# for a feed
def refresh_articles(conn, feed_id, articles):
    create_temp_table = ("CREATE TEMP TABLE temp_articles ("
                  "url VARCHAR NOT NULL,"
                  "title VARCHAR NOT NULL,"
                  "author VARCHAR NULL, "
                  "feed_id INTEGER NOT NULL,"
                  "description TEXT NULL,"
                  "published_at DATETIME);")

    insert_into_temp = "INSERT INTO temp_articles (url, title, author, feed_id, description, published_at) VALUES (?, ?, ?, ?, ?, ?);"

    merge_temp = "INSERT INTO articles (url, title, author, feed_id, description, published_at, created_at) SELECT t.url, t.title, t.author, t.feed_id, t.description, DATETIME(t.published_at, 'UTC'), CURRENT_TIMESTAMP FROM temp_articles AS t LEFT JOIN articles AS a ON t.feed_id = a.feed_id AND t.url = a.url WHERE a.article_id IS NULL;"

    values = list(map((lambda a: (a['url'], a['title'], a['author'], feed_id, a['description'], a['published_at'])), articles))

    cur = conn.cursor()

    cur.execute("UPDATE feeds SET refreshed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE feed_id = ?;", (feed_id,))
    cur.execute(create_temp_table)
    cur.executemany(insert_into_temp, values)
    cur.execute(merge_temp)

    conn.commit()

    num_merged = cur.rowcount

    cur.execute("DROP TABLE temp_articles;")
    conn.commit()
    cur.close()

    return num_merged


def find_articles_for_delivery(conn, subscription_id):
    cur = conn.cursor()
    query = ("SELECT "
             "a.article_id,"
             "a.title,"
             "a.url,"
             "a.published_at,"
             "a.author,"
             "a.description,"
             "a.feed_id "
             "FROM subscriptions s "
             "INNER JOIN articles a ON s.feed_id = a.feed_id "
             "WHERE s.subscription_id = ? "
             "AND COALESCE(a.published_at, a.created_at) > COALESCE(s.attempted_delivery_at, a.created_at); ")

    cur.execute(query, (subscription_id,))
    conn.commit()
    rows = cur.fetchall()
    cur.close()

    return rows


def set_attempted_delivery_at(conn, subscription_id):
    query = "UPDATE subscriptions SET attempted_delivery_at = CURRENT_TIMESTAMP WHERE subscription_id = ?;"
    cur = conn.cursor()

    cur.execute(query, (subscription_id,))
    conn.commit()
    cur.close()
