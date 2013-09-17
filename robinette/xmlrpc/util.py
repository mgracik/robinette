def format_signature(func):
    if not hasattr(func, '_signature'):
        return '%s -- signature not available' % func.__name__

    return '%s(%s) -> %s' % (
        func.__name__,
        ', '.join(func._signature['args']),
        func._signature['returns']
    )


def signature(args=None, returns=None):
    def _signature(func):
        func._signature = {'args': args or [], 'returns': returns}
        return func
    return _signature
