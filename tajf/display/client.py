import asyncio
import datetime
import functools
import json
import threading
from urllib import parse
import zlib

import websockets

from tajf.display.protocol import *


class ClientThread(threading.Thread):

  def __init__(self, port=None, host=None):
    self.port = int(port or DEFAULT_PORT)
    self.host = host or DEFAULT_HOST
    self.task = None
    super().__init__()

  def run(self):
    self.loop = asyncio.new_event_loop()
    self.async = functools.partial(asyncio.async,
        loop=self.loop)
    self.queue = asyncio.Queue(loop=self.loop)
    self.loop.run_until_complete(self.create_client())
    self.loop.run_until_complete(self.waiting_for_commands())
    self.loop.run_until_complete(self.ws.close())
    self.loop.stop()
    self.loop.close()

  @asyncio.coroutine
  def create_client(self):
    url = get_url()
    self.ws = yield from websockets.connect(url,
        loop=self.loop)

  @asyncio.coroutine
  def waiting_for_commands(self):
    while True:
      listener_task = self.loop.create_task(self.ws.recv())
      producer_task = self.loop.create_task(self.queue.get())
      done, pending = yield from asyncio.wait(
        [listener_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
        loop=self.loop)

      if listener_task in done:
        message = listener_task.result()
        if not message:
          break
        self.on_message(message)
      else:
        listener_task.cancel()

      if producer_task in done:
        obj = producer_task.result()
        if obj is None:
          break
        else:
          if self.task is not None:
            self.task.cancel()
          data = json.dumps(obj).encode('utf-8')
          data = zlib.compress(data)
          self.task = self.loop.create_task(self.ws.send(data))
      else:
        producer_task.cancel()

  def command(self, obj):
    self.loop.call_soon_threadsafe(self.async,
        self.queue.put(obj))

  def on_message(self, message):
    print(message)
