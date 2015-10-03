import asyncio
import json
import logging
import queue
import threading
import zlib

import websockets

from tajf.display.protocol import *
from tajf import threads

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
    self.status_watcher = threads.ConditionWatcherThread(
        self.app.changed_cond,
        lambda: self.loop.call_soon_threadsafe(
            self.on_status_change)
        )
    self.status_watcher.start()
    self.loop.create_task(self.hook_queues())
    self.loop.run_forever()

  @asyncio.coroutine
  def hook_queues(self):
    while True:
      obj = yield from self.server.queue_to_disp.get()
      if obj is None:
        break
      i = obj[0]
      command_obj = (obj[1],) + tuple(obj[2])
      answer_code, exc = self.app.command(*command_obj)
      yield from self.server.queue_from_disp.put(answer_code)
      if answer_code is None:
        break
    self.loop.stop()

  def on_status_change(self):
    status = self.app.status
    #print('+++', status)


#if __name__ == '__main__':
#
#  class DummyApplication:
#
#    queue_from_disp = queue.Queue()
#    queue_to_disp = queue.Queue()
#
#  serverthread = ServerThread(DummyApplication())
#  serverthread.start()
