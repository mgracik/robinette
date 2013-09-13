#!/usr/bin/env python

import argparse
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
import xmlrpclib

import twisted
from twisted.internet import protocol, reactor
from twisted.words.protocols import irc


class IRCClient(irc.IRCClient):

    @staticmethod
    def nick(user):
        return user.split('!')[0]

    def signedOn(self):
        log.info('Signed on as %s', self.nickname)
        self.join(self.channel)

    def joined(self, channel):
        log.info('Joined %s', channel)

    def privmsg(self, user, channel, msg):
        msg = dict(user=user, channel=channel, msg=msg)
        # log.debug('Received %s', msg)
        # INFO:__main__:Received {'msg': 'lalala', 'user': 'mgracik!~mgracik@proxy.seznam.cz', 'channel': '#finishers'}
        # INFO:__main__:Received {'msg': 'r0b1n3tt3: bla bla bla', 'user': 'mgracik!~mgracik@proxy.seznam.cz', 'channel': '#finishers'}
        self.proxy.irc.log('msg', msg)
        self.dispatch(msg)

    def userJoined(self, user, channel):
        data = dict(user=user, channel=channel)
        self.proxy.irc.log('user_join', data)

    def userLeft(self, user, channel):
        data = dict(user=user, channel=channel)
        self.proxy.irc.log('user_left', data)

    def userQuit(self, user, quit_msg):
        data = dict(user=user, quit_msg=quit_msg)
        self.proxy.irc.log('user_quit', data)

    def dispatch(self, msg):
        available_methods = self.proxy.system.listMethods()
        available_methods.remove('irc.log')  # Do not expose the log method.
        response = None

        if msg['msg'].startswith(self.nickname):
            respond_to = msg['msg'][len(self.nickname):]
            if respond_to[0] in (':', ','):
                respond_to = respond_to[1:]
            response = self.proxy.irc.respond(respond_to.strip())

        elif msg['msg'].startswith('!'):
            cmdline = msg['msg'][1:].split()
            cmd, params = cmdline[0], cmdline[1:]
            if cmd == 'help':
                if not params:
                    methods = [m[4:] for m in available_methods if m.startswith('irc.')]
                    response = ', '.join(methods)
                else:
                    method = 'irc.%s' % params[0]
                    if method in available_methods:
                        response = self.proxy.system.methodHelp(method)
            elif 'irc.%s' % cmd in available_methods:
                method_obj = getattr(self.proxy.irc, cmd)
                response = method_obj(*params)

        if response:
            self.respond(msg, response)

    def respond(self, msg, response):
        self.msg(
            msg['channel'],
            '%s: %s' % (self.nick(msg['user']), response)
        )

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
        self.proxy = xmlrpclib.ServerProxy('http://%s:%s/RPC2' % (proxy_addr))

    def clientConnectionFailed(self, connector, reason):
        log.warning('Client connection failed')
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        log.warning('Client connection lost')
        try:
            reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            # Already stopped.
            pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server', default='irc.freenode.net')
    parser.add_argument('-p', '--port', default=6667)
    parser.add_argument('-n', '--nickname', default='r0b1n3tt3')
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
