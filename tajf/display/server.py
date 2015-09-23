import asyncio
import json
import logging
import queue
import threading
import zlib

import websockets

from tajf.display.protocol import *

logger = logging.getLogger('websockets.server')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class ServerThread(threading.Thread):

  DEFAULT_TIMEOUT = 0.001

  def __init__(self, application, port=None, host=None,
      timeout=DEFAULT_TIMEOUT):
    self.app = application
    self.port = int(port or DEFAULT_PORT)
    self.host = host or DEFAULT_HOST
    self.timeout = timeout
    super().__init__()

  def run(self):
    self.loop = asyncio.new_event_loop()
    self.server = TajfDisplayServer(host=self.host,
        port=self.port, loop=self.loop)
    print('server.py', object.__repr__(self.server))
    self.loop.run_until_complete(self.server.serve())
    self.loop.create_task(self.hook_queues())
    self.loop.run_forever()

  @asyncio.coroutine
  def hook_queues(self):
    while True:
      recv_task = self.loop.create_task(
          self.server.queue_to_disp.get())
      send_task = self.loop.create_task(
          self._queue_send_get_coro())
      done, pending = yield from asyncio.wait(
          [recv_task, send_task],
          return_when=asyncio.FIRST_COMPLETED,
          loop=self.loop)
      if recv_task in done:
        obj = recv_task.result()
        print('server.py', 'yield from self._queue_recv_put_coro(obj)', '...')
        yield from self._queue_recv_put_coro(obj)
        print('server.py', 'yield from self._queue_recv_put_coro(obj)', 'OK')
        if obj is None:
          break
      else:
        recv_task.cancel()
      if send_task in done:
        obj = send_task.result()
        print('server.py', 'yield from self.server.queue_from_disp.put(obj)', '...')
        yield from self.server.queue_from_disp.put(obj)
        print('server.py', 'yield from self.server.queue_from_disp.put(obj)', 'OK')
        if obj is None:
          break
      else:
        send_task.cancel()
    self.loop.stop()

  @asyncio.coroutine
  def _queue_send_get_coro(self):
    while True:
      try:
        obj = self.app.queue_send.get_nowait()
      except queue.Empty:
        pass
      else:
        print('aqsg', obj)
        return obj
      yield from asyncio.sleep(self.timeout, loop=self.loop)

  @asyncio.coroutine
  def _queue_recv_put_coro(self, obj):
    while True:
      try:
        self.app.queue_recv.put_nowait(obj)
      except queue.Full:
        pass
      else:
        print('aqrp', obj)
        break
      yield from asyncio.sleep(self.timeout, loop=self.loop)








#  @asyncio.coroutine
#  def create_server(self):
#    self.server = yield from websockets.serve(self.ws_handler,
#        self.host, self.port, loop=self.loop)
#
#  @asyncio.coroutine
#  def ws_handler(self, ws_server_proto, uri):
#    print('*', ws_server_proto.host, ws_server_proto.port, ws_server_proto.reader._transport._sock.getpeername(), ws_server_proto.writer._transport._sock.getsockname())
#    while True:
#      listener_task = self.loop.create_task(
#        ws_server_proto.recv())
#      producer_task = self.loop.create_task(
#        self.idle_queue.get())
#      done, pending = yield from asyncio.wait(
#        [listener_task, producer_task],
#        return_when=asyncio.FIRST_COMPLETED,
#        loop=self.loop)
#
#      if listener_task in done:
#        compressed_data = listener_task.result()
#        if not compressed_data:
#          break
#        data = zlib.decompress(compressed_data)
#        obj = json.loads(data.decode('utf-8'))
#        self.queue.put(obj)
#      else:
#        listener_task.cancel()
#
#      if producer_task in done:
#        message = producer_task.result()
#        if not ws_server_proto.open:
#            break
#        yield from ws_server_proto.send(message)
#      else:
#        producer_task.cancel()
#
#  @asyncio.coroutine
#  def notify_display_idle(self):
#    while True:
#      if self.app.idle.is_set():
#        if not self.idle_flag_sent:
#          yield from self.idle_queue.put(IDLE_FLAG)
#          self.idle_flag_sent = True
#      else:
#        self.idle_flag_sent = False
#      yield from asyncio.sleep(0.01, loop=self.loop)

if __name__ == '__main__':

  class DummyApplication:

    queue_from_disp = queue.Queue()
    queue_to_disp = queue.Queue()

  serverthread = ServerThread(DummyApplication())
  serverthread.start()
