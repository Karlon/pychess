import inspect

from pychess.compat import basestring


def fident (f):
    '''
    Get an identifier for a function or method
    '''
    joinchar = '.'
    if hasattr(f, 'im_class'):
        fparent = f.im_class.__name__
    else:
        joinchar = ':'
        fparent = f.__module__.split('.')[-1]

    lineno = inspect.getsourcelines(f)[1]
    fullname = joinchar.join((fparent, f.__name__))
    return ':'.join((fullname, str(lineno)))

def get_threadname (thread_namer):
    if isinstance(thread_namer, basestring):
        return thread_namer
    else:
        return fident(thread_namer)
