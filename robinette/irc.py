import bson
from dateutil import tz
from nltk.chat.eliza import eliza_chatbot as chatbot
import pymongo

from xmlrpc.server import BaseHandler
from xmlrpc.util import signature


class IRC(BaseHandler):

    MESSAGE = 'msg'
    USERJOIN = 'user_join'
    USERLEFT = 'user_left'
    USERQUIT = 'user_quit'

    @staticmethod
    def nick(user):
        return user.split('!', 1)[0]

    def __init__(self, chatbot):
        self._mongo_conn = pymongo.MongoClient()
        self._chatbot = chatbot

    @property
    def db(self):
        return self._mongo_conn.robinette_db

    def log(self, event, data):
        logmethod = '_log_%s' % event
        if hasattr(self, logmethod):
            getattr(self, logmethod)(event, data)

    def _log_msg(self, event, data):
        _id = bson.ObjectId()
        self.db.messages.insert({
            '_id': _id,
            'user': data['user'],
            'channel': data['channel'],
            'msg': data['msg'],
            'timestamp': _id.generation_time.astimezone(tz.tzlocal())
        }, w=1)

    def _log_user_join(self, event, data):
        self.db.events.insert({
            '_id': bson.ObjectId(),
            'user': data['user'],
            'channel': data['channel'],
            'event': event
        }, w=1)

    def _log_user_left(self, event, data):
        self.db.events.insert({
            '_id': bson.ObjectId(),
            'user': data['user'],
            'channel': data['channel'],
            'event': event
        }, w=1)

    def _log_user_quit(self, event, data):
        self.db.events.insert({
            '_id': bson.ObjectId(),
            'user': data['user'],
            'quit_msg': data['quit_msg'],
            'event': event
        }, w=1)

    @signature(args=['string'], returns='string')
    def respond(self, msg):
        """
        Respond to the message.

        """
        return self._chatbot.respond(msg)

    @signature(args=['string'], returns='string')
    def seen(self, msg, nick):
        """
        Return the last time a user was seen.

        """
        messages = self.db.messages.find(
            {'user': {'$regex': '^%s' % nick, '$options': 'i'}}
        )
        # Get latest.
        messages = list(messages.sort([('_id', -1)]).limit(1))

        if messages:
            msg = messages[0]
            timestamp = msg['timestamp']
            return '%s was last seen on %s, saying: %s' % (
                nick, timestamp.strftime('%a %b %d %X'), msg['msg']
            )
        else:
            return 'I have not seen %s' % nick


irc = IRC(chatbot)
