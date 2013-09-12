#!/usr/bin/env python

from irc import irc
from xmlrpc.server import AsyncXMLRPCServer


if __name__ == '__main__':
    server = AsyncXMLRPCServer(('localhost', 8000), allow_none=True)
    server.add_handler(irc)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print 'Exiting'
