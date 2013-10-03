import inspect
from itertools import izip_longest


def format_signature(func):
    if not hasattr(func, '_signature'):
        func._signature = {'args': [], 'returns': None}

    argspec = inspect.getargspec(func)
    args = izip_longest(
        argspec.args[::-1],
        argspec.defaults[::-1],
        fillvalue=''
    )[::-1]
    args = ['%s=%s' % (arg, default) if default else arg for arg, default in args]

    return '%s(%s) -> %s' % (
        func.__name__,
        ', '.join(
            '%s %s' % arg for arg in
            izip_longest(func._signature['args'], args)
        ),
        func._signature['returns']
    )


def signature(args=None, returns=None):
    def _signature(func):
        func._signature = {'args': args or [], 'returns': returns}
        return func
    return _signature
