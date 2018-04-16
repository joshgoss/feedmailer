import cmd
import constants
import database

DB_LOCATION = 'feed-mailer.db'
APP_NAME = 'feed-mailer'
DEFAULT_EMAIL='josh@joshgoss.com'

if __name__ == "__main__":
    conn = database.connect(DB_LOCATION)

    database.setup_db(conn)
    cmd.run_cli(conn=conn, app_name=APP_NAME, email=DEFAULT_EMAIL)

    conn.close()
