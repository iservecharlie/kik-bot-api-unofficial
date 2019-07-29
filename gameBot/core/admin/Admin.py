from os import environ

from kik_unofficial.client import KikClient

from gameBot.core.Constants import Constants

IS_DEV = False
GLOBAL_ADMIN = [environ['global_admin']]


class Admin:
    def __init__(self, client: KikClient, group_code_lookup, name_lookup):
        self.client = client
        self.group_code_lookup = group_code_lookup
        self.name_lookup = name_lookup
        if not IS_DEV:
            for global_admin in GLOBAL_ADMIN:
                self.client.send_chat_message(global_admin, "I am now online.")

    def process_if_admin_command(self, group_jid, message, member_jid, is_admin):
        is_processed = False
        if message in Constants.KIK_BOT_TRIGGERS:
            is_processed = True
            if message == Constants.LEAVE_TRIGGER and is_admin:
                print("[+] Leaving group {}.".format(self.group_code_lookup[group_jid]))
                self.client.leave_group(group_jid)
            elif message == Constants.TEST_TRIGGER:
                self.client.send_chat_message(group_jid, "-GER")
            else:
                is_processed = False
        return is_processed
