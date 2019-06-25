import httplib2
import json
# pip3 install random-word

class WordBank:
    WORD_SOURCE = "https://randomwordgenerator.com/json/words.json"

    def __init__(self):
        self.words = []
        self.init_words()

    def init_words(self):
        h = httplib2.Http(".cache")
        url_header = {'content-type': 'application/json'}
        (resp_headers, content) = h.request(self.WORD_SOURCE, "GET", "", url_header)
        json_string = str(content.decode())
        data = json.loads(json_string)
        words = data["data"]