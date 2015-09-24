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
        yield from self._queue_recv_put_coro(obj)
        if obj is None:
          break
      else:
        recv_task.cancel()
      if send_task in done:
        obj = send_task.result()
        yield from self.server.queue_from_disp.put(obj)
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
        break
      yield from asyncio.sleep(self.timeout, loop=self.loop)


if __name__ == '__main__':

  class DummyApplication:

    queue_from_disp = queue.Queue()
    queue_to_disp = queue.Queue()

  serverthread = ServerThread(DummyApplication())
  serverthread.start()
