import asyncio
import websockets
import json
import logging
import threading
import zlib

from tajf.display.protocol import *


logger = logging.getLogger('websockets.server')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class ServerThread(threading.Thread):

  def __init__(self, application, port=None, host=None):
    self._application = application
    self.port = int(port or DEFAULT_PORT)
    self.host = host or DEFAULT_HOST
    super().__init__()

  @property
  def queue(self):
    return self._application.queue

  def run(self):
    self.loop = asyncio.new_event_loop()
    self.loop.run_until_complete(self.create_server())
    self.loop.run_forever()

  @asyncio.coroutine
  def create_server(self):
    self.server = yield from websockets.serve(self.ws_handler,
        self.host, self.port, loop=self.loop)

  @asyncio.coroutine
  def ws_handler(self, ws_server_proto, uri):
    while True:
      compressed_data = yield from ws_server_proto.recv()
      if not compressed_data:
        break
      data = zlib.decompress(compressed_data)
      obj = json.loads(data.decode('utf-8'))
      # print("< {!r}".format(obj))
      self.queue.put(obj)


if __name__ == '__main__':

  class DummyApplication:
    pass

  serverthread = ServerThread(DummyApplication())
  serverthread.start()
