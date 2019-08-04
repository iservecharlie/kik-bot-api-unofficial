from os import environ

import kik_unofficial.datatypes.xmpp.chatting as chatting
from gameBot.core.Constants import Constants
from gameBot.core.admin.Admin import Admin
from gameBot.core.persistence.Connection import Connection
from gameBot.game.GameManager import GameManager
from gameBot.game.TextTwist import TextTwist
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.client import KikClient
from kik_unofficial.datatypes.peers import User, Group
from kik_unofficial.datatypes.xmpp.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeerInfoResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse

username = environ['kik_username']
password = environ['kik_password']


class KikBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password)
        self.group_code_lookup = {}
        self.name_lookup = {}
        self.group_admins = {}
        self.logging = {
            "typing": False,
            "receipts": False,
            "read": False,
            "group_chat": True
        }
        self.admin_actions = Admin(self.client, self.group_code_lookup, self.name_lookup)
        self.game_manager = GameManager(self.client, self.group_code_lookup, self.name_lookup)

    def on_authenticated(self):
        print("Now I'm Authenticated, let's request roster")
        self.client.request_roster()

    def on_login_ended(self, response: LoginResponse):
        print("Full name: {} {}".format(response.first_name, response.last_name))

    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        print("[+] '{}' says: {}".format(chat_message.from_jid, chat_message.body))
        clean_message = chat_message.body.strip().lower()
        help_message = Constants.DEFAULT_HELP_MESSAGE
        if clean_message.startswith("man "):
            game_name = clean_message.split(" ")[1]
            if "tt" == game_name or "texttwist" == game_name:
                help_message = TextTwist.TEXT_TWIST_HELP
        self.client.send_chat_message(chat_message.from_jid, help_message)

    def on_message_delivered(self, response: chatting.IncomingMessageDeliveredEvent):
        print("[+] Chat message with ID {} is delivered.".format(response.message_id))

    def on_message_read(self, response: chatting.IncomingMessageReadEvent):
        if self.logging["read"]:
            print("[+] Human has read the message with ID {}.".format(response.message_id))

    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        group_jid = chat_message.group_jid
        member_jid = chat_message.from_jid
        group_code = self.group_code_lookup[group_jid]
        name = self.name_lookup[member_jid]
        clean_message = chat_message.body.strip().lower()
        admins = self.group_admins[group_jid]
        is_admin_message = member_jid in admins
        if self.logging['group_chat']:
            print("[+] '{}' from group '{}' says: {}".format(name, group_code, chat_message.body))

        is_admin_trigger = self.admin_actions.process_if_admin_command(group_jid, clean_message,
                                                                       member_jid, is_admin_message)
        if not is_admin_trigger:
            self.game_manager.process_if_game_command(group_jid, chat_message,
                                                      member_jid, is_admin_message)

    def on_is_typing_event_received(self, response: chatting.IncomingIsTypingEvent):
        if self.logging["typing"]:
            print("[+] {} is now {}typing.".format(response.from_jid, "not " if not response.is_typing else ""))

    def on_group_is_typing_event_received(self, response: chatting.IncomingGroupIsTypingEvent):
        if self.logging["typing"]:
            print("[+] {} is now {}typing in group {}".format(response.from_jid, "not " if not response.is_typing else "",
                                                          response.group_jid))

    def on_roster_received(self, response: FetchRosterResponse):
        print("[*]ROSTER init:")
        group_jids = []
        connection = Connection()
        for peer in response.peers:
            try:
                if type(peer) is User:
                    print("[*] User: {}".format(peer))
                if type(peer) is Group:
                    print("[*] Group: {}".format(peer))
                    group_jid = peer.jid
                    admins = []
                    for group_member in peer.members:
                        member_jid = group_member.jid
                        member_is_admin = group_member.is_admin or group_member.is_owner
                        if member_is_admin:
                            admins.append(member_jid)
                        self.client.request_info_of_jids([member_jid])
                    self.group_admins[group_jid] = admins
                    self.group_code_lookup[group_jid] = peer.code
                    connection.register_group(group_jid, peer.code)
                    print("[**] Group has {} Admins".format(len(admins)))
            except Exception, e:
                print("[XXX] There was an error displaying: {} of type: {}".format(peer.jid, type(peer)))
                print(e)
        connection.close()
        self.game_manager.init_text_twist_legacy_sessions(self.group_admins.keys())

    def on_friend_attribution(self, response: chatting.IncomingFriendAttribution):
        print("[+] Friend attribution request from " + response.referrer_jid)

    def on_image_received(self, image_message: chatting.IncomingImageMessage):
        print("[+] Image message was received from {}".format(image_message.from_jid))

    def on_peer_info_received(self, response: PeerInfoResponse):
        for user in response.users:
            self.name_lookup[user.jid] = user.display_name

    def on_group_status_received(self, response: chatting.IncomingGroupStatus):
        print("[+] Status message in {}: {}".format(response.group_jid, response.status))

    def on_group_receipts_received(self, response: chatting.IncomingGroupReceiptsEvent):
        if self.logging["receipts"]:
            print("[+] Received receipts in group {}: {}".format(response.group_jid, ",".join(response.receipt_ids)))

    def on_status_message_received(self, response: chatting.IncomingStatusResponse):
        print("[+] Status message from {}: {}".format(response.from_jid, response.status))

    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
        print("Is {} a unique username? {}".format(response.username, response.unique))

    def on_sign_up_ended(self, response: RegisterResponse):
        print("[+] Registered as " + response.kik_node)

    # Error handling

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("[-] Connection failed: " + response.message)

    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)

    def on_register_error(self, response: SignUpError):
        print("[-] Register error: {}".format(response.message))
