from tajf.display.gui.mainwindow import Application
from tajf.display.server import ServerThread

if __name__ == '__main__':
  import sys

  if len(sys.argv) > 2:
    print('PVMOE Event Display')
    print('USAGE: python pvmoedisplay.py <port>')
  else:
    if len(sys.argv) == 2:
      port = int(sys.argv[1])
    else:
      port = None
    app = Application()
    serverthread = ServerThread(app, port, host='0.0.0.0')
    serverthread.start()
    app.mainloop()
    serverthread.loop.stop()
    while True:
      try:
        serverthread.loop.close()
      except RuntimeError:  # loop is not stopped yet...
        continue
      break
