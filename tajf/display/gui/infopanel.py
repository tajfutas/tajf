
import copy
import bisect
import datetime
import threading
import time
import tkinter
from tkinter.font import Font, nametofont

from tajf import threads
from tajf import timeconv


class InfoPanelWidget(tkinter.Frame):

  LS_EXTRA = 7
  MIN_FONT_SIZE = 6

  def __init__(self, master=None, cnf={}, **kw):
    self.fonts = {}
    super().__init__(master=master, cnf=cnf, **kw)
    self.curr_size = 0, 0
    self.prev_size = 0, 0
    self.bind('<Configure>', self._on_configure)

  def alter_fonts(self, normal=None, bold=None, initial=False):
    label_w = next(self.iter_all_label_widgets())
    if normal is None:
      first_font = nametofont(label_w.cget('font'))
      cnormal = dict(first_font.configure())
      cnormal['weight'] = 'normal'
    else:
      cnormal = dict(normal.configure())
    if bold is None:
      first_font = nametofont(label_w.cget('font'))
      cbold = dict(first_font.configure())
      cbold['weight'] = 'bold'
    else:
      cbold = dict(bold.configure())
    if initial:
      self.fonts['normal'] = Font(**cnormal)
      self.fonts['bold'] = Font(**cbold)
      [w.configure(font=self.fonts['normal'])
       for w in self.iter_all_label_widgets()]
    else:
      self.fonts['normal'].configure(**cnormal)
      self.fonts['bold'].configure(**cbold)

  def iter_all_widgets(self):
    yield from (w for row in self.widgets for w in row)

  def iter_row_widgets(self, row):
    yield from iter(self.widgets[row])

  def iter_frame_widgets(self, row=None):
    if row is None:
      yield from self.iter_all_frame_widgets()
    else:
      yield from self.iter_row_frame_widgets(row)

  def iter_all_frame_widgets(self):
    yield from (w for row in self.frames for w in row)

  def iter_row_frame_widgets(self, row):
    yield from iter(self.frames[row])

  def iter_label_widgets(self, row=None):
    if row is None:
      yield from self.iter_all_label_widgets()
    else:
      yield from self.iter_row_label_widgets(row)

  def iter_all_label_widgets(self):
    yield from (w for row in self.labels for w in row)

  def iter_row_label_widgets(self, row):
    yield from iter(self.labels[row])

  def _on_configure(self, event):
    self.on_before_configure(event)
    self.on_configure(event)
    self.on_after_configure(event)

  def on_before_configure(self, event):
    self.curr_size = event.width, event.height

  def on_configure(self, event):
    if self.curr_size[1] != self.prev_size[1]:
      self.adjust_fonts(event)

  def on_after_configure(self, event):
    self.prev_size = self.curr_size

  def adjust_fonts(self, event):
    new_font = Font(**self.fonts['normal'].configure())
    size = orig_size = new_font['size']
    desired_total_height = event.height
    orig_row_height = new_font.metrics('linespace')
    orig_row_height += self.LS_EXTRA
    orig_total_height = self.N_ROWS * orig_row_height
    if orig_total_height < desired_total_height:
      a, compfname, final_neg_adjust = 1, '__gt__', True
    elif orig_total_height > desired_total_height:
      a, compfname, final_neg_adjust = -1, '__lt__', False
    else:
      return
    prev_total_height = orig_total_height
    while True:
      if a < 0 and size <= self.MIN_FONT_SIZE:
        size = self.MIN_FONT_SIZE
        break
      size += a
      new_font.configure(size=size)
      new_row_height = new_font.metrics('linespace')
      new_row_height += self.LS_EXTRA
      new_total_height = self.N_ROWS * new_row_height
      if new_total_height == prev_total_height:
        size -= a
        break
      compf = getattr(new_total_height, compfname)
      if compf(desired_total_height):
        if final_neg_adjust and size > self.MIN_FONT_SIZE:
          size -= a
        break
      prev_total_height = new_total_height
    if size != orig_size:
      self.fonts['normal'].configure(size=size)
      self.fonts['bold'].configure(size=size)

  def set_style(self, style_name, **kw):
    return getattr(self, 'set_style_' + style_name)(**kw)

  def set_default_style(self, initial=False):
    self.alter_fonts(initial=initial)
    self.set_style(self.DEFAULT_STYLE)


