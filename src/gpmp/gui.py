
import sys
import random
from time import sleep
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtWidgets import QSizePolicy

from gpmp.log import get_logger
from main import TrackTimingInfo

log = get_logger("gui")

import pdb

def secondsToMinuteStr(secs):
   mins = int(secs / 60)
   secs = int(secs) % 60
   return "{}:{:02d}".format(mins, secs)

class Window(QtWidgets.QWidget):
   progress_bar_max = 500

   def __init__(self):
      super().__init__()
      self.setWindowTitle("gplaymusicplayer")
      self.layout_player()

   def layout_player(self):
      self.track_info = QtWidgets.QLabel("Unknown - Unknown")
      self.track_info.setAlignment(QtCore.Qt.AlignHCenter)

      #  self.progress_bar = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
      self.progress_bar = QtWidgets.QProgressBar()
      self.progress_bar.setFormat("")
      self.progress_bar.setMaximumHeight(10)
      self.progress_bar.setMinimum(0)
      self.progress_bar.setMaximum(self.progress_bar_max)
      #  self.progress_bar.setSliderPosition(75)
      self.progress_bar.setValue(0)

      self.progress_text = QtWidgets.QLabel("1:00")
      self.progress_text.setAlignment(QtCore.Qt.AlignLeft)

      # Despite the policy being "maximum", this shrinks the button to the
      # text size
      sp = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

      self.previous_button = QtWidgets.QPushButton("\u23EE")
      self.previous_button.setSizePolicy(sp)

      self.play_pause_button = QtWidgets.QPushButton("\u23EF")
      self.play_pause_button.setSizePolicy(sp)

      self.next_button = QtWidgets.QPushButton("\u23ED")
      self.next_button.setSizePolicy(sp)

      # Layouts:
      self.button_layout = QtWidgets.QHBoxLayout()
      self.button_layout.addWidget(self.progress_text)
      self.button_layout.addWidget(self.previous_button)
      self.button_layout.addWidget(self.play_pause_button)
      self.button_layout.addWidget(self.next_button)

      self.layout = QtWidgets.QVBoxLayout()
      self.layout.addWidget(self.track_info)
      self.layout.addWidget(self.progress_bar)
      self.layout.addLayout(self.button_layout)

      self.setLayout(self.layout)

   def update_progress(self, info: TrackTimingInfo):
      currtime = 0
      duration_secs = 0
      if info:
         self.set_progress_bar_fract(info.position_fract)
         currtime = info.position_fract * info.duration_secs
         duration_secs = info.duration_secs

      else:
         self.set_progress_bar_fract(0)

      self.progress_text.setText("{}/{}".format(
         secondsToMinuteStr(currtime),
         secondsToMinuteStr(duration_secs)))

   def set_progress_bar_fract(self, prog):
      try:
         self.progress_bar.setValue(prog * self.progress_bar_max)
      except Exception as e:
         log.error("caught exception: {}".format(e))

   def set_song_info(self, song_info: str):
      if song_info is not None:
         self.track_info.setText(song_info)

   def do_test_layout(self):
      self.hello = ["Hallo Welt", "Hei maailma", "Hola Mundo", "Привет мир"] * 20

      #  self.button = QtWidgets.QPushButton("Click me!")
      #  self.text = QtWidgets.QLabel("Hello World")
      #  self.text.setAlignment(QtCore.Qt.AlignCenter)
      self.list = QtWidgets.QListView()

      model = QtGui.QStandardItemModel()
      for f in self.hello:
          model.appendRow(QtGui.QStandardItem(f))
      self.list.setModel(model)

      sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
      sp.setHorizontalStretch(1)
      self.list.setSizePolicy(sp)

      self.tree = QtWidgets.QTreeView()
      self.pop_tree()
      sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
      sp.setHorizontalStretch(2)
      self.tree.setSizePolicy(sp)

      self.layout = QtWidgets.QHBoxLayout()
      self.layout.addWidget(self.list)
      self.layout.addWidget(self.tree)
      #  self.layout.addWidget(self.text)
      #  self.layout.addWidget(self.button)
      self.setLayout(self.layout)

      #  self.button.clicked.connect(self.magic)

   def pop_tree(self):
      self.tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
      model = QtGui.QStandardItemModel()
      model.setHorizontalHeaderLabels(['col1', 'col2', 'col3'])
      self.tree.setModel(model)
      self.tree.setUniformRowHeights(True)
      # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      # populate data
      for i in range(3):
          parent1 = QtGui.QStandardItem('Family {}. Some long status text for sp'.format(i))
          for j in range(3):
              child1 = QtGui.QStandardItem('Child {}'.format(i*3+j))
              child2 = QtGui.QStandardItem('row: {}, col: {}'.format(i, j+1))
              child3 = QtGui.QStandardItem('row: {}, col: {}'.format(i, j+2))
              parent1.appendRow([child1, child2, child3])
          model.appendRow(parent1)
          # span container columns
          self.tree.setFirstColumnSpanned(i, self.tree.rootIndex(), True)

      parent2 = QtGui.QStandardItem("No children here")
      model.appendRow(parent2)

      # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
      # expand third container
      index = model.indexFromItem(parent1)
      self.tree.expand(index)

