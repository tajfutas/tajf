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
      f = yield from self.queue.get()
      if f is None:
        break
      else:
        if self.task is not None:
          self.task.cancel()
        self.task = self.loop.create_task(f(self.ws, self.loop))

  def command(self, f):
    self.loop.call_soon_threadsafe(self.async,
        self.queue.put(f))


def applydefs(f):
  @asyncio.coroutine
  @functools.wraps(f)
  def wrapper(ws=None, loop=None, **kwds):
    if loop is None:
      loop = asyncio.get_event_loop()
    if ws is None:
      url = get_url(**kwds)
      ws = yield from websockets.connect(url, loop=loop)
    yield from f(ws, loop)
  return wrapper


@asyncio.coroutine
@applydefs
def static(ws=None, loop=None):
  obj = {'mode': 'static',
    'head': {'style': 'blue', 'values': ['NYT', 'cél']},
    'table': [
      {'values': [1, 'Dalos Máté', 'SPA', '37:31']},
      {'values': [2, 'Tóth Tamás', 'TTE', '41:55']},
      {'values': [3, 'Lajtai Zoltán', 'PVM', '43:23']},
      ],
    }
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  yield from ws.send(data)
  yield from asyncio.sleep(5, loop=loop)
  obj = {'mode': 'static',
    'head': {'style': 'red', 'values': ['NYT', '21']},
    'table': [
      {'values': [1, 'Akárki', 'AKA', '37:31']},
      {'values': [2, 'Tóth Tamás', 'TTE', '41:55']},
      {'values': [3, 'Lajtai Zoltán', 'PVM', '43:23']},
      ],
    }
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  yield from ws.send(data)
  # print("> {!r}".format(obj))


@asyncio.coroutine
@applydefs
def punch(ws=None, loop=None):
  obj = {'mode': 'punch',
    'head': {'style': 'blue', 'values': ['NYT', 'cél']},
    'table': [
      {'values': [1, 'Dalos Máté', 'SPA', '37:31']},
      {'values': [2, 'Tóth Tamás', 'TTE', '41:55']},
      {'values': [3, 'Lajtai Zoltán', 'PVM', '43:23']},
      ],
    'punch_pos': 2,
    }
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  yield from ws.send(data)


@asyncio.coroutine
@applydefs
def highlight(ws=None, loop=None):
  now = datetime.datetime.now()
  td = datetime.timedelta(minutes=37, seconds=21)
  hstart = now - td
  obj = {'mode': 'highlight',
    'head': {'style': 'blue', 'values': ['F30', 'cél']},
    'table': [
      {'values': [1, 'Dalos Máté', 'SPA', '37:31']},
      {'values': [2, 'Tóth Tamás', 'TTE', '37:39']},
      {'values': [3, 'Lajtai Zoltán', 'PVM', '43:23']},
      ],
    'highlighted': ['Mutatott Ferenc', 'X!X'],
    'highlighted_start': hstart.isoformat(),
    }
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  yield from ws.send(data)
  yield from asyncio.sleep(22, loop=loop)
  obj = {'mode': 'highlight_punch',
         'punch_time': True}
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  yield from ws.send(data)

if __name__ == '__main__':
  clientthread = ClientThread()
  clientthread.start()

  shortcuts = {
    'h': highlight,
    'p': punch,
    's': static,
  }

  input_ = None
  while input_ != 'q':
    input_ = input('Shortcut letter?  >  ')
    if input_ == 'q':
      clientthread.command(None)
      continue
    if input_ not in shortcuts:
      keys = ', '.join(sorted(shortcuts.keys()))
      print('Valid shortcuts: ' + keys)
      continue
    else:
      clientthread.command(shortcuts[input_])

