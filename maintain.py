from scrape import DB_PATH, HEADER
import requests
import sqlite3


def maintain_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT name, url FROM servers')
    rows = c.fetchall()
    for name, url in rows:
        try:
            response = requests.get(url, headers=HEADER, timeout=10)
            if response.status_code != 200:
                print(f"Removing {name} ({url}): HTTP {response.status_code}")
                c.execute('DELETE FROM servers WHERE url = ?', (url,))
        except Exception as e:
            print(f"Error accessing {url}: {e}")
            c.execute('DELETE FROM servers WHERE url = ?', (url,))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    maintain_db(DB_PATH)
