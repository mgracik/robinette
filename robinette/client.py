#!/usr/bin/env python

import argparse
import functools
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('robinette.client')
import socket
import xmlrpclib

import twisted
from twisted.internet import protocol, reactor
from twisted.words.protocols import irc


def catch_socket_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except socket.error as e:
            params = args + tuple('%s=%r' % arg for arg in kwargs.items())
            log.error(
                '%s(%s) raised %s',
                func.__name__,
                ', '.join(map(str, params)),
                str(e)
            )
    return wrapper


class IRCClient(irc.IRCClient):

    def signedOn(self):
        log.info('Signed on as %s', self.nickname)
        self.join(self.channel)

    def joined(self, channel):
        log.info('Joined %s', channel)

    def privmsg(self, user, channel, msg):
        message = {
            'event': 'privmsg',
            'data': {
                'user': user,
                'channel': channel,
                'msg': msg,
                'private': channel == self.nickname
            }
        }
        self.dispatch(message)

    def userJoined(self, user, channel):
        message = {
            'event': 'user_join',
            'data': {
                'user': user,
                'channel': channel
            }
        }
        self.dispatch(message)

    def userLeft(self, user, channel):
        message = {
            'event': 'user_left',
            'data': {
                'user': user,
                'channel': channel
            }
        }
        self.dispatch(message)

    def userQuit(self, user, quit_msg):
        message = {
            'event': 'user_quit',
            'data': {
                'user': user,
                'quit_msg': quit_msg
            }
        }
        self.dispatch(message)

    @catch_socket_errors
    def dispatch(self, message):
        log.debug('Received %s', message)
        response = self.proxy.irc.process(message)
        if response:
            self.respond(response)

    def respond(self, response):
        log.debug('Sending %s', response)
        wait = 1 if len(response['msg']) > 5 else 0
        for line in response['msg']:
            if isinstance(line, unicode):
                line = line.encode('utf-8')
            self.msg(response['receiver'], line)
            if wait:
                time.sleep(wait)

    @property
    def nickname(self):
        return self.factory.nickname

    @property
    def channel(self):
        return self.factory.channel

    @property
    def proxy(self):
        return self.factory.proxy


class IRCClientFactory(protocol.ClientFactory):

    protocol = IRCClient

    def __init__(self, nickname, channel, proxy_addr=('localhost', 8000)):
        self.nickname = nickname
        self.channel = channel
        self.proxy = xmlrpclib.ServerProxy('http://%s:%s/RPC2' % proxy_addr)

    def clientConnectionFailed(self, connector, reason):
        log.warning('Client connection failed: %s', reason)
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        log.warning('Client connection lost: %s', reason)
        try:
            reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            # Already stopped.
            pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', default='irc.freenode.net')
    parser.add_argument('-p', '--port', default=6667)
    parser.add_argument('-n', '--nickname', default='rob1n3tt3')
    parser.add_argument('-c', '--channel', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.channel.startswith('#'):
        channel = args.channel
    else:
        channel = '#%s' % args.channel

    client = IRCClientFactory(args.nickname, channel)
    reactor.connectTCP(args.server, args.port, client)
    reactor.run()
