import asyncio
import datetime
import functools
import json
import queue
import threading
from urllib import parse
import zlib

import websockets

from tajf.display.protocol import *


class ClientThread(threading.Thread):

  DEFAULT_TIMEOUT = 0.001

  def __init__(self, queue_recv=None, queue_send=None,
      port=None, host=None, timeout=DEFAULT_TIMEOUT):
    self.queue_recv = queue_recv or queue.Queue()
    self.queue_send = queue_send or queue.Queue()
    self.port = int(port or DEFAULT_PORT)
    self.host = host or DEFAULT_HOST
    self.task = None
    self.timeout = timeout
    super().__init__()

  def run(self):
    self.loop = asyncio.new_event_loop()
    self.on_connecting()
    self.client = TajfDisplayClient(host=self.host,
        port=self.port, loop=self.loop)
    try:
      self.loop.run_until_complete(self.client.connect())
    except OSError as err:
      self.on_connection_failed()
      self.loop.close()
    else:
      self.on_connected()
      self.loop.create_task(self.hook_queues())
      self.loop.run_forever()
      self.on_disconnecting()
      try:
        self.loop.run_until_complete(self.client.stop())
      except:
        pass
      self.on_disconnected()
      self.loop.close()

  def stop(self):
    self.queue_send.put(None)

  @asyncio.coroutine
  def hook_queues(self):
    while True:
      recv_task = self.loop.create_task(self.client.recv())
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
        yield from self.client.send(obj)
        if obj is None:
          break
      else:
        send_task.cancel()
    self.loop.stop()

  @asyncio.coroutine
  def _queue_send_get_coro(self):
    while True:
      try:
        obj = self.queue_send.get_nowait()
      except queue.Empty:
        pass
      else:
        print('csg', obj)
        return obj
      yield from asyncio.sleep(self.timeout, loop=self.loop)

  @asyncio.coroutine
  def _queue_recv_put_coro(self, obj):
    while True:
      try:
        self.queue_recv.put_nowait(obj)
      except queue.Full:
        pass
      else:
        print('crp', obj)
        break
      yield from asyncio.sleep(self.timeout, loop=self.loop)

  def on_connecting(self):
    pass

  def on_connected(self):
    pass

  def on_connection_failed(self):
    pass

  def on_disconnecting(self):
    pass

  def on_disconnected(self):
    pass

  def on_message(self, message):
    print('cmsg', message)
