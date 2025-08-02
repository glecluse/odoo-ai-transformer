import sqlite3

DB_FILE = "connections.db"

def init_db():
    """Crée la table des connexions si elle n'existe pas."""
    with sqlite3.connect(DB_FILE) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                db_name TEXT NOT NULL,
                username TEXT NOT NULL
            )""")
        con.commit()

def load_connections():
    """Charge toutes les connexions sauvegardées depuis la base de données."""
    try:
        with sqlite3.connect(DB_FILE) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM connections ORDER BY name")
            return [dict(row) for row in cur.fetchall()]
    except sqlite3.OperationalError:
        # La table n'existe probablement pas encore, initialisons-la
        init_db()
        return []


def save_connection(name, url, db_name, username):
    """Sauvegarde ou met à jour une connexion."""
    with sqlite3.connect(DB_FILE) as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO connections (name, url, db_name, username) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                url=excluded.url,
                db_name=excluded.db_name,
                username=excluded.username
        """, (name, url, db_name, username))
        con.commit()