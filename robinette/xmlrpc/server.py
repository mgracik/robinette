from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import list_public_methods
from SocketServer import ThreadingMixIn
import pydoc

from .util import format_signature, signature


class BaseHandler(object):

    def get_public_method(self, method):
        if method not in list_public_methods(self):
            raise AttributeError('Method %r not available' % method)

        return getattr(self, method)


class _SystemHandler(BaseHandler):

    def __init__(self, xmlrpc_server):
        self._xmlrpc_server = xmlrpc_server

    def get_public_method(self, method):
        try:
            handler_name, method_name = method.split('.')
        except ValueError:
            raise AttributeError('Method %r not available' % method)

        if handler_name in self._xmlrpc_server.register:
            handler = self._xmlrpc_server.register[handler_name]
            try:
                method_obj = BaseHandler.get_public_method(handler, method_name)
            except AttributeError:
                raise AttributeError('Method %r not available' % method)
            return method_obj

        raise AttributeError('Handler %r not available' % handler_name)

    @signature(returns='list')
    def listMethods(self):
        result = set()
        for name, handler in self._xmlrpc_server.register.items():
            methods = list_public_methods(handler)
            methods = set('%s.%s' % (name, method) for method in methods)
            result.update(methods)
        return sorted(result)

    @signature(args=['string'], returns='string')
    def methodHelp(self, method):
        method_obj = self.get_public_method(method)
        return '%s\n\n%s' % (
            self.methodSignature(method),
            pydoc.getdoc(method_obj)
        )

    @signature(args=['string'], returns='string')
    def methodSignature(self, method):
        method_obj = self.get_public_method(method)
        return format_signature(method_obj)


class AsyncXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):

    def __init__(self, *args, **kwargs):
        SimpleXMLRPCServer.__init__(self, *args, **kwargs)
        self._register = {}
        self.add_handler(_SystemHandler(self), 'system')

    def _dispatch(self, method, params):
        system_handler = self._register['system']
        method_obj = system_handler.get_public_method(method)
        return method_obj(*params)

    def add_handler(self, handler, name=None):
        name = name or handler.__class__.__name__.lower()
        if name in self._register:
            raise ValueError('Handler %r already registered' % name)

        self._register[name] = handler

    @property
    def register(self):
        return self._register
