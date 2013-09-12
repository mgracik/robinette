from dateutil import tz
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
        self._mongo_conn = pymongo.MongoClient()
        self._chatbot = chatbot

    def log(self, data):
        log.debug('Logged %s', data)
        event = {
            '_id': bson.ObjectId(),
            'user': data['user'],
            'channel': data['channel'],
            'msg': data['msg']
        }
        db = self._mongo_conn.event_db
        db.events.insert(event, w=1)

    @signature(args=['string'], returns='string')
    def respond(self, msg):
        """
        Respond to the message.

        """
        return self._chatbot.respond(msg)

    @signature(args=['string'], returns='string')
    def seen(self, nick):
        """
        Return the last time a user was seen.

        """
        db = self._mongo_conn.event_db
        messages = db.events.find(
            {'user': {'$regex': '^%s' % nick, '$options': 'i'}}
        )
        # Get latest.
        messages = list(messages.sort([('_id', -1)]).limit(1))

        if messages:
            msg = messages[0]
            return '%s was last seen on %s, saying: %s' % (
                nick,
                msg['_id'].generation_time.astimezone(tz.tzlocal()).strftime('%a %b %d %X'),
                msg['msg']
            )
        else:
            return 'I have not seen %s' % nick


irc = IRC(chatbot)