class InfoPanelHead(InfoPanelWidget):

  DEFAULT_STYLE = 'white'
  N_ROWS = 2
  N_COLS = 1

  def __init__(self, master=None, cnf={}, **kw):
    super().__init__(master=master, cnf=cnf, **kw)
    class_ = tkinter.Label(self)
    class_.grid(row=0, column=0, sticky='news')
    control = tkinter.Label(self)
    control.grid(row=1, column=0, sticky='news')
    self.labels = [[class_], [control]]
    self.widgets = [[class_], [control]]
    for r in range(self.N_ROWS):
      self.rowconfigure(r, weight=1)
    self.columnconfigure(0, weight=1)
    self.set_default_style(initial=True)

  def clear(self):
    self.set_default_style(initial=True)
    for w in self.iter_all_label_widgets():
      w.config(text='')

  def set_style_blue(self):
    for w in self.iter_all_widgets():
      w.config(bg='blue', fg='white', font=self.fonts['normal'])

  def set_style_grey(self):
    for w in self.iter_all_widgets():
      w.config(bg='grey', fg='black', font=self.fonts['normal'])

  def set_style_red(self):
    for w in self.iter_all_widgets():
      w.config(bg='red', fg='white', font=self.fonts['normal'])

  def set_style_white(self):
    for w in self.iter_all_widgets():
      w.config(bg='white', fg='black',
        font=self.fonts['normal'])

  def set_values(self, values):
    [w.config(text=str(values[i]))
     for i, w in enumerate(self.iter_all_widgets())]

  def set(self, obj):
    self.set_style(obj['style'])
    self.set_values(obj['values'])


