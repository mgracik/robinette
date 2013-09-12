import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

import bson
from nltk.chat.eliza import eliza_chatbot as chatbot
import pymongo

from xmlrpc.server import BaseHandler
from xmlrpc.util import signature


class IRC(BaseHandler):

    def __init__(self, chatbot):
        #self._mongo_conn = pymongo.MongoClient()
        self._chatbot = chatbot

    def log(self, data):
        log.debug('Logged %s', data)
        #event = {
        #    _id: bson.ObjectId(),
        #    user: user,
        #    channel: channel,
        #    msg: msg
        #}
        #db = self._mongo_conn.event_db
        #db.events.insert(event, w=1)

    @signature(args=['string'], returns='string')
    def respond(self, msg):
        """
        Respond to the message.

        """
        return self._chatbot.respond(msg)

    @signature(args=['int', 'int'], returns='int')
    def add(self, a, b):
        """
        Add two integers.

        """
        try:
            a, b = int(a), int(b)
        except ValueError:
            return None

        return a + b

    @signature(args=['int', 'int'], returns='int')
    def sub(self, a, b):
        """
        Subtract two integers.

        """
        try:
            a, b = int(a), int(b)
        except ValueError:
            return None

        return a - b


irc = IRC(chatbot)
