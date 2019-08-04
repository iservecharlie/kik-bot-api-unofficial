class Constants:
    LEAVE_TRIGGER = "layas kulas"
    GAME_LIST_TRIGGER = "laro tayo kulas"
    TEST_TRIGGER = "ping"
    DEFAULT_HELP_MESSAGE = "Base commands:  \n" \
                           " Admin only: \n" \
                           "  " + LEAVE_TRIGGER + " - bot leaves \n" \
                           "  " + GAME_LIST_TRIGGER + " - game list \n" \
                           " Game bot manual. For help with game commands reply with 'man [game name]." \
                           " Games available: texttwist(tt)."
    KIK_BOT_TRIGGERS = [LEAVE_TRIGGER, GAME_LIST_TRIGGER, TEST_TRIGGER]
