import queue
import tkinter
from tkinter.font import Font, nametofont

class InfoPanelWidget(tkinter.Frame):

  LS_EXTRA = 7
  MIN_FONT_SIZE = 6

  def __init__(self, master=None, cnf={}, **kw):
    self.fonts = {}
    super().__init__(master=master, cnf=cnf, **kw)
    self.bind('<Configure>', self.on_configure)

  def alter_fonts(self, normal=None, bold=None, initial=False):
    if normal is None:
      first_font = nametofont(self.widgets[0][0].cget('font'))
      cnormal = dict(first_font.configure())
      cnormal['weight'] = 'normal'
    else:
      cnormal = dict(normal.configure())
    if bold is None:
      first_font = nametofont(self.widgets[0][0].cget('font'))
      cbold = dict(first_font.configure())
      cbold['weight'] = 'bold'
    else:
      cbold = dict(bold.configure())
    if initial:
      self.fonts['normal'] = Font(**cnormal)
      self.fonts['bold'] = Font(**cbold)
      [w.configure(font=self.fonts['normal'])
       for w in self.iter_label_widgets()]
    else:
      self.fonts['normal'].configure(**cnormal)
      self.fonts['bold'].configure(**cbold)

  def iter_all_widgets(self):
    yield from (w for row in self.widgets for w in row)

  def iter_label_widgets(self):
    yield from (w for w in self.iter_all_widgets()
                if w.widgetName == 'label')

  def on_configure(self, event):
    self.adjust_fonts(event)

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

  DEFAULT_STYLE = 'grey'
  N_ROWS = 2
  N_COLS = 1

  def __init__(self, master=None, cnf={}, **kw):
    super().__init__(master=master, cnf=cnf, **kw)
    class_ = tkinter.Label(self)
    class_.grid(row=0, column=0, sticky='news')
    control = tkinter.Label(self)
    control.grid(row=1, column=0, sticky='news')
    self.widgets = [[class_], [control]]
    for r in range(self.N_ROWS):
      self.rowconfigure(r, weight=1)
    self.columnconfigure(0, weight=1)
    self.set_default_style(initial=True)

  def set_style_blue(self):
    for w in self.iter_all_widgets():
      w.config(bg='blue', fg='white', font=self.fonts['normal'])

  def set_style_grey(self):
    for w in self.iter_all_widgets():
      w.config(bg='grey', fg='black', font=self.fonts['normal'])

  def set_style_red(self):
    for w in self.iter_all_widgets():
      w.config(bg='red', fg='white', font=self.fonts['normal'])

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
    self.widgets, self.name_frames = [], []
    for r in range(self.N_ROWS):
      pos =  tkinter.Label(self, bg=bg, width=2)
      pos.grid(row=r, column=0, sticky='news')
      name_frame = tkinter.Frame(self, bg=bg)
      name_frame.grid(row=r, column=1, sticky='news')
      name = tkinter.Label(name_frame, bg=bg)
      name.place(x=0, y=0)
      club = tkinter.Label(self, bg=bg, width=5, anchor='nw')
      club.grid(row=r, column=2, sticky='news')
      time = tkinter.Label(self, bg=bg, width=7, anchor='ne')
      time.grid(row=r, column=3, sticky='news')
      self.widgets.append([pos, name, club, time])
      self.name_frames.append(name_frame)
    for r in range(self.N_ROWS):
      self.rowconfigure(r, weight=1)
    self.columnconfigure(1, weight=1)
    self.set_default_style(initial=True)

  def iter_all_widgets(self):
    yield from super().iter_all_widgets()
    yield from self.name_frames

  def iter_row_widgets(self, row):
    yield from self.widgets[row]
    yield self.name_frames[row]

  def iter_label_widgets(self, row=None):
    yield from (w for w in self.iter_widgets(row)
                if w.widgetName == 'label')

  def iter_widgets(self, row=None):
    if row is None:
      yield from self.iter_all_widgets()
    else:
      yield from self.iter_row_widgets(row)

  def set_style(self, style_name, row=None):
    method = getattr(self, 'set_style_' + style_name)
    my_params, label_params, frame_params = method()
    self.config(**my_params)
    for w in self.iter_widgets(row):
      if w.widgetName == 'label':
        w.config(**label_params)
      elif w.widgetName == 'frame':
        w.config(**frame_params)

  def set_style_normal(self):
    my_params = dict()
    label_params = dict(bg='white', fg='black',
                        font=self.fonts['normal'])
    frame_params = dict(bg='white')
    return my_params, label_params, frame_params

  def set_style_emph1(self):
    my_params = dict()
    label_params = dict(bg='orange', fg='black',
                        font=self.fonts['bold'])
    frame_params = dict(bg='orange')
    return my_params, label_params, frame_params

  def set_style_emph2(self):
    my_params = dict()
    label_params = dict(bg='green', fg='black',
                        font=self.fonts['bold'])
    frame_params = dict(bg='green')
    return my_params, label_params, frame_params

  def set_values(self, values, row):
      for i, w in enumerate(self.iter_label_widgets(row)):
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
  DEFULT_BORDERWIDTH = 2

  def __init__(self, master=None, queue_=None, cnf={}, **kw):
    if not set(kw.keys()) & {'bg', 'background'}:
      kw['bg'] = self.DEFAULT_BACKGROUND
    super().__init__(master=master, cnf=cnf, **kw)
    self.queue = queue_ or queue.Queue(maxsize=1)
    self.head = InfoPanelHead(self)
    self.head.grid(row=0, column=0, sticky='news')
    self.table = InfoPanelTable(self)
    self.table.grid(row=0, column=1, sticky='news')
    self.rowconfigure(0, weight=1)
    self.columnconfigure(1, weight=1)
    self.bind('<Configure>', self.on_configure)

  def on_configure(self, event):
    self.adjust_borderwidth(event)
    self.adjust_head_width(event)

  def adjust_borderwidth(self, event):
    width = min(event.width, event.height) // 30
    self.config(padx=width, pady=width)

  def adjust_head_width(self, event):
    self.columnconfigure(0, minsize=event.height)

if __name__ == "__main__":
  import datetime
  import tkinter as tk
  r=tk.Tk()
  ip = InfoPanel()
  ip.pack(expand=True, fill='both')
  ip.set([{'style': 'blue', 'values': ['NYT', 'cél']},
         [
          {'style': 'normal',
           'values': [1, 'Dalos Máté', 'SPA', '37:31']},
          {'style': 'emph1',
           'values': [2, 'Tóth Tamás', 'TTE', '41:55']},
          {'style': 'normal',
           'values': [3, 'Lajtai Zoltán', 'PVM', '43:23']},
         ]])
  r.mainloop()
