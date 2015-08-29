import bisect
import copy
import datetime
import queue
import re
import threading
import time
import tkinter

from . import infopanel

START_SIZE = 640, 120
REFRESH = 25

STRP_ISO_FMT = '%Y-%m-%dT%H:%M:%S.%f'


def string_to_timedelta(s):
  restr = ('^(?P<minutes>\d+)?:?(?P<seconds>\d+)?'
           '\.?(?P<prec_value>\d+)?$')
  m = re.search(restr, s)
  if m is None:
    errfstr = 'invaild timedelta string: {!r}'
    raise ValueError(errfstr.format(s))
  d = {k: int(v) for k, v in m.groupdict().items() if v}
  s_prec_value = m.group('prec_value')
  if s_prec_value:
    preceision = len(s_prec_value)
    µs = d['prec_value'] * 10**(6-preceision)
    d['microseconds'] = µs
    del d['prec_value']
  return datetime.timedelta(**d)

def seq_of_strings_to_timedelta(seq):
  result = []
  for s in seq:
    try:
      td = string_to_timedelta(s)
    except ValueError:
      break
    else:
      result.append(td)
  return result


# based on source code of datetime.py
def timedelta_to_string(td, precision=0):
    mm, ss = divmod(td.seconds, 60)
    if td.days:
      mm += 24 * 60 * td.days
    if mm:
      s = '{:d}:{:0>2d}'.format(mm, ss)
    else:
      s = '{:d}'.format(ss)
    if precision:
      fs = '.{{:0<{:d}d}}'.format(precision)
      value = round(td.microseconds / 10**(6-precision))
      s += fs.format(value)
    return s


class Application(tkinter.Tk):

  TITLE = 'PVMOE Event Display'

  def __init__(self, precision=0):
    super().__init__()
    self.precision = precision
    self.withdraw()  # assembling in background...
    self.idle = threading.Event()
    self.idle.set()
    self.queue = queue.Queue()
    self._display_obj = None
    self.title(self.TITLE)
    self.infopanel = infopanel.InfoPanel(self)
    self.infopanel.pack(expand=True, fill='both')
    self.minsize(*START_SIZE)
    self.clear()
    self.deiconify()  # and show it
    self._worker_thread = None
    self._refresh()

  def clear(self):
    self.infopanel.clear()

  def _refresh(self):
    try:
      obj = self.queue.get_nowait()
    except queue.Empty:
      if self._display_obj:
        obj = self._display_obj
        self._display_obj = None
        self.set_display(obj)
      if self.queue.unfinished_tasks == 0:
        self.idle.set()
    else:
      self.set_mode(obj)
      self.idle.clear()
    self.after(REFRESH, self._refresh)

  def relief_worker_thread(self):
    if self._worker_thread:
      self._worker_thread.stop()
      self._worker_thread = None

  def relief_display(self):
    self._display_obj = None

  def set_mode(self, obj):
    getattr(self, 'set_mode_{}'.format(obj['mode']))(obj)

  def set_mode_highlight(self, obj):
    self.relief_worker_thread()
    self.relief_display()
    self.infopanel.head.set(obj['head'])
    self._worker_thread = HighlighterThread(self, obj)
    self._worker_thread.start()

  def set_mode_highlight_punch(self, obj):
    self._worker_thread.punch_time = obj['punch_time']

  def set_mode_punch(self, obj):
    self.relief_worker_thread()
    self.relief_display()
    self.infopanel.head.set(obj['head'])
    self._worker_thread = PunchThread(self, obj)
    self._worker_thread.start()

  def set_mode_results(self, obj):
    self.relief_worker_thread()
    self.relief_display()
    self.infopanel.head.set(obj['head'])
    self._worker_thread = ResultsThread(self, obj)
    self._worker_thread.start()

  def set_mode_static(self, obj):
    self.relief_worker_thread()
    self.relief_display()
    self.set_display(obj)
    self.queue.task_done()

  def set_display(self, obj):
    if 'head' in obj:
      self.infopanel.head.set(obj['head'])
    if 'table' in obj:
      self.infopanel.table.set(obj['table'])


# Based on code by Bluebird75
# http://stackoverflow.com/a/325528/2334951
class StoppableThread(threading.Thread):
  """Thread class with a stop() method.

  The thread itself has to check regularly for the stopped()
  condition."""

  def __init__(self):
    super().__init__()
    self._stop = threading.Event()

  def stop(self):
    self._stop.set()

  def stopped(self):
    return self._stop.isSet()


