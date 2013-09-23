import datetime
import json
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('robinette.irc')
import re
import urllib
import urllib2

from BeautifulSoup import BeautifulSoup
import bson
from dateutil import tz
from nltk.chat.eliza import eliza_chatbot as chatbot
import pymongo

from xmlrpc.server import BaseHandler
from xmlrpc.util import signature


YQL_QUERY = 'select Name, AskRealtime, BidRealtime from yahoo.finance.quote where symbol = "%s"'
YQL_URL = 'http://query.yahooapis.com/v1/public/yql?%s'

YOUTUBE_URL = re.compile(r'((?:www\.)?youtube\.com/watch\?v=\S+)')


def nickname(user):
    return user.split('!', 1)[0]


class PrivMsg(str):
    pass


class MongoDB(object):

    def __init__(self):
        self._mongo_conn = pymongo.MongoClient()

    @property
    def db(self):
        return self._mongo_conn.robinette_db

    def log_privmsg(self, event, data):
        _id = bson.ObjectId()
        self.db.messages.insert({
            '_id': _id,
            'user': data['user'],
            'channel': data['channel'],
            'msg': data['msg'],
            'timestamp': _id.generation_time
        }, w=1)

    def log_user_join(self, event, data):
        self.db.events.insert({
            '_id': bson.ObjectId(),
            'event': event,
            'user': data['user'],
            'channel': data['channel']
        }, w=1)

    def log_user_left(self, event, data):
        self.db.events.insert({
            '_id': bson.ObjectId(),
            'event': event,
            'user': data['user'],
            'channel': data['channel']
        }, w=1)

    def log_user_quit(self, event, data):
        self.db.events.insert({
            '_id': bson.ObjectId(),
            'event': event,
            'user': data['user'],
            'quit_msg': data['quit_msg'],
        }, w=1)

    def backlog(self, nick, limit=20):
        login = self.db.events.find({
            'user': {'$regex': '^%s' % nick, '$options': 'i'},
            'event': 'user_join'
        })
        login = list(login.sort([('_id', -1)]).limit(1))

        logout = self.db.events.find({
            'user': {'$regex': '^%s' % nick, '$options': 'i'},
            'event': {'$in': ['user_left', 'user_quit']}
        })
        logout = list(logout.sort([('_id', -1)]).limit(1))

        if login and logout:
            login_time = login[0]['_id'].generation_time
            logout_time = logout[0]['_id'].generation_time

            # We need naive times for the query.
            login_time = login_time.replace(tzinfo=None)
            logout_time = logout_time.replace(tzinfo=None)
            # Add some context.
            logout_time = logout_time - datetime.timedelta(minutes=2)

            messages = self.db.messages.find({
                'timestamp': {'$gt': logout_time, '$lt': login_time}
            })
            messages = list(messages.sort([('_id', -1)]).limit(limit))

            return '\n'.join([
                '[%s %s] %s' % (
                    message['_id'].generation_time.\
                        astimezone(tz.tzlocal()).strftime('%m/%d %X'),
                    nickname(message['user']),
                    message['msg']
                ) for message in reversed(messages)
            ])

        return 'No messages'

    def seen(self, nick):
        messages = self.db.messages.find({
            'user': {'$regex': '^%s' % nick, '$options': 'i'}
        })
        messages = list(messages.sort([('_id', -1)]).limit(1))  # Latest.

        if messages:
            msg = messages[0]
            timestamp = msg['_id'].generation_time.astimezone(tz.tzlocal())
            return '%s was last seen on %s, saying: %s' % (
                nick, timestamp.strftime('%a %b %d %X'), msg['msg']
            )
        else:
            return 'I have not seen %s' % nick


class IRC(BaseHandler):

    def __init__(self):
        self.db = MongoDB()

    def process(self, message):
        event, data = message['event'], message['data']

        # Log all events except private messages.
        if event != 'privmsg' or not data['private']:
            logmethod = 'log_%s' % event
            if hasattr(self.db, logmethod):
                logmethod = getattr(self.db, logmethod)
                logmethod(event, data)

        # Only messages need further processing.
        if event == 'privmsg':
            return self._process_privmsg(data)

    def _process_privmsg(self, data):
        log.debug('Processing %s', data)

        if data['msg'].startswith('!'):
            cmdline = data['msg'][1:].split()
            cmd, params = cmdline[0], cmdline[1:]
            if hasattr(self, cmd):
                try:
                    response = getattr(self, cmd)(data, *params)
                except TypeError as e:
                    log.error('%s', str(e))
                    response = '%s: invalid arguments' % cmd
            else:
                response = 'Command %r not available' % cmd

        else:
            # Check for youtube urls.
            response = '\n'.join([
                self._youtube(url) for url in YOUTUBE_URL.findall(data['msg'])
            ])

        if not response:
            return {}

        if data['private'] or isinstance(response, PrivMsg):
            # Private response.
            receiver = nickname(data['user'])
            prefix = ''
        else:
            # Public response.
            receiver = data['channel']
            prefix = '%s: ' % nickname(data['user'])

        msg = ['%s%s' % (prefix, line) for line in response.split('\n')]
        return {'receiver': receiver, 'msg': msg}

    def backlog(self, data):
        return PrivMsg(self.db.backlog(nickname(data['user'])))

    def quote(self, data, symbol):
        params = {
            'q': urllib.quote(YQL_QUERY % symbol),
            'format': 'json',
            'env': 'store://datatables.org/alltableswithkeys'
        }
        url = YQL_URL % urllib.urlencode(params)
        data = urllib2.urlopen(url).read()
        data = json.loads(data)
        try:
            quote = data[u'query'][u'results'][u'quote']
            name = quote[u'Name']
            ask = quote[u'AskRealtime']
            bid = quote[u'BidRealtime']
        except KeyError:
            return 'Quote for %r not available' % symbol

        return '%s -- Ask: %s, Bid: %s' % (name, ask, bid)

    def seen(self, data, nick):
        return self.db.seen(nick)

    def _youtube(self, url):
        if not url.startswith('http://'):
            url = 'http://%s' % url
        data = urllib2.urlopen(url).read()
        data = BeautifulSoup(
            data,
            convertEntities=BeautifulSoup.HTML_ENTITIES
        )
        title = data.find(id='eow-title')
        return 'Youtube: %s' % title.getText()