class InfoPanelTable(InfoPanelWidget):

  DEFAULT_STYLE = 'normal'
  N_ROWS = 3
  N_COLS = 4

  def __init__(self, master=None, cnf={}, **kw):
    super().__init__(master=master, cnf=cnf, **kw)
    bg = self.cget('bg')
    self.widgets = []
    self.labels = [[] for _ in range(self.N_ROWS)]
    self.frames = [[] for _ in range(self.N_ROWS)]
    for r in range(self.N_ROWS):

      pos_frame = tkinter.Frame(self, bg=bg)
      self.frames[r].append(pos_frame)
      pos_frame.grid(row=r, column=0, sticky='news')
      pos =  tkinter.Label(pos_frame, bg=bg)
      self.labels[r].append(pos)
      pos.place(relx=0.5, rely=0.5, anchor='c')

      name_frame = tkinter.Frame(self, bg=bg)
      self.frames[r].append(name_frame)
      name_frame.grid(row=r, column=1, sticky='news')
      name = tkinter.Label(name_frame, bg=bg)
      self.labels[r].append(name)
      name.place(x=0, rely=0.5, anchor='w')

      club_frame = tkinter.Frame(self, bg=bg)
      self.frames[r].append(club_frame)
      club_frame.grid(row=r, column=2, sticky='news')
      club = tkinter.Label(club_frame, bg=bg, width=5,
                           anchor='w')
      self.labels[r].append(club)
      club.place(x=0, rely=0.5, anchor='w')

      time_frame = tkinter.Frame(self, bg=bg)
      self.frames[r].append(time_frame)
      time_frame.grid(row=r, column=3, sticky='news')
      time = tkinter.Label(time_frame, bg=bg, width=7,
                           anchor='e')
      self.labels[r].append(time)
      time.place(relx=1, rely=0.5, anchor='e')

      self.widgets.append([pos_frame, pos, name_frame, name,
                           club_frame, club, time_frame, time])

    [self.rowconfigure(r, weight=1) for r in range(self.N_ROWS)]
    self.columnconfigure(1, weight=1)
    self.set_default_style(initial=True)
    self.set_column_widths()

  def clear(self):
    self.set_default_style(initial=True)
    for w in self.iter_all_label_widgets():
      w.config(text='')

  def on_configure(self, event):
    super().on_configure(event)
    if self.curr_size[1] != self.prev_size[1]:
      self.set_column_widths()

  def set_column_widths(self):
    sample_strings = '99', None, 'XXXX', '+8:88:88'
    for i, s in enumerate(sample_strings):
      if s:
        new_width = self.fonts['bold'].measure(s)
        for w in (row[i] for row in self.frames):
          w.configure(width=new_width)

  def set_style(self, style_name, row=None):
    root = self.winfo_toplevel()
    method = getattr(self, 'set_style_' + style_name)
    my_params, label_params, frame_params = method()
    self.config(**my_params)
    for w in self.iter_frame_widgets(row):
      w.config(**frame_params)
    for w in self.iter_label_widgets(row):
      w.config(**label_params)

  def set_style_normal(self):
    my_params = dict()
    label_params = dict(bg='white', fg='black',
                        font=self.fonts['normal'])
    frame_params = dict(bg='white')
    return my_params, label_params, frame_params

  def set_style_emph1(self):
    my_params = dict()
    label_params = dict(bg='orange', fg='black',
                        font=self.fonts['normal'])
    frame_params = dict(bg='orange')
    return my_params, label_params, frame_params

  def set_style_emph2(self):
    my_params = dict()
    label_params = dict(bg='red', fg='black',
                        font=self.fonts['normal'])
    frame_params = dict(bg='red')
    return my_params, label_params, frame_params

  def set_values(self, values, row):
      for i, w in enumerate(self.iter_row_label_widgets(row)):
        w.config(text=str(values[i]))

  def set(self, obj):
    for row, obj_ in enumerate(obj):
      self.set_style(obj_.get('style', 'normal'), row=row)
      self.set_values(obj_['values'], row=row)
    for i in range(self.N_ROWS - len(obj)):
      row = -i - 1
      self.set_style('normal', row=row)
      self.set_values([''] * self.N_COLS, row=row)


