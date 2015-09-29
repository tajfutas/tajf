import threading


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


class ConditionWatcherThread(StoppableThread):

  def __init__(self, condition, callback):
    self.condition = condition
    self.callback = callback
    super().__init__()

  def stop(self):
    super().stop()

  def run(self):
    with self.condition:
      while not self.stopped():
        self.condition.wait()
        self.callback()


class QueueConsumerThread(StoppableThread):

  def __init__(self, queue_, callback):
    self.queue = queue_
    self.callback = callback
    super().__init__()

  def stop(self):
    super().stop()
    self.queue.put(None)

  def run(self):
    while not self.stopped():
      obj = self.queue.get()
      self.callback(obj)
      self.queue.task_done()
