from urllib import parse

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 3177

SCHEME = 'ws'
PATH = '/'
PARAMS = ''
QUERY = ''
FRAGMENT = ''


def get_netloc(host=None, port=None):
  host = (host if host is not None else DEFAULT_HOST)
  port = (port if port is not None else DEFAULT_PORT)
  return '{}:{}'.format(host, port)


def get_url(*, host=None, port=None, _scheme=None, _path=None,
    _params=None, _query=None, _fragment=None):
  """Returns the URL of a Websocket command."""
  _scheme = (_scheme if _scheme is not None else SCHEME)
  _netloc = get_netloc(host, port)
  _path = (_path if _path is not None else PATH)
  _params = (_params if _params is not None else PARAMS)
  _query = (_query if _query is not None else QUERY)
  _fragment = (_fragment if _fragment is not None else FRAGMENT)
  pr = parse.ParseResult(_scheme, _netloc, _path, _params,
      _query, _fragment)
  return pr.geturl()
