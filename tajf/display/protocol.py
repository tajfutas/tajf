import asyncio
import collections
import json
import struct
from urllib import parse
import zlib

import websockets
import websockets.server

DEFAULT_SERVER_IP = '0.0.0.0'
DEFAULT_CLIENT_IP = '127.0.0.1'
DEFAULT_PORT = 3177

SCHEME = 'ws'
PATH = '/'
PARAMS = ''
QUERY = ''
FRAGMENT = ''

PEERNAME_STRUCT_FMT = '<4BH'

# codes
# C_STATUSREQ = b'\xC5'
C_SHOW = b'\xC5'
C_CLOSE = b'\xCC'
A_ACCEPTED = b'\xAA'
A_DENIED = b'\xAD'
A_ERROR = b'\xAE'
# A_STATUSREP = b'\xA5'
D_STATUSUPD = b'\xD5'


def peername2peerobj(peername):
  ip_addr, port = peername
  return [int(x) for x in ip_addr.split('.')] + [port]

def peerdata2peerobj(peerdata):
  return list(struct.unpack(PEERNAME_STRUCT_FMT, peerdata))

def peerobj2peerdata(peerobj):
  return struct.pack(PEERNAME_STRUCT_FMT, *peerobj)

def peerobj2peername(peerobj):
  ip_addr = '.'.join([str(x) for x in peerobj[:4]])
  port = peerobj[4]
  return ip_addr, port


def get_netloc(host=None, port=None):
  host = (host if host is not None else DEFAULT_CLIENT_IP)
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


class ProtocolError(Exception):
  pass

class WsSubprotocol:

  name = None

  def __init__(self, loop=None):
    self.loop = loop or asyncio.get_event_loop()
    super().__init__()

  async def __call__(self, ws_proto, uri=None):
    if ws_proto.is_client:
      await self.ws_handle_client(ws_proto, uri)
    else:
      await self.ws_handle_server(ws_proto, uri)


