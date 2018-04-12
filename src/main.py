import sqlite3

import cmd
import constants
import database


if __name__ == "__main__":
    conn = sqlite3.connect(constants.DB_LOCATION)

    database.setup_db(conn)
    cmd.run_cli(conn=conn)

    conn.close()