class InfoPanel(tkinter.Frame):

  DEFAULT_BACKGROUND = 'black'
  DEFAULT_PRECISION = 0

  MODES = ('follow', 'follow_stop_punch', 'punch',
      'results', 'static')

  def __init__(self, master=None, status=None,
      changed_cond=None, cnf={}, **kw):
    cnf_ = {
        'background': self.DEFAULT_BACKGROUND,
        }
    cnf_.update(tkinter._cnfmerge((cnf, kw)))
    super().__init__(master=master, cnf=cnf_, **kw)
    self._worker_thread = None
    self.status = ({} if status is None else status)
    self.changed_cond = changed_cond or threading.Condition()
    self.head = InfoPanelHead(self)
    self.head.grid(row=0, column=0, sticky='news')
    self.table = InfoPanelTable(self, bg='white')
    self.table.grid(row=0, column=1, sticky='news')
    self.rowconfigure(0, weight=1)
    self.columnconfigure(1, weight=1)
    self.bind('<Configure>', self.on_configure)

  def relief_worker_thread(self):
    if self._worker_thread:
      self._worker_thread.stop()
      self._worker_thread = None

  def clear(self):
    self.head.clear()
    self.table.clear()
    for key in set(self.status):
      del self.status[key]

  def on_configure(self, event):
    self.adjust_borderwidth(event)
    self.adjust_head_width(event)

  def adjust_borderwidth(self, event):
    width = min(event.width, event.height) // 30
    self.config(padx=width, pady=width)

  def adjust_head_width(self, event):
    self.columnconfigure(0, minsize=event.height)

  def show(self, payload_obj, **kwgs):
    mode = payload_obj.get('mode')
    if mode not in self.MODES:
      raise ValueError('Invalid mode: {}'.format(mode))
    f_mode_handler = getattr(self, 'set_mode_{}'.format(mode))
    return f_mode_handler(payload_obj, **kwgs)

  def close(self, **kwgs):
    self.clear()
    self.relief_worker_thread()
    return True

  def set_mode_follow(self, payload_obj):
    self.clear()
    self.relief_worker_thread()
    self.head.set(payload_obj['head'])
    self._worker_thread = FollowerThread(self, payload_obj)
    self._worker_thread.start()
    return True

  def set_mode_follow_stop_punch(self, payload_obj):
    self._worker_thread.punch_time = payload_obj['punch_time']
    return True

  def set_mode_punch(self, payload_obj, clear=False):
    if clear:
      self.clear()
    self.relief_worker_thread()
    head = payload_obj.get('head')
    if head is not None:
      self.head.set(head)
    self._worker_thread = PunchThread(self, payload_obj)
    self._worker_thread.start()
    return True

  def set_mode_results(self, payload_obj):
    self.clear()
    self.relief_worker_thread()
    self.head.set(payload_obj['head'])
    self._worker_thread = ResultsThread(self, payload_obj)
    self._worker_thread.start()
    return True

  def set_mode_static(self, payload_obj):
    self.clear()
    self.relief_worker_thread()
    self.set_display(payload_obj)
    self.idle.set()
    return True

  def set_display(self, payload_obj):
    if 'head' in payload_obj:
      self.head.set(payload_obj['head'])
    if 'table' in payload_obj:
      self.table.set(payload_obj['table'])


class InfoPanelThread(threads.StoppableThread):

  def __init__(self, infopanel, obj):
    super().__init__()
    self.ip = infopanel
    self.obj = obj


class FollowerThread(InfoPanelThread):

  DEFAULT_REFRESH = 0.03

  def __init__(self, infopanel, obj):
    super().__init__(infopanel, obj)
    self.precision = self.obj.get('precision',
        self.ip.DEFAULT_PRECISION)
    self.table = [r for r in self.obj['table']
        if r['values'][0] != '']
    seq = (r['values'][-1] for r in self.table)
    self.timedeltas = timeconv.seq_of_strings_to_timedelta(seq)
    s_hstart = self.obj['followed_start']
    self.hstart = timeconv.string_to_datetime(s_hstart)
    self.punch_time = None

  def punch_time_norm(self, punch_time):
    µs = punch_time.microseconds // 10**(6-self.precision)
    return datetime.timedelta(days=punch_time.days,
        seconds=punch_time.seconds, microseconds=µs)

  def get_follow_display_obj(self):
    punch_obj = self.get_punch_obj()
    del punch_obj['mode']
    del punch_obj['head']
    punch_pos = punch_obj['punch_pos']
    punch_obj['table'][punch_pos - 1]['style'] = 'emph1'
    del punch_obj['punch_pos']
    return punch_obj

  def get_punch_obj(self):
    if not self.punch_time or self.punch_time is True:
      punch_timedelta = datetime.datetime.now() - self.hstart
    else:
      punch_timedelta = timeconv.string_to_timedelta(
          self.punch_time)
    name, club = self.obj['followed']
    return get_punch_obj(punch_timedelta, name, club,
      self.obj['head'], self.table, timedeltas=self.timedeltas,
      precision=self.precision)

  def run(self):
    self.ip.status.update(self.obj)
    with self.ip.changed_cond:
      self.ip.changed_cond.notify_all()
    while not self.stopped():
      if self.punch_time:
        punch_obj = self.get_punch_obj()
        del punch_obj['head']
        self.ip.set_mode_punch(punch_obj)
        break
      self.ip.set_display(self.get_follow_display_obj())
      if not self.stopped() and not self.punch_time:
        time.sleep(self.DEFAULT_REFRESH)