class TajfDisplaySubprotocol(WsSubprotocol):

  name = 'tajf-display.1'

  async def task_wait_loop(self, ws_proto, coro_funcs,
      handle_name_fs):
    tasks = {self.loop.create_task(cf()): k
        for k, cf in coro_funcs.items()}
    while True:
      done, pending = await asyncio.wait(
        list(tasks.keys()),
        return_when=asyncio.FIRST_COMPLETED,
        loop=ws_proto.loop)
      for t in done:
        k = tasks[t]
        handler_name = handle_name_fs.format(k)
        handler_coro = getattr(self, handler_name)
        result = await handler_coro(ws_proto, t)
        if result == 'BREAK':
          return
        else:
          del tasks[t]
          tasks[self.loop.create_task(coro_funcs[k]())] = k

  async def ws_handle_server(self, ws_proto, uri):
    # register the protocol at server
    ws_proto.ws_server.peers.add(ws_proto)
    coro_funcs = {
      'on_request': ws_proto.recv,
      #'on_display_response':
      #    ws_proto.ws_server.queue_from_disp.get,
      'on_response': ws_proto.queue_send.get,
    }
    handle_name_fs = 'ws_handle_server_{}'
    await self.task_wait_loop(ws_proto, coro_funcs,
        handle_name_fs)
    # deregister the protocol at server
    ws_proto.ws_server.peers.remove(ws_proto)

  async def ws_handle_server_on_request(self, ws_proto, task):
    #await ws_proto.lock.acquire()  # TODO: Temporary
    data = task.result()
    print('server req', data)
    if not data:
      return 'BREAK'
    code = data[:1]
    if code in (C_SHOW, C_CLOSE):
      payload_data = zlib.decompress(data[1:])
      payload_obj = json.loads(payload_data.decode('utf-8'))
      #print('*******', payload_obj)
    else:
      errfs = 'invalid client request code: {X}'
      raise ProtocolError(errfs.format(code[0]))
    i = ws_proto.ws_server.i
    ws_proto.ws_server.peers_by_i[i] = ws_proto
    obj = i, code, payload_obj
    await ws_proto.ws_server.queue_to_disp.put(obj)

  async def ws_handle_server_on_display_response(self, ws_proto,
      task):
    return  # TEMPORARY
    obj = task.result()
    code = obj[0]
    if code in (A_ACCEPTED, A_DENIED, A_ERROR):
      i = obj[1]
      ws_proto = ws_proto.ws_server.peers_by_i[i]
      del ws_proto.ws_server.peers_by_i[i]
      answer_data = code
      if code == A_ERROR:
        payload_data = json.dumps(obj[2]).encode('utf-8')
        compessed_payload_data = zlib.compress(payload_data)
        answer_data += compessed_payload_data
      await ws_proto.queue_send.put(answer_data)
      ws_proto.lock.release()
    elif code == D_STATUSUPD:
      payload_data = json.dumps(obj[1]).encode('utf-8')
      compessed_payload_data = zlib.compress(payload_data)
      data = code + compessed_payload_data
      # broadcast it
      for p in ws_proto.ws_server.peers:
        await p.queue_send.put(data)
    else:
      errfs = 'invalid display response code: {X}'
      raise ProtocolError(errfs.format(code[0]))

  async def ws_handle_server_on_response(self, ws_proto, task):
    data = task.result()
    if not ws_proto.open:
      return 'BREAK'
    await ws_proto.send(data)

  async def ws_handle_client(self, ws_proto, uri):
    coro_funcs = {
      'on_response': ws_proto.recv,
      'on_request': ws_proto.queue_send.get,
    }
    handle_name_fs = 'ws_handle_client_{}'
    await self.task_wait_loop(ws_proto, coro_funcs,
        handle_name_fs)

  async def ws_handle_client_on_response(self, ws_proto, task):
    return  # TEMPORARY
    data = task.result()
    if not data:
      return 'BREAK'
    code = data[:1]
    if code in (A_ACCEPTED, A_DENIED):
      #ws_proto.lock.release()
      obj = data,
    elif code == D_STATUSUPD:
      payload_data = zlib.decompress(data[1:])
      payload_obj = json.loads(payload_data.decode('utf-8'))
      obj = data, payload_obj
    else:
      errfs = 'invalid server response code: {X}'
      raise ProtocolError(errfs.format(code[0]))
    await ws_proto.queue_recv.put(obj)

  async def ws_handle_client_on_request(self, ws_proto, task):
    #await ws_proto.lock.acquire()
    obj = task.result()
    if not ws_proto.open:
      return 'BREAK'
    if obj in (None, b''):
      data = b''
    else:
      code = obj[0]
      if code in (C_SHOW, C_CLOSE):
        print('itt', obj[1:])
        payload_data = json.dumps(obj[1:]).encode('utf-8')
        compessed_payload_data = zlib.compress(payload_data)
        data = code + compessed_payload_data
      else:
        errfs = 'invalid client request code: {X}'
        raise ProtocolError(errfs.format(code[0]))
    await  ws_proto.send(data)
    if data == b'':
      return 'BREAK'

class WsSubprotocolHandler:

  def __init__(self, subprotocols=None):
    self.subprotocols = {}
    if subprotocols:
      for i, p in enumerate(subprotocols):
        self.add_subprotocol((i+1) * 100, p)

  def add_subprotocol(self, priority, subprotocol):
    name = subprotocol.name
    if name in self.subprotocols:
      errfs = 'subprotocol is already registered: {}'
      raise ValueError(errfs.format(name))
    else:
      self.subprotocols[name] = (priority, subprotocol)

  async def __call__(self, ws_proto, uri=None):
    subprotocol_name = ws_proto.subprotocol
    priority, ws_handler = self.subprotocols[subprotocol_name]
    await ws_handler(ws_proto, uri)

  def namelist(self):
    return [i[0] for i in sorted(self.subprotocols.items(),
        key=lambda i: (i[1][0], i[0]))]


class TajfDisplayServerProtocol(
    websockets.WebSocketServerProtocol):

  is_client = False

  def __init__(self, *args, **kwds):
    super().__init__(*args, **kwds)
    self.loop = self.ws_server.loop
    self.n = -1
    self.lock = asyncio.Lock(loop=self.loop)
    self.queue_send = asyncio.Queue(loop=self.loop)

  def client_connected(self, reader, writer):
    super().client_connected(reader, writer)

  def connection_made(self, transport):
    super().connection_made(transport)