class MainWindowThread(StoppableThread):

  def __init__(self, application, obj):
    super().__init__()
    self.app = application
    self.obj = obj


class HighlighterThread(MainWindowThread):

  def __init__(self, application, obj):
    super().__init__(application, obj)
    seq = (r['values'][-1] for r in self.obj['table'])
    self.timedeltas = seq_of_strings_to_timedelta(seq)
    s_hstart = self.obj['highlighted_start']
    self.hstart = datetime.datetime.strptime(s_hstart,
                                             STRP_ISO_FMT)
    self.punch_time = None

  def punch_time_norm(self, punch_time):
    µs = punch_time.microseconds // 10**(6-self.app.precision)
    return datetime.timedelta(days=punch_time.days,
        seconds=punch_time.seconds, microseconds=µs)

  def get_highlight_display_obj(self):
    punch_obj = self.get_punch_obj()
    del punch_obj['mode']
    del punch_obj['head']
    punch_pos = punch_obj['punch_pos']
    punch_obj['table'][punch_pos - 1]['style'] = 'emph1'
    del punch_obj['punch_pos']
    return punch_obj

  def get_punch_obj(self):
    if not self.punch_time or self.punch_time is True:
      punch_time = datetime.datetime.now() - self.hstart
    else:
      punch_time = string_to_timedelta(self.punch_time)
    punch_time = self.punch_time_norm(punch_time)
    htime = timedelta_to_string(punch_time, self.app.precision)
    i = bisect.bisect_left(self.timedeltas, punch_time)
    h = [i + 1] + self.obj['highlighted'] + [htime]
    highl = [{'values': h}]
    if i == 0:
      before = []
      after = copy.deepcopy(self.obj['table'][i:i+2])
      punch_pos = 1
    elif i == len(self.obj['table']):
      before = copy.deepcopy(self.obj['table'][i-2:i])
      after = []
      punch_pos = len(before) + 1
    else:
      before = copy.deepcopy(self.obj['table'][i-1:i])
      after = copy.deepcopy(self.obj['table'][i:i+1])
      punch_pos = 2
    table = before + highl + after
    seq = (r['values'][-1] for r in table)
    table_timedeltas = seq_of_strings_to_timedelta(seq)
    last_pos = i + 1
    for ti, tr in enumerate(table):
      if ti == 0:
        tr['values'][0] = last_pos
      elif table_timedeltas[ti] == table_timedeltas[ti-1]:
        tr['values'][0] = ''
      else:
        tr['values'][0] = last_pos
      last_pos += 1
    return {'mode': 'punch', 'head': self.obj['head'],
            'table': table, 'punch_pos': punch_pos}

  def run(self):
    while not self.stopped():
      if self.punch_time:
        obj = self.get_punch_obj()
        self.app.set_mode_punch(obj)
        break
      obj = self.get_highlight_display_obj()
      self.app._display_obj = obj
      if not self.stopped() and not self.punch_time:
        time.sleep(REFRESH / 3000)
      else:
        break
    self.app.queue.task_done()


class PunchThread(MainWindowThread):

  BLINK_INTERVAL = 100
  BLINK_COUNT = 10

  def run(self):
    t = self.obj.get('blink_interval', self.BLINK_INTERVAL)
    N = self.obj.get('blink_count', self.BLINK_COUNT)
    blinkobj = copy.deepcopy(self.obj)
    punch_row_d = blinkobj['table'][self.obj['punch_pos'] - 1]
    punch_row_d['style'] = 'emph1'
    n = 0
    while not self.stopped() and n < N:
      if n == N - 1:
        punch_row_d['style'] = 'emph2'
      if n % 2:
        self.app._display_obj = blinkobj
      else:
        self.app._display_obj = self.obj
      n += 1
      if not self.stopped():
        time.sleep(t / 1000)
    self.app.queue.task_done()


class ResultsThread(MainWindowThread):

  TURN_INTERVAL = 5000

  def run(self):
    t = self.obj.get('turn_interval', self.TURN_INTERVAL)
    result_rows = len(self.obj['table'])
    panel_rows = self.app.infopanel.table.N_ROWS
    n = 0
    while not self.stopped() and n < result_rows:
      table = self.obj['table'][n:n+panel_rows]
      self.app._display_obj = {'table': table}
      n += panel_rows
      if not self.stopped():
        time.sleep(t / 1000)
    self.app.queue.task_done()
