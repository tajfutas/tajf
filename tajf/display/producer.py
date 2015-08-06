import json
import socket
import struct
import _thread, threading
import time

from sportswmock.dbisam import connect, query

import connection
from gui import infopanel

__version__ = '0.1'

class Producer(threading.Thread):

  SLIDE_INTERVAL = 6

  def __init__(self, path, port, host=None):
    self._path = path
    self._host = host or connection.CnxnThread.DEFAULT_HOST
    self._port = int(port)
    super().__init__()
    self.dbisam_connect()
    self.display_connect()
    self.flag = None

  @property
  def path(self):
    return self._path

  @property
  def host(self):
    return self._host

  @property
  def port(self):
    return self._port

  def dbisam_connect(self):
    self.cnxn = connect.get_connection(self.path)

  def display_connect(self):
    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.s.connect((self.host, self.port))

  def send_to_display(self, obj):
    jsonstr = json.dumps(obj)
    bytes = jsonstr.encode(connection.Protocol.ENC)
    len_fmt = connection.Protocol.LEN_FMT
    self.s.send(struct.pack(len_fmt, len(bytes)))
    self.s.send(bytes)

  def display_results(self, day, class_, control=None):
    if self.flag is not None:
      self.flag.clear()
    self.flag = threading.Event()
    self.flag.set()
    args = day, class_, control
    return _thread.start_new_thread(self._display_results, args)

  def _display_results(self, day, class_, control):
    flag = self.flag
    if control is not None:
      raise NotImplementedError()
    if class_.startswith('NY'):
      style = 'grey'
    elif class_[0] in ('F', 'M'):
      style = 'blue'
    elif class_[0] in ('N', 'W'):
      style = 'red'
    headobj = {'style': style, 'values': [class_, '']}
    results = tuple(r for r in
                    query.class_results(self.cnxn, day, class_)
                    if r.status_code < 2
                    )
    offset = 0
    n_rows = infopanel.InfoPanelTable.N_ROWS
    while flag.is_set():
      sl = slice(offset, min(len(results), offset + n_rows))
      if sl.start == sl.stop:
        offset = 0
        continue
      tableobj = [{'style': 'normal', 'values':
        [
         offset + i + 1,
         query.get_fullname(row),
         row.club,
         query.get_run_time_str(row),
        ]}
        for i, row in enumerate(results[sl])]
      empty_rows = n_rows - (sl.stop - sl.start)
      if empty_rows:
        tableobj.extend([{'style': 'normal', 'values': ['']*4}
                        for _ in range(empty_rows)])
        offset = 0
      else:
        offset += n_rows
      self.send_to_display([headobj, tableobj])
      time.sleep(self.SLIDE_INTERVAL)

if __name__ == '__main__':
  import sys
  if len(sys.argv) != 3:
    print('PVMOE Event Display Producer v' + __version__)
    print('USAGE: python producer.py '
                   '<path_to_dbisam_dir> <port>')
  else:
    path = sys.argv[1]
    port = int(sys.argv[2])
    p = Producer(path, port)