class TajfDisplayClientProtocol(
    websockets.WebSocketClientProtocol):

  is_client = True

  def __init__(self, *args, **kwgs):
    super().__init__(*args, **kwgs)
    self.lock = asyncio.Lock(loop=self.loop)
    self.queue_recv = asyncio.Queue(loop=self.loop)
    self.queue_send = asyncio.Queue(loop=self.loop)

class AutoIncrement:
  def __init__(self, start_value=-1):
    self._value = start_value

  def __get__(self, inst, cls):
    self._value += 1
    return self._value

  def __set__(self, inst, value):
    raise AttributeError('Can\'t set attribute')

  def __delete__(self, inst):
    raise AttributeError('Can\'t delete attribute')


class TajfDisplayServer(websockets.server.WebSocketServer):

  i = AutoIncrement()

  def __init__(self, *, ws_handler=None, host=None, port=None,
      loop=None, proto_class=TajfDisplayServerProtocol,
      origins=None, extra_headers=None):
    super().__init__(loop=loop)
    if self.loop is None:
      self.loop = asyncio.get_event_loop()
    self.server = None

    if ws_handler is None:
      subprotocols = [TajfDisplaySubprotocol(self.loop)]
      self.ws_handler = WsSubprotocolHandler(subprotocols)
    else:
      self.ws_handler = ws_handler

    self.host = host or DEFAULT_SERVER_IP
    self.port = port or DEFAULT_PORT
    self.proto_class = proto_class
    self.origins = origins
    self.extra_headers = extra_headers
    self.queue_to_disp = asyncio.Queue(loop=self.loop)
    self.queue_from_disp = asyncio.Queue(loop=self.loop)
    self.peers = set()
    self.peers_by_i = {}

  def start(self, **kwds):
    self.loop.create_task(self.serve(**kwds))

  def stop(self):
    if self.server is not None:
      self.close()
      return self.loop.create_task(self.wait_closed())

  # based on websockets.server.serve()
  @asyncio.coroutine
  async def serve(self, **kwds):
    self.secure = kwds.get('ssl') is not None
    self.wrap((await self.loop.create_server(self.factory,
      self.host, self.port, **kwds)))
    return self.server

  def factory(self):
    factory = self.proto_class(
      self.ws_handler,
      self,
      host=self.host,
      port=self.port,
      secure=self.secure,
      origins=self.origins,
      subprotocols=self.ws_handler.namelist(),
      extra_headers=self.extra_headers,
      loop=self.loop)
    return factory


class TajfDisplayClient:

  def __init__(self, *, ws_handler=None, host=None, port=None,
    loop=None, class_=TajfDisplayClientProtocol, origin=None,
    extra_headers=None):
    self._ws_proto = None
    self.loop = loop or asyncio.get_event_loop()
    if ws_handler is None:
      subprotocols = [TajfDisplaySubprotocol(self.loop)]
      self.ws_handler = WsSubprotocolHandler(subprotocols)
    else:
      self.ws_handler = ws_handler
    self.host = host or DEFAULT_CLIENT_IP
    self.port = port or DEFAULT_PORT
    self.class_ = class_
    self.origin = origin
    self.extra_headers = extra_headers

  def start(self, **kwds):
    return self.loop.create_task(self.connect(**kwds))

  def stop(self):
    if self._ws_proto is not None:
      return self.loop.create_task(self.send(None))

  async def recv(self):
    recv_obj = await self._ws_proto.queue_recv.get()
    return recv_obj

  async def send(self, obj):
    return (await self._ws_proto.queue_send.put(obj))

  async def connect(self, **kwds):
    uri = get_url(host=self.host, port=self.port)
    self._ws_proto = await websockets.connect(uri,
      loop=self.loop, klass=self.class_, origin=self.origin,
      subprotocols=self.ws_handler.namelist(),
      extra_headers=self.extra_headers,
      **kwds)
    self.loop.create_task(self.ws_handler(self._ws_proto))
    return self._ws_proto


if __name__ == '__main__':

  import sys
  loop = asyncio.get_event_loop()
  if sys.argv[1] == 's':
    s = loop.run_until_complete(serve(loop=loop))
  elif sys.argv[1] == 'c':
    ws_proto = loop.run_until_complete(connect(loop=loop))
    loop.create_task(ws_handler(ws_proto))
  loop.run_forever()
