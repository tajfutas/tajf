import bisect
import copy
import datetime
import queue
import re
import threading
import time
import tkinter

from tajf.display import protocol as display_proto
from tajf import threads

from . import infopanel


START_SIZE = 640, 120


class Main(tkinter.Frame):

  DEFAULT_REFRESH = 25

  handler_abbr = {
      display_proto.C_SHOW: 'show',
      display_proto.C_CLOSE: 'close',
      }

  def __init__(self, master, *, changed_cond=None, **kw):
    super().__init__(master, **kw)
    self.status = {
      'infopanel': {},
      }
    self.changed_cond = changed_cond or threading.Condition()
    self.widgets = {
        'infopanel': infopanel.InfoPanel(self, **{
            'status': self.status['infopanel'],
            'changed_cond': self.changed_cond,
            }),
        }
    self.widgets['infopanel'].pack(expand=True,
        fill=tkinter.BOTH)

  def close(self):
    for w in self.widgets.values():
      w.close()

  def command(self, code, widget_name, payload_obj):
    code_handler_name = self.handler_abbr.get(code)
    if code_handler_name is None:
      exc_msg = 'Invalid client code: {}'.format(code)
      exc = ValueError(exc_msg)
      return display_proto.A_ERROR, exc
    else:
      handler_func_name = 'handle_{}'.format(code_handler_name)
    try:
      accepted = getattr(self, handler_func_name)(
          widget_name, payload_obj)
    except Exception as exc:
      return display_proto.A_ERROR, exc
    else:
      if accepted is True:
        answer_code = display_proto.A_ACCEPTED
      else:
        answer_code = display_proto.A_DENIED
      return answer_code, None

  def handle_show(self, widget_name, payload_obj):
    w = self.widgets[widget_name]
    accepted = w.show(payload_obj)
    return accepted

  def handle_close(self, widget_name, payload_obj):
    w = self.widgets[widget_name]
    accepted = w.close()
    return accepted


class Application(tkinter.Tk):

  TITLE = 'PVMOE Event Display'

  code_handlers = {
    display_proto.C_SHOW: 'show',
    display_proto.C_CLOSE: 'close',
    }

  def __init__(self, precision=0):
    super().__init__()
    self.withdraw()  # assembling in background...
    self.title(self.TITLE)
    self.main = Main(self)
    self.main.pack(expand=True, fill='both')
    self.minsize(*START_SIZE)
    self.deiconify()  # and show it
