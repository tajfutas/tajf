import asyncio
import datetime
import json
from urllib import parse
import zlib

import websockets

from tajf.display.protocol import *

@asyncio.coroutine
def hello():
  url = get_url()
  print(url)
  websocket = yield from websockets.connect(url)
  name = 'Hello'
  yield from websocket.send(name)
  print("> {}".format(name))

@asyncio.coroutine
def static():
  url = get_url()
  websocket = yield from websockets.connect(url)
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
  yield from websocket.send(data)
  yield from asyncio.sleep(5)
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
  yield from websocket.send(data)
  # print("> {!r}".format(obj))

@asyncio.coroutine
def highlight():
  url = get_url()
  websocket = yield from websockets.connect(url)
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
  yield from websocket.send(data)
  yield from asyncio.sleep(22)
  obj = {'mode': 'highlight_punch',
         'punch_time': True}
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  yield from websocket.send(data)

asyncio.get_event_loop().run_until_complete(highlight())
