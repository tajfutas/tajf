from tajf.display.gui.mainwindow import Application
from tajf.display.server import ServerThread

if __name__ == '__main__':
  import sys

  if len(sys.argv) !=2:
    print('PVMOE Event Display')
    print('USAGE: python pvmoedisplay.py <port>')
  else:
    port = int(sys.argv[1])
    app = Application()
    serverthread = ServerThread(app, port)
    serverthread.start()
    app.mainloop()
    serverthread.loop.stop()
    while True:
      try:
        serverthread.loop.close()
      except RuntimeError:  # loop is not stopped yet...
        continue
      break
