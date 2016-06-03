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

  async def create_client(self):
    url = get_url()
    self.ws = await websockets.connect(url,
        loop=self.loop)

  async def waiting_for_commands(self):
    while True:
      listener_task = self.loop.create_task(self.ws.recv())
      producer_task = self.loop.create_task(self.queue.get())
      done, pending = await asyncio.wait(
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
        f = producer_task.result()
        if f is None:
          break
        else:
          if self.task is not None:
            self.task.cancel()
          self.task = self.loop.create_task(f(self.ws, self.loop))
      else:
        producer_task.cancel()

  def command(self, f):
    self.loop.call_soon_threadsafe(self.async,
        self.queue.put(f))

  def on_message(self, message):
    pass


def applydefs(f):
  @functools.wraps(f)
  async def wrapper(ws=None, loop=None, **kwds):
    if loop is None:
      loop = asyncio.get_event_loop()
    if ws is None:
      url = get_url(**kwds)
      ws = await websockets.connect(url, loop=loop)
    await f(ws, loop)
  return wrapper


@applydefs
async def highlight(ws=None, loop=None):
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
  await ws.send(data)
  await asyncio.sleep(22, loop=loop)
  obj = {'mode': 'highlight_punch',
         'punch_time': True}
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  await ws.send(data)


@applydefs
async def punch(ws=None, loop=None):
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
  await ws.send(data)


@applydefs
async def results(ws=None, loop=None):
  obj = {'mode': 'results',
    'head': {'style': 'blue', 'values': ['F21E', '']},
    'table': [
      {'values': [1, 'Baumholczer Máté', 'PVS', '1:25:14']},
      {'values': [2, 'Bakó Áron', 'SPA', '1:25:17']},
      {'values': [3, 'Gösswein Csaba', 'PSE', '1:29:24']},
      {'values': [4, 'Zsebeházy István', 'MOM', '1:34:52']},
      {'values': [5, 'Tugyi Levente', 'DTC', '1:37:48']},
      {'values': [6, 'Gyulai Tamás', 'MSE', '1:44:36']},
      {'values': [7, 'Kazal Márton', 'PVS', '1:45:46']},
      {'values': [8, 'Kisvölcsey Ákos', 'MOM', '1:46:13']},
      {'values': [9, 'Morandini Viktor', 'SPA', '1:50:12']},
      {'values': [10, 'Bugár Gergely', 'SPA', '1:50:57']},
      {'values': [11, 'Mihályi Ferenc', 'TTE', '1:51:22']},
      {'values': [12, 'Sulyok Ábel', 'SPA', '1:51:34']},
      {'values': [13, 'Kirilla Péter', 'DTC', '1:51:54']},
      {'values': [14, 'Domonyik Gábor', 'MEA', '1:53:28']},
      {'values': [15, 'Vonyó Péter', 'PVS', '1:54:59']},
      {'values': [16, 'Oszlovics Ádám', 'MOM', '2:00:12']},
      {'values': [17, 'Kain Gergely', 'MOM', '2:08:40']},
      {'values': [18, 'Vajda Balázs', 'SZV', '2:14:02']},
      {'values': [19, 'Gond Gergely', 'GOC', '2:14:51']},
      {'values': [20, 'Pintér Ábel', 'GYO', '2:16:13']},
      {'values': [21, 'Forrai Gábor', 'HOD', '2:16:30']},
      {'values': [22, 'Forrai Miklós', 'HOD', '2:22:19']},
      {'values': [23, 'Kemenczky Jenő', 'SPA', '2:38:37']},
      {'values': [24, 'Kövesdi Ádám', 'TTE', '2:47:19']},
      {'values': ['', 'Harkányi Zoltán', 'MEA', 'DNS']},
      {'values': ['', 'Kovács Ádám', 'SZV', 'DNS']},
      {'values': ['', 'Nagy István', 'TSE', 'DNS']},
      {'values': ['', 'Novai György', 'SZV', 'DNS']},
      {'values': ['', 'Szundi Attila', 'DTC', 'DNF']},
      {'values': ['', 'Vellner Gábor', 'SPA', 'DNF']},
      {'values': ['', 'Viczián Péter', 'SZV', 'DNF']},
      ],
    }
  data = json.dumps(obj).encode('utf-8')
  data = zlib.compress(data)
  await ws.send(data)


@applydefs
async def static(ws=None, loop=None):
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
  await ws.send(data)
  await asyncio.sleep(5, loop=loop)
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
  await ws.send(data)
  # print("> {!r}".format(obj))


if __name__ == '__main__':
  clientthread = ClientThread()
  clientthread.on_message = lambda msg: print(
      '\n{}\n'.format(msg))
  clientthread.start()

  shortcuts = {
    'h': highlight,
    'p': punch,
    'r': results,
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