class PunchThread(InfoPanelThread):

  BLINK_INTERVAL = 100
  BLINK_COUNT = 10
  RELAX_INTERVAL = 5000

  def run(self):
    t = self.obj.get('blink_interval', self.BLINK_INTERVAL)
    N = self.obj.get('blink_count', self.BLINK_COUNT)
    R = self.obj.get('relax_interval', self.RELAX_INTERVAL)
    blinkobj = copy.deepcopy(self.obj)
    punch_row_d = blinkobj['table'][self.obj['punch_pos'] - 1]
    punch_row_d['style'] = 'emph1'
    relax_N = R // t
    n, relax_n = 0, 0
    self.ip.status.update(self.obj)
    with self.ip.changed_cond:
      self.ip.changed_cond.notify_all()
    while not self.stopped():
      if n < N:
        if n == N - 1:
          punch_row_d['style'] = 'emph2'
        if n % 2:
          self.ip.set_display(blinkobj)
        else:
          self.ip.set_display(self.obj)
        n += 1
      elif relax_n < relax_N:
        relax_n += 1
      else:
        break
      if not self.stopped():
        time.sleep(t / 1000)
    if not self.stopped():
      self.ip.clear()
      with self.ip.changed_cond:
        self.ip.changed_cond.notify_all()


class ResultsThread(InfoPanelThread):

  TURN_INTERVAL = 5000

  def run(self):
    self.ip.status.update(self.obj)
    t = self.ip.status.get('turn_interval', self.TURN_INTERVAL)
    result_rows = len(self.obj['table'])
    panel_rows = self.ip.table.N_ROWS
    n = self.ip.status.setdefault('n', 0)
    while not self.stopped() and n < result_rows:
      self.ip.status['n'] = n
      table = self.ip.status['table'][n:n+panel_rows]
      self.ip.set_display({'table': table})
      with self.ip.changed_cond:
        self.ip.changed_cond.notify_all()
      n += panel_rows
      if not self.stopped():
        time.sleep(t / 1000)
    if not self.stopped():
      self.ip.clear()
      with self.ip.changed_cond:
          self.ip.changed_cond.notify_all()


def get_punch_obj(punch_timedelta, name, club, head, table,
    timedeltas=None, precision=0):
  htime = timeconv.timedelta_to_string(punch_timedelta,
      precision)
  if timedeltas is None:
    seq = (r['values'][-1] for r in table)
    timedeltas = timeconv.seq_of_strings_to_timedelta(seq)
  i = bisect.bisect_left(timedeltas, punch_timedelta)
  h = [i + 1] + [name, club] + [htime]
  highl = [{'values': h}]
  if i == 0:
    before = []
    after = copy.deepcopy(table[i:i+2])
    punch_pos = 1
  elif i == len(table):
    before = copy.deepcopy(table[i-2:i])
    after = []
    punch_pos = len(before) + 1
  else:
    before = copy.deepcopy(table[i-1:i])
    after = copy.deepcopy(table[i:i+1])
    punch_pos = 2
  table_ = before + highl + after
  seq = (r['values'][-1] for r in table_)
  table_timedeltas = timeconv.seq_of_strings_to_timedelta(seq)
  last_pos = i + 1
  for ti, tr in enumerate(table_):
    if ti == 0:
      tr['values'][0] = last_pos
    elif table_timedeltas[ti] == table_timedeltas[ti-1]:
      tr['values'][0] = ''
    else:
      tr['values'][0] = last_pos
    last_pos += 1
  return {'mode': 'punch', 'head': head, 'table': table_,
      'punch_pos': punch_pos}


if __name__ == "__main__":
  r = tkinter.Tk()
  ip = InfoPanel(r)
  ip.pack(expand=True, fill=tkinter.BOTH)
  r.mainloop()
