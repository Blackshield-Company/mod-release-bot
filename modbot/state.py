"""seen.db: release IDs already drafted. First run per repo seeds silently (release-notifier pattern)."""
import sqlite3
import time


class Seen:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("create table if not exists seen(id text primary key, ts int)")
        self.db.execute("create table if not exists seeded_repos(repo text primary key, ts int)")

    def is_seeded(self, repo):
        return self.db.execute("select 1 from seeded_repos where repo=?", (repo.lower(),)).fetchone() is not None

    def mark_seeded(self, repo):
        self.db.execute("insert or ignore into seeded_repos values(?,?)", (repo.lower(), int(time.time())))
        self.db.commit()

    def has(self, key):
        return self.db.execute("select 1 from seen where id=?", (key,)).fetchone() is not None

    def add(self, key):
        self.db.execute("insert or ignore into seen values(?,?)", (key, int(time.time())))
        self.db.commit()
