from os import environ

import psycopg2
import psycopg2.extras


class Connection:
    def __init__(self):
        self.connection = psycopg2.connect(host=environ["postgres_host"],
                                     database=environ["postgres_db"], user=environ["postgres_user"],
                                     password=environ["postgres_pass"])
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def display_db_version(self):
        self.cursor.execute("SELECT version()")
        db_version = self.cursor.fetchone()
        print("Database version is {}".format(db_version))

    def register_group(self, group_jid, peer_code):
        row = self.get_group(group_jid)
        if row:
            print("Group {} already exist. Will not create a new entry".format(row))
        else:
            print("Adding new entry for Group ('', '{}', '{}')".format(group_jid, peer_code))
            sql_insert = "INSERT INTO group_chat(gc_kik_id, gc_name) VALUES(%s, %s)"
            self.cursor.execute(sql_insert, (group_jid, peer_code))
            self.connection.commit()

    def get_group(self, group_jid):
        sql_find = "SELECT * from group_chat WHERE gc_kik_id like %s"
        self.cursor.execute(sql_find, (group_jid,))
        return self.cursor.fetchone()

    def find_game(self, group_jid, game_type, exclude_concluded=True):
        sql_find = "SELECT * from game WHERE gc_kik_id like %s and game_type like %s"
        if exclude_concluded:
            sql_find = sql_find + "  and is_concluded is false"
        self.cursor.execute(sql_find, (group_jid, game_type))
        return self.cursor.fetchone()

    def start_game(self, group_jid, game_type, max_round):
        row = self.find_game(group_jid, game_type, False)
        if row:
            print("Game {} already exist. Will not create a new entry".format(row))
        else:
            sql_find = "SELECT * from game WHERE gc_kik_id like %s and game_type like %s"
            self.cursor.execute(sql_find, (group_jid, game_type))
            row = self.cursor.fetchone()
            if row:
                print("Game {} already exist but is concluded. Will update".format(row))
                sql_update_game = "UPDATE game SET is_concluded = false WHERE game_id = %s"
                self.cursor.execute(sql_update_game, (row["game_id"], ))
                self.connection.commit()
            else:
                print("Adding new entry for Game ('', '{}', '{}', '{}')".format(group_jid, game_type, max_round))
                sql_insert = "INSERT INTO game(gc_kik_id, game_type, is_concluded, max_round) VALUES(%s, %s, false, %s)"
                self.cursor.execute(sql_insert, (group_jid, game_type, max_round))
                self.connection.commit()

    def end_game(self, group_id, game_type):
        row = self.find_game(group_id, game_type)
        if row:
            self.cursor.execute("UPDATE game SET is_concluded = true, current_round = 0 WHERE game_id = %s",
                                (row["game_id"],))
            self.connection.commit()
            self.cursor.execute("DELETE FROM game_score WHERE game_id = %s", (row["game_id"],))
            self.connection.commit()

    def update_text_twist_scores(self, group_jid, from_jid, current_word, current_round):
        row_game = self.find_game(group_jid, "TextTwist")
        if row_game:
            sql_find_score = "SELECT * from game_score WHERE game_id = %s and member_kik_id like %s"
            self.cursor.execute(sql_find_score, (row_game["game_id"], from_jid))
            row_game_score = self.cursor.fetchone()
            if row_game_score:
                updated_score = row_game_score["score"] + 1
                sql_update_score = "UPDATE game_score SET score = %s WHERE game_score_id = %s"
                self.cursor.execute(sql_update_score, (updated_score, row_game_score["game_score_id"]))
                self.connection.commit()
            else:
                sql_insert = "INSERT INTO game_score(game_id, member_kik_id, score) VALUES(%s, %s, 1)"
                self.cursor.execute(sql_insert, (row_game["game_id"], from_jid))
                self.connection.commit()
            sql_update_game = "UPDATE game SET current_round = %s WHERE game_id = %s"
            self.cursor.execute(sql_update_game, (current_round, row_game["game_id"]))
            self.connection.commit()

            sql_insert_used_word = "INSERT INTO used_words(game_id, word) VALUES(%s, %s)"
            self.cursor.execute(sql_insert_used_word, (row_game["game_id"], current_word))
            self.connection.commit()

    def get_scores(self, game_id):
        scores = {}
        sql_find_scores = "SELECT * from game_score WHERE game_id = %s"
        self.cursor.execute(sql_find_scores, (game_id,))
        rows_game_score = self.cursor.fetchall()
        for row in rows_game_score:
            scores[row["member_kik_id"]] = row["score"]
        return scores

    def get_used_words(self, game_id):
        used_words = []
        sql_find_used_words = "SELECT * from used_words WHERE game_id = %s"
        self.cursor.execute(sql_find_used_words, (game_id,))
        rows_used_words = self.cursor.fetchall()
        for row in rows_used_words:
            used_words.append(row["word"])
        return used_words

    def close(self):
        self.cursor.close()
