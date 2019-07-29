from gameBot.core.persistence.Connection import Connection
from gameBot.game.TextTwist import TextTwist
from kik_unofficial.client import KikClient


class GameManager:
    def __init__(self, client: KikClient, group_code_lookup, name_lookup):
        self.client = client
        self.group_code_lookup = group_code_lookup
        self.name_lookup = name_lookup
        print("initialize game manager")
        self.connection = Connection()
        self.text_twist_sessions = {}

    def init_text_twist_legacy_sessions(self, group_jids):
        for group_jid in group_jids:
            row_game = self.connection.find_game(group_jid, "TextTwist")
            if row_game:
                scores = self.connection.get_scores(row_game["game_id"])
                used_words = self.connection.get_used_words(row_game["game_id"])
                text_twist = TextTwist(group_jid, TextTwist.DEFAULT_CONFIG, row_game["max_round"], self.name_lookup,
                                       self.client, scores, used_words, row_game["current_round"] - 1, True)
                self.text_twist_sessions[group_jid] = text_twist

    def get_text_twist_session(self, group_jid):
        if group_jid in self.text_twist_sessions:
            return self.text_twist_sessions[group_jid]
        else:
            return False

    def process_if_game_command(self, group_jid, chat_message, member_jid, is_admin):
        is_processed = True
        group_name = self.group_code_lookup[group_jid]
        text_twist = self.get_text_twist_session(group_jid)
        message = chat_message.body.strip().lower()
        if message in TextTwist.TRIGGERS or message.startswith(TextTwist.START):
            if text_twist:
                if message == TextTwist.START and is_admin:
                    print("[+] Group {} has an active game session of TextTwist.".format(group_name))
                    self.client.send_chat_message(group_jid, "There is already a game of Text Twist active.\n"
                                                             " To end the game an admin must enter: "
                                                             "'" + TextTwist.END + "'")
                elif message == TextTwist.END and is_admin:
                    print("[+] Group {} ending a game session of TextTwist.".format(group_name))
                    text_twist.end_game()
                    del self.text_twist_sessions[group_jid]
                elif is_admin:
                    text_twist.process_admin_command_trigger(chat_message)
                else:
                    text_twist.process_command_trigger(chat_message)
            else:
                if message.startswith(TextTwist.START) and is_admin:
                    print("[+] Group {} starting a game session of TextTwist.".format(group_name))
                    number_of_rounds = 0
                    tokens = message.replace(TextTwist.START, "").split(" ")
                    if len(tokens) > 1:
                        try:
                            number_of_rounds = int(tokens[0])
                        except ValueError:
                            number_of_rounds = 0
                    self.text_twist_sessions[group_jid] = TextTwist(group_jid, TextTwist.DEFAULT_CONFIG,
                                                                    number_of_rounds, self.name_lookup, self.client,
                                                                    {}, [], 0, False)

                    self.connection.start_game(group_jid, "TextTwist", number_of_rounds)
                elif message == TextTwist.END and is_admin:
                    self.client.send_chat_message(group_jid, "There is no game of Text Twist active.\n"
                                                             " To start a game an admin must enter: "
                                                             "'" + TextTwist.START + "'")
        elif group_jid in self.text_twist_sessions:
            end_game = self.text_twist_sessions[group_jid].process_response(chat_message)
            if end_game:
                self.text_twist_sessions[group_jid].end_game()
                del self.text_twist_sessions[group_jid]
        else:
            is_processed = False
        return is_processed
