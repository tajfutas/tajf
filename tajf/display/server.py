import asyncio
import websockets
import json
import logging
import threading
import zlib

from tajf.display.protocol import *

IDLE_FLAG = b'\x01'

logger = logging.getLogger('websockets.server')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class ServerThread(threading.Thread):

  def __init__(self, application, port=None, host=None):
    self.app = application
    self.port = int(port or DEFAULT_PORT)
    self.host = host or DEFAULT_HOST
    self.idle_flag_sent = False
    super().__init__()

  @property
  def queue(self):
    return self.app.queue

  def run(self):
    self.loop = asyncio.new_event_loop()
    self.idle_queue = asyncio.Queue(loop=self.loop)
    self.loop.run_until_complete(self.create_server())
    self.loop.create_task(self.notify_display_idle())
    self.loop.run_forever()

  @asyncio.coroutine
  def create_server(self):
    self.server = yield from websockets.serve(self.ws_handler,
        self.host, self.port, loop=self.loop)

  @asyncio.coroutine
  def ws_handler(self, ws_server_proto, uri):
    while True:
      listener_task = self.loop.create_task(
        ws_server_proto.recv())
      producer_task = self.loop.create_task(
        self.idle_queue.get())
      done, pending = yield from asyncio.wait(
        [listener_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
        loop=self.loop)

      if listener_task in done:
        compressed_data = listener_task.result()
        if not compressed_data:
          break
        data = zlib.decompress(compressed_data)
        obj = json.loads(data.decode('utf-8'))
        self.queue.put(obj)
      else:
        listener_task.cancel()

      if producer_task in done:
        message = producer_task.result()
        if not ws_server_proto.open:
            break
        yield from ws_server_proto.send(message)
      else:
        producer_task.cancel()

  @asyncio.coroutine
  def notify_display_idle(self):
    while True:
      if self.app.idle.is_set():
        if not self.idle_flag_sent:
          yield from self.idle_queue.put(IDLE_FLAG)
          self.idle_flag_sent = True
      else:
        self.idle_flag_sent = False
      yield from asyncio.sleep(0.01, loop=self.loop)

if __name__ == '__main__':

  class DummyApplication:
    pass

  serverthread = ServerThread(DummyApplication())
  serverthread.start()