#  class WorkerObject(QtCore.QObject):

   #  #  signalStatus = QtCore.pyqtSignal(str)
   #  prog_signal = QtCore.Signal(int)

   #  def __init__(self, parent=None):
      #  super(self.__class__, self).__init__(parent)

   #  def startWork(self):
      #  print("startWork")
      #  from time import sleep
      #  for ii in range(100):
         #  sleep(1.0)
         #  print("startWork:", ii)
         #  self.prog_signal.emit(ii)
            #  #  number = random.randint(0,5000**ii)
            #  #  self.signalStatus.emit('Iteration: {}, Factoring: {}'.format(ii, number))
            #  #  factors = self.primeFactors(number)
            #  #  print('Number: ', number, 'Factors: ', factors)
        #  #  self.signalStatus.emit('Idle.')

class WorkerThread(QtCore.QThread):
   prog_signal = QtCore.Signal(TrackTimingInfo)
   song_info_signal = QtCore.Signal(str)

   def __init__(self, player):
      QtCore.QThread.__init__(self)
      self.player = player

      self.current_song_info = None
      self.interrupted = False
      self.self_terminated = False

   def __del__(self):
      if not self.self_terminated:
         self.wait()

   def interrupt(self):
      self.interrupted = True

   def send_ui_update_signal(self):
      if self.player is not None:
         prog = min(int(self.player.get_position() * 100), 100)
         self.prog_signal.emit(self.player.get_timing_info())

         player_current_song_info = self.player.current_song_info.value
         if player_current_song_info != self.current_song_info:
            self.current_song_info = player_current_song_info
            self.song_info_signal.emit(player_current_song_info)

   def run(self):
      log.debug("WorkerThread.run")
      while not self.interrupted:
         sleep(0.5)
         self.send_ui_update_signal()

      log.info("WorkerThread interrupted")
      self.terminate()
      self.self_terminated = True

class QtController(QtCore.QObject):
   #  signalStatus = QtCore.pyqtSignal(str)
   worker_start_signal = QtCore.Signal()
   worker_interrupt_signal = QtCore.Signal()

   def __init__(self, parent, player):
      super(self.__class__, self).__init__(parent)

      self.player = player

      # Create a gui object.
      self.gui = Window()

      self.gui.resize(400, 0)

      self.connect_controls()

      # Create a new worker thread.
      self.createWorkerThread()

      # Make any cross object connections.
      #  self._connectSignals()

      self.gui.show()

   def connect_controls(self):
      if self.player:
         self.gui.play_pause_button.clicked.connect(self.player.toggle_play)
         self.gui.next_button.clicked.connect(self.player.play_next_track)
         self.gui.previous_button.clicked.connect(
               self.player.handle_previous_track_action)

   def createWorkerThread(self):
      #  self.worker = WorkerObject()
      #  self.worker_thread = QtCore.QThread()
      #  self.worker.moveToThread(self.worker_thread)

      #  self.worker.prog_signal.connect(self.gui.set_progress_bar_fract)

      #  self.worker_thread.start()

      self.parent().aboutToQuit.connect(self.forceWorkerQuit)

      self.custom_worker_thread = WorkerThread(self.player)
      #  self.custom_worker_thread.prog_signal.connect(self.gui.set_progress_bar_fract)
      self.custom_worker_thread.prog_signal.connect(self.gui.update_progress)
      self.custom_worker_thread.song_info_signal.connect(self.gui.set_song_info)
      self.custom_worker_thread.start()


      # Connect any worker signals
      #  self.worker.signalStatus.connect(self.gui.updateStatus)
      #  self.gui.button_start.clicked.connect(self.worker.startWork)
      self.worker_interrupt_signal.connect(self.custom_worker_thread.interrupt)

   def forceWorkerQuit(self):
      try:
         #  if self.worker_thread.isRunning():
            #  self.worker_thread.terminate()
            #  self.worker_thread.wait()

         if self.custom_worker_thread.isRunning():
            self.worker_interrupt_signal.emit()
            self.custom_worker_thread.wait()
            #  self.custom_worker_thread.terminate()
            #  if self.custom_worker_thread.isRunning():
               #  self.custom_worker_thread.wait()
      except Exception as e:
         log.error("caught exception: {}".format(e))

def make_app():
   return QtWidgets.QApplication([])
