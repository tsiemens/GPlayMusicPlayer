
import sys
import random
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtWidgets import QSizePolicy

import pdb

class MyWidget(QtWidgets.QWidget):
   def __init__(self):
      super().__init__()
      self.layout_player()

   def handle_play_pause_button(self):
      pass

   def layout_player(self):
      self.track_info = QtWidgets.QLabel("Unknown - Unknown")
      self.track_info.setAlignment(QtCore.Qt.AlignHCenter)

      #  self.progress_bar = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
      self.progress_bar = QtWidgets.QProgressBar()
      self.progress_bar.setFormat("")
      self.progress_bar.setMaximumHeight(10)
      self.progress_bar.setMinimum(0)
      self.progress_bar.setMaximum(100)
      #  self.progress_bar.setSliderPosition(75)
      self.progress_bar.setValue(75)

      self.progress_text = QtWidgets.QLabel("1:00")
      self.progress_text.setAlignment(QtCore.Qt.AlignLeft)

      self.play_pause_button = QtWidgets.QPushButton("Play/Pause")
      # Despite the policy being "maximum", this shrinks the button to the
      # text size
      sp = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
      self.play_pause_button.setSizePolicy(sp)

      self.play_pause_button.clicked.connect(self.handle_play_pause_button)

      # Layouts:
      self.button_layout = QtWidgets.QHBoxLayout()
      self.button_layout.addWidget(self.progress_text)
      self.button_layout.addWidget(self.play_pause_button)

      self.layout = QtWidgets.QVBoxLayout()
      self.layout.addWidget(self.track_info)
      self.layout.addWidget(self.progress_bar)
      self.layout.addLayout(self.button_layout)

      self.setLayout(self.layout)

   def set_progress_percent(self, prog):
      self.progress_bar.setValue(int(prog))

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
      pdb.set_trace()

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

   def magic(self):
      self.text.setText(random.choice(self.hello))

def make_app():
   return QtWidgets.QApplication([])

def show_gui(app):
   widget = MyWidget()
   widget.resize(800, 600)
   widget.show()
   app.exec_()

def run_gui():
   app = show_app()

   #  sys.exit(app.exec_())
   return app.exec_()

if __name__ == "__main__":
   sys.exit(run_gui())
