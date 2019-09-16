import json
import random
from os import environ
from random import shuffle

import httplib2
# pip3 install random-word
from random_word import RandomWords

import kik_unofficial.datatypes.xmpp.chatting as chatting
from gameBot.core.persistence.Connection import Connection
from kik_unofficial.client import KikClient


class TextTwist:
    text_twist_base_trigger = "tt"
    START = text_twist_base_trigger + " start"
    END = text_twist_base_trigger + " end"
    SKIP = text_twist_base_trigger + " skip"
    SHOW = text_twist_base_trigger + " show"
    SCORE = text_twist_base_trigger + " score"
    SHUFFLE = text_twist_base_trigger + " shuffle"
    HINT = text_twist_base_trigger + " hint"
    HELP = text_twist_base_trigger + " help"
    TEXT_TWIST_HELP = "TextTwist commands:\n" \
                      " Admin only command: \n" \
                      "  " + START + " [number of rounds] - number of rounds is optional \n" \
                      "  " + END + " - end the game \n" \
                      "  " + SKIP + " - skip current word \n" \
                      " All: \n" \
                      "  " + SHOW + " - display twisted text" \
                      "  " + SCORE + " - show scores" \
                      "  " + SHUFFLE + " - reshuffle letters" \
                      "  " + HINT + " - display hint" \
                      "  " + HELP + " - displays this help"
    TRIGGERS = [START, END, SKIP, SHOW, SCORE, SHUFFLE, HINT, HELP]
    HINT_SOURCE = "https://dictionaryapi.com/api/v3/references/sd4/json/"
    OLD_WORD_API_URL = "https://nlp.fi.muni.cz/projekty/random_word/run.cgi?"
    DEFAULT_CONFIG = {
        "verbose_logging": False,
        "min_length": 5,
        "max_length": 8,
        "parts_of_speech": "verbs",
        "form": "use",
        "probability": "true",
        "hint_api_key_param": environ["word_defn_api_key_param"]
    }

    def __init__(self, group_jid, text_twist_config, number_of_rounds, name_lookup, client: KikClient, score_board, used_words, current_round, is_legacy):
        self.group_jid = group_jid
        self.client = client
        self.game_config = text_twist_config
        self.current_word = ""
        self.twisted_word = ""
        self.number_of_rounds = number_of_rounds
        self.name_lookup = name_lookup
        self.score_board = score_board
        self.response_lock = False
        self.used_words = used_words
        self.cached_hint = []
        self.random_word_generator = RandomWords()
        self.connection = Connection()
        if is_legacy:
            self.current_round = current_round
            self.init_game("Game of Text twist has been resumed. ")
        else:
            self.current_round = 0
            self.init_game("Game of Text twist has been started. ")

    def init_game(self, message):
        self.init_round(message, False)

    def end_game(self):
        if self.score_board:
            self.display_score(True)
            max_score = 0
            winner_jids = []
            for key, val in sorted(self.score_board.items(), key=lambda kv: (kv[1], kv[0]), reverse=True):
                if max_score < val:
                    winner_jids = [key]
                    max_score = val
                elif max_score == val:
                    winner_jids.append(key)
            winner_count = len(winner_jids)
            if winner_count > 1:
                winner_names = []
                for winner_jid in winner_jids:
                    winner_names.append(self.name_lookup[winner_jid])
                self.client.send_chat_message(self.group_jid,
                                              "Game of Text twist has ended. It's a tie between {}. CONGRATULATIONS! Ang gagaling nyo!".format(" ,".join(winner_names)))
            else:
                self.client.send_chat_message(self.group_jid,
                                          "Game of Text twist has ended. The winner is {}. CONGRATULATIONS! PaCanton ka naman!".format(self.name_lookup[winner_jids[0]]))
        else:
            self.client.send_chat_message(self.group_jid, "Waley naka score!")
        self.connection.end_game(self.group_jid, "TextTwist")

    def init_round(self, prefix_message, skip):
        if not skip:
            self.current_round = self.current_round + 1
        unique_word = self.get_next_word()
        self.cached_hint = []
        while len(self.cached_hint) == 0:
            while unique_word in self.used_words:
                unique_word = self.get_next_word()
            self.used_words.append(unique_word)
            self.cached_hint = self.get_hint(unique_word)
        self.current_word = unique_word
        self.shuffle_word()
        self.display_shuffled_word(prefix_message)
        self.response_lock = False
        print("For game number {}, the word is {}".format(self.current_round, self.current_word))
        print("For game number {}, the word defn {}".format(self.current_round, self.cached_hint))

    def get_next_word(self):
        try:
            word = self.random_word_generator.get_random_word(hasDictionaryDef="true", includePartOfSpeech="verb", minLength=self.game_config["min_length"], maxLength=self.game_config["max_length"])
            self.response_lock = True
            return word.lower()
        except:
            print("Failed to get a word from random-word. Will get from backup")
            word = self.get_word_from_old_api()
            self.response_lock = True
            return word.lower()

    def get_word_from_old_api(self):
        h = httplib2.Http(".cache")
        api_params = "language_selection=en&word_selection={}&model_selection={}&length_selection={}&probability_selection={}" \
            .format(self.game_config["parts_of_speech"],self.game_config["form"],
                    random.randint(self.game_config["min_length"],self.game_config["max_length"]),
                    self.game_config["probability"],)
        (resp_headers, content) = h.request(self.OLD_WORD_API_URL + api_params, "GET")
        return str(content).replace("b'", "").replace("\\n'", "")

    def process_admin_command_trigger(self, chat_message: chatting.IncomingGroupChatMessage):
        trigger = chat_message.body.strip().lower()
        if trigger == self.SKIP and not self.response_lock:
            self.init_round("Skipping word, the correct answer is \"{}\". ".format(self.current_word), True)
        self.process_command_trigger(chat_message)

    def process_command_trigger(self, chat_message: chatting.IncomingGroupChatMessage):
        trigger = chat_message.body.strip().lower()
        if trigger == self.SHOW and not self.response_lock:
            print("Game number {}, twisted word:\n\t\"{}\"".format(self.current_round, self.current_word))
            self.display_shuffled_word("Displaying twisted word. ")
        elif trigger == self.SCORE:
            self.display_score(False)
        elif trigger == self.SHUFFLE:
            self.shuffle_word()
            self.display_shuffled_word("Shuffling letters. ")
        elif trigger == self.HINT:
            self.display_hint()
        elif trigger == self.HELP:
            self.client.send_chat_message(self.group_jid, self.TEXT_TWIST_HELP)

    def process_response(self, chat_message: chatting.IncomingGroupChatMessage):
        response = chat_message.body.strip().lower()
        from_jid = chat_message.from_jid
        if response == self.current_word and not self.response_lock and from_jid in self.name_lookup:
            self.response_lock = True
            if from_jid in self.name_lookup:
                display_name = self.name_lookup[from_jid]
                self.init_round("CORRECT! {} is the first to answer {}. \n".format(display_name, self.current_word), False)
                if from_jid in self.score_board:
                    self.score_board[from_jid] = self.score_board[from_jid] + 1
                else:
                    self.score_board[from_jid] = 1
                self.connection.update_text_twist_scores(self.group_jid, from_jid, self.current_word, self.current_round)
            if self.number_of_rounds != 0 and self.number_of_rounds >= self.current_round:
                return True
        else:
            if self.game_config["verbose_logging"]:
                print("Ignored response because wrong word? {}; response_locked? {}; not in name_lookup {}"
                      .format(response != self.current_round, self.response_lock, from_jid not in self.name_lookup))
            return False

    def get_hint(self, word):
        hint = []
        try:
            print("Initializing hint for {}".format(word))
            h = httplib2.Http(".cache")
            url_header = {'content-type': 'application/json'}
            (resp_headers, content) = h.request(
                self.HINT_SOURCE + word + self.game_config["hint_api_key_param"], "GET", "", url_header)
            json_string = str(content.decode())
            data = json.loads(json_string)[0]
            hint = data["shortdef"]
            print("Found {} definition for {}".format(len(hint), word))
        except:
            print("[XXX] Cannot find a hint for word {}.".format(word))
        return hint

    def display_shuffled_word(self, prefix_message):
        self.client.send_chat_message(self.group_jid, prefix_message +
                                      "Game number {}, twisted word:\n\t\"{}\"".format(self.current_round,
                                                                                       self.twisted_word))

    def display_score(self, final):
        scores = []
        for key, val in sorted(self.score_board.items(), key=lambda kv: (kv[1], kv[0]), reverse=True):
            try:
                scores.append(" {}: {}".format(self.name_lookup[key], str(val)))
            except KeyError as key_error:
                scores.append(" {}: {}".format("** pumanaw na **, str(val)))
        message = "Current Scores:\n{}".format("\n".join(scores))
        if final:
            message = "Final Scores:\n{}".format("\n".join(scores))
        self.client.send_chat_message(self.group_jid, message)

    def display_hint(self):
        self.client.send_chat_message(self.group_jid,
                                      "Game number {}, word definition:\n\t{}".format(self.current_round,
                                                                                       self.cached_hint[0]))

    def shuffle_word(self):
        word = list(self.current_word)
        shuffle(word)
        self.twisted_word = ''.join(word)
