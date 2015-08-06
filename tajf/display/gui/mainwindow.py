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
  d = {k: int(v) for k, v in m.groupdict().items() if v}
  s_prec_value = m.group('prec_value')
  if s_prec_value:
    preceision = len(s_prec_value)
    µs = d['prec_value'] * 10**(6-preceision)
    d['microseconds'] = µs
    del d['prec_value']
  return datetime.timedelta(**d)


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
    self._queue = queue.Queue()
    self._display_obj = None
    self.title(self.TITLE)
    self.infopanel = infopanel.InfoPanel(self)
    self.infopanel.pack(expand=True, fill='both')
    self.minsize(*START_SIZE)
    self.deiconify()  # and show it
    self.update()
    self._worker_thread = None
    self._refresh()

  @property
  def queue(self):
    return self._queue

  def _refresh(self):
    try:
      obj = self._queue.get_nowait()
    except queue.Empty:
      if self._display_obj:
        obj = self._display_obj
        self._display_obj = None
        self.set_display(obj)
    else:
      self.set_mode(obj)
    self.after(REFRESH, self._refresh)

  def relief_worker_thread(self):
    if self._worker_thread:
      self._worker_thread.stop()
      self._worker_thread = None

  def relief_display(self):
    self._display_obj = None

  def set_mode(self, obj):
    getattr(self, 'set_mode_{}'.format(obj['mode']))(obj)

  def set_mode_static(self, obj):
    self.relief_worker_thread()
    self.relief_display()
    self.set_display(obj)

  def set_mode_highlight(self, obj):
    self.relief_worker_thread()
    self.relief_display()
    self.infopanel.head.set(obj['head'])
    self._worker_thread = HighlighterThread(self, obj)
    obj_ = self._worker_thread.get_obj()
    self.set_display(obj_)
    self._worker_thread.start()

  def set_mode_highlight_punch(self, obj):
    self._worker_thread.punch_time = obj['punch_time']

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


class HighlighterThread(StoppableThread):

  def __init__(self, application, obj):
    super().__init__()
    self.app = application
    self.obj = obj
    self.timedeltas = [string_to_timedelta(r['values'][-1])
                       for r in self.obj['table']]
    s_hstart = self.obj['highlighted_start']
    self.hstart = datetime.datetime.strptime(s_hstart,
                                             STRP_ISO_FMT)
    self.punch_time = None

  def get_obj(self):
    if not self.punch_time:
      style = 'emph1'
    else:
      style = 'emph2'
    if not self.punch_time or self.punch_time is True:
      punch_time = datetime.datetime.now() - self.hstart
    else:
      punch_time = string_to_timedelta(self.punch_time)
    µs = punch_time.microseconds // 10**(6-self.app.precision)
    punch_time = datetime.timedelta(days=punch_time.days,
      seconds=punch_time.seconds, microseconds=µs)
    htime = timedelta_to_string(punch_time, self.app.precision)
    i = bisect.bisect_left(self.timedeltas, punch_time)
    h = [i + 1] + self.obj['highlighted'] + [htime]
    highl = [{'style': style, 'values': h}]
    if i == 0:
      before = []
      after = copy.deepcopy(self.obj['table'][i:i+2])
    else:
      before = copy.deepcopy(self.obj['table'][i-1:i])
      after = copy.deepcopy(self.obj['table'][i:i+1])
    if before and self.timedeltas[i-1] == punch_time:
      h[0] = ''
    if after and punch_time < self.timedeltas[i]:
      for r in after:
        r['values'][0] += 1
    elif after and punch_time == self.timedeltas[i]:
      after[0]['values'][0] = ''
    return {'table': before + highl + after}

  def run(self):
    while not self.stopped() and not self.punch_time:
      time.sleep(REFRESH / 3000)
      obj = self.get_obj()
      self.app._display_obj = obj
    if self.punch_time:
      obj = self.get_obj()
