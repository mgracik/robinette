import urllib2

from BeautifulSoup import BeautifulSoup
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
            'timestamp': _id.generation_time
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
            timestamp = msg['_id'].generation_time.astimezone(tz.tzlocal())
            return '%s was last seen on %s, saying: %s' % (
                nick, timestamp.strftime('%a %b %d %X'), msg['msg']
            )
        else:
            return 'I have not seen %s' % nick

    @signature(returns='string')
    def backlog(self, msg, *params):
        try:
            limit, = params
        except ValueError:
            limit = 10

        limit = min(max(10, limit), 50)

        response = []

        login = self.db.events.find({
            'user': {'$regex': '^%s' % self.nick(msg['user']), '$options': 'i'},
            'event': self.USERJOIN
        })
        login = list(login.sort([('_id', -1)]).limit(1))

        logout = self.db.events.find({
            'user': {'$regex': '^%s' % self.nick(msg['user']), '$options': 'i'},
            'event': {'$in': [self.USERLEFT, self.USERQUIT]}
        })
        logout = list(logout.sort([('_id', -1)]).limit(1))

        if login and logout:
            login_time = login[0]['_id'].generation_time
            logout_time = logout[0]['_id'].generation_time

            # We need naive times for the query.
            login_time = login_time.replace(tzinfo=None)
            logout_time = logout_time.replace(tzinfo=None)

            messages = self.db.messages.find(
                {'timestamp': {'$gt': logout_time, '$lt': login_time}}
            )
            messages = list(messages.sort([('_id', -1)]).limit(limit))
            for message in messages:
                response.append('%s: %s' % (self.nick(message['user']), message['msg']))

        return '\n'.join(response) if response else 'No messages'

    @signature(args=['string'], returns='string')
    def youtube(self, url):
        if not url.startswith('http://'):
            url = 'http://%s' % url
        fobj = urllib2.urlopen(url)
        soup = BeautifulSoup(
            fobj.read(),
            convertEntities=BeautifulSoup.HTML_ENTITIES
        )
        title = soup.find(id='eow-title')
        return 'Youtube spoiler: %s' % title.getText()


irc = IRC(chatbot)
