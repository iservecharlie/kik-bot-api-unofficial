from os import environ

import psycopg2


class Connection:
    def __init__(self):
        self.connection = psycopg2.connect(host=environ["postgres_host"],
                                     database=environ["postgres_db"], user=environ["postgres_user"],
                                     password=environ["postgres_pass"])
        self.cursor = self.connection.cursor()

    def display_db_version(self):
        self.cursor.execute("SELECT version()")
        db_version = self.cursor.fetchone()
        print("Database version is {}".format(db_version))

    def register_group(self, group_jid, peer_code):
        sql_find = "SELECT * from group_chat WHERE gc_kik_id like %s"
        self.cursor.execute(sql_find, (group_jid,))
        row = self.cursor.fetchone()
        if row:
            print("Group {} already exist. Will not create a new entry".format(row))
        else:
            print("Adding new entry for Group ('', '{}', '{}')".format(group_jid, peer_code))
            sql_insert = "INSERT INTO group_chat(gc_kik_id, gc_name) VALUES(%s, %s)"
            self.cursor.execute(sql_insert, (group_jid, peer_code))
            self.connection.commit()

    def close(self):
        self.cursor.close()
