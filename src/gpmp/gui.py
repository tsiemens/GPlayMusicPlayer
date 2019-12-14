"""Logic and layouts for Qt GUI"""

import pdb # pylint: disable-msg=unused-import
from time import sleep

import qdarkstyle
from gmusicapi import Mobileclient
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtWidgets import QSizePolicy

from gpmp.auth import authenticate_client
from gpmp.log import get_logger
from gpmp.player import Library, TrackTimingInfo, TrackPlayer

log = get_logger()

def seconds_to_minutes_str(secs):
   mins = int(secs / 60)
   secs = int(secs) % 60
   return "{}:{:02d}".format(mins, secs)

class Settings:
   def __init__(self):
      self.settings = QtCore.QSettings("gplaymusicplayer")

   def set_theme(self, theme):
      self.settings.setValue("theme", theme)

   def theme(self):
      return self.settings.value("theme", "light")

class Window(QtWidgets.QMainWindow):
   key_pressed_signal = QtCore.Signal(QtGui.QKeyEvent)
   theme_changed_signal = QtCore.Signal(str)

   def __init__(self, theme):
      super().__init__()
      self.setWindowTitle("gplaymusicplayer")
      self.settings = Settings()
      self.theme_actions = {}
      self.widget = WindowContent()
      self.setCentralWidget(self.widget)
      self.layout_menu()
      self.set_checked_theme(theme)

   def layout_menu(self):
      mb = self.menuBar()
      #  mb.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
      mb.setHidden(True)

      edit_menu = mb.addMenu("&Edit")
      theme_menu = edit_menu.addMenu("Theme")

      self.theme_act_grp = QtWidgets.QActionGroup(theme_menu)
      self.theme_act_grp.setExclusive(True)

      def _add_theme(attr_name, name):
         nonlocal theme_menu
         action = QtWidgets.QAction(name)
         self.theme_actions[attr_name] = action
         action.setCheckable(True)
         action.triggered.connect(self.on_theme_action_triggered)
         self.theme_act_grp.addAction(action)
         theme_menu.addAction(action)

      _add_theme("light", "Light")
      _add_theme("dark", "Dark")

   # Overrides
   def keyPressEvent(self, event):
      super(Window, self).keyPressEvent(event)
      self.key_pressed_signal.emit(event)

   def toggle_window_hidden(self):
      mb = self.menuBar()
      hidden = mb.isHidden()
      # Toggle menu visibility
      mb.setHidden(not hidden)
      hidden = not hidden
      if hidden:
         mb.clearFocus()
      else:
         mb.setFocus()

   def set_checked_theme(self, theme):
      if theme not in self.theme_actions:
         return

      for theme_, theme_act in self.theme_actions.items():
         theme_act.setChecked(theme == theme_)

   def on_theme_action_triggered(self):
      for theme, theme_act in self.theme_actions.items():
         if theme_act.isChecked():
            self.theme_changed_signal.emit(theme)
            return

class WindowContent(QtWidgets.QWidget):
   # pylint: disable-msg=too-many-instance-attributes
   progress_bar_max = 500

   AllSongsItem = object()

   def __init__(self):
      super().__init__()
      self.layout_player()

   # pylint: disable-msg=too-many-statements,attribute-defined-outside-init
   def layout_player(self):
      self.playlist_list = QtWidgets.QListView()
      self.playlist_list.setAlternatingRowColors(True)
      self.playlist_list_model = QtGui.QStandardItemModel()
      self.playlist_list.setModel(self.playlist_list_model)
      self.playlist_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

      self.selected_track_index = None
      self.track_list = QtWidgets.QListView()
      self.track_list.setAlternatingRowColors(True)
      self.track_list_model = QtGui.QStandardItemModel()
      self.track_list.setModel(self.track_list_model)
      self.track_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
      self.track_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

      self.track_info = QtWidgets.QLabel("Unknown - Unknown")
      self.track_info.setAlignment(QtCore.Qt.AlignHCenter)
      sp = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
      self.track_info.setSizePolicy(sp)

      self.progress_bar = QtWidgets.QProgressBar()
      self.progress_bar.setFormat("")
      self.progress_bar.setMaximumHeight(10)
      self.progress_bar.setMinimum(0)
      self.progress_bar.setMaximum(self.progress_bar_max)

      self.progress_text = QtWidgets.QLabel()
      self.progress_text.setAlignment(QtCore.Qt.AlignLeft)

      self.update_progress(None)

      # Despite the policy being "maximum", this shrinks the button to the
      # text size
      sp = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

      button_stylesheet = ("padding-left: 15px; padding-right: 15px; "
                           "padding-top: 4px; padding-bottom: 4px;")
      self.previous_button = QtWidgets.QPushButton("\u23EE")
      self.previous_button.setSizePolicy(sp)
      self.previous_button.setStyleSheet(button_stylesheet)

      self.play_pause_button = QtWidgets.QPushButton("\u23EF")
      self.play_pause_button.setSizePolicy(sp)
      self.play_pause_button.setStyleSheet(button_stylesheet)

      self.next_button = QtWidgets.QPushButton("\u23ED")
      self.next_button.setSizePolicy(sp)
      self.next_button.setStyleSheet(button_stylesheet)

      self.loading_text = QtWidgets.QLabel()
      self.loading_text.setAlignment(QtCore.Qt.AlignLeft)
      self.loading_text.setSizePolicy(sp)

      # Layouts:
      self.button_layout = QtWidgets.QHBoxLayout()
      self.button_layout.addWidget(self.progress_text)
      self.button_layout.addWidget(self.previous_button)
      self.button_layout.addWidget(self.play_pause_button)
      self.button_layout.addWidget(self.next_button)

      self.upper_layout = QtWidgets.QSplitter()
      self.upper_layout.addWidget(self.playlist_list)
      self.upper_layout.addWidget(self.track_list)
      self.upper_layout.setSizes([200, 300])

      self.loading_status_layout = QtWidgets.QHBoxLayout()
      self.loading_status_layout.addWidget(self.loading_text)
      sp = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

      self.layout = QtWidgets.QVBoxLayout()
      self.layout.addWidget(self.upper_layout)
      self.layout.addWidget(self.track_info)
      self.layout.addWidget(self.progress_bar)
      self.layout.addLayout(self.button_layout)
      self.layout.addLayout(self.loading_status_layout)

      self.setLayout(self.layout)

      self.set_playlist_list_content([])

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
         seconds_to_minutes_str(currtime),
         seconds_to_minutes_str(duration_secs)))

   def set_progress_bar_fract(self, prog):
      self.progress_bar.setValue(prog * self.progress_bar_max)

   def set_song_info(self, song_info: str):
      if song_info is not None:
         self.track_info.setText(song_info)

   def set_playlist_list_content(self, playlists):
      self.playlist_list_model.clear()
      item = QtGui.QStandardItem("All Songs")
      item.setData(WindowContent.AllSongsItem)
      self.playlist_list_model.appendRow(item)

      item = QtGui.QStandardItem("Playlists")
      item.setFlags(QtCore.Qt.NoItemFlags)
      self.playlist_list_model.appendRow(item)

      for playlist in playlists:
         item = QtGui.QStandardItem(playlist['name'])
         item.setData(playlist)
         self.playlist_list_model.appendRow(item)

   def set_track_list_content(self, song_ids, library):
      self.track_list_model.clear()
      unknown_song_str = "Unknown - Unknown"
      for song_id in song_ids:
         song_info = library.songs.get(song_id)
         song_str = unknown_song_str
         if song_info:
            song_str = "{0} - {1}".format(song_info['title'], song_info['artist'])
         else:
            log.error("Could not find track info for %s", song_id)

         item = QtGui.QStandardItem(song_str)
         self.track_list_model.appendRow(item)

      # first track always auto-plays right now
      self.set_selected_track_in_list(0)

   def set_selected_track_in_list(self, index, unselect=False):
      if not unselect and self.selected_track_index is not None:
         self.set_selected_track_in_list(self.selected_track_index, unselect=True)

      qindex = self.track_list_model.item(index).index()
      rect = self.track_list.rectForIndex(qindex)

      if unselect:
         self.track_list.setSelection(rect, QtCore.QItemSelectionModel.Clear)
      else:
         self.track_list.setSelection(rect, QtCore.QItemSelectionModel.Select)

      self.selected_track_index = index

   def set_loading_status(self, loading_status_str):
      if loading_status_str is None:
         self.loading_text.setText("")
      else:
         self.loading_text.setText(loading_status_str)

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

class LibraryLoaderWorkerObject(QtCore.QObject):
   load_library_done_signal = QtCore.Signal()
   load_playlists_done_signal = QtCore.Signal()

   def __init__(self, player: TrackPlayer, library: Library,
                parent=None):
      super().__init__(parent)
      self.player = player
      self.library = library

   def load_library(self):
      log.debug("")
      try:
         self.player.initialize()

         self.library.load_core()

         log.debug("done")
         self.load_library_done_signal.emit()
      except Exception as e: # pylint: disable-msg=broad-except
         print("load_library caught exception", e)
         log.error("caught exception: %s", e)

   def load_playlist_contents(self):
      log.debug("")
      try:
         self.library.load_playlist_contents()

         log.debug("done")
         self.load_playlists_done_signal.emit()
      except Exception as e: # pylint: disable-msg=broad-except
         print("load_playlist_contents caught exception", e)
         log.error("caught exception: %s", e)

class PlayerStateMonitorThread(QtCore.QThread):
   prog_signal = QtCore.Signal(TrackTimingInfo)
   song_index_signal = QtCore.Signal(int)
   song_info_signal = QtCore.Signal(str)

   def __init__(self, player: TrackPlayer):
      QtCore.QThread.__init__(self)

      self.player = player
      self.current_song_index = None
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
         self.prog_signal.emit(self.player.get_timing_info())

         player_current_song_index = self.player.current_track_index.value
         if player_current_song_index != self.current_song_index:
            self.current_song_index = player_current_song_index
            self.song_index_signal.emit(player_current_song_index)

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
   # pylint: disable-msg=too-many-instance-attributes

   worker_start_signal = QtCore.Signal()
   load_player_start_signal = QtCore.Signal()
   load_playlists_start_signal = QtCore.Signal()

   worker_interrupt_signal = QtCore.Signal()

   def __init__(self, qapp, api, hotkey_mgr, player, init_player=True):
      # Note qapp is being used as the parent attribute in the super
      super().__init__(qapp)

      self.settings = Settings()

      self.api = api
      self.hotkey_mgr = hotkey_mgr
      self.player = player
      #  self.sr.player.value = player
      self.init_player = init_player

      self.library = self.player.library

      self.pending_playlist_action = None

      if not self.api.is_authenticated() and self.init_player:
         authenticate_client(self.api)

      # Create a gui object.
      self.window = Window(self.settings.theme())
      self.gui = self.window.widget
      self.window.resize(500, 500)

      self.set_theme(self.settings.theme())

      self.connect_controls()

      # Create a new worker thread.
      self.create_worker_threads()

      # Make any cross object connections.
      #  self._connectSignals()

      self.window.show()

   @property
   def app(self):
      return self.parent()

   def connect_controls(self):
      if self.player:
         self.gui.play_pause_button.clicked.connect(self.player.toggle_play)
         self.gui.next_button.clicked.connect(self.player.play_next_track)
         self.gui.previous_button.clicked.connect(
            self.player.handle_previous_track_action)

      self.gui.playlist_list.doubleClicked.connect(self.handle_playlist_item_click)
      self.gui.track_list.doubleClicked.connect(self.handle_track_item_click)

      self.window.theme_changed_signal.connect(self.set_theme)
      self.window.key_pressed_signal.connect(self.on_window_key_press)

   def create_worker_threads(self):
      self.parent().aboutToQuit.connect(self.force_worker_quit)

      self.loader_worker = LibraryLoaderWorkerObject(self.player,
                                                     self.library)
      self.worker_thread = QtCore.QThread()
      self.loader_worker.moveToThread(self.worker_thread)
      self.loader_worker.load_library_done_signal.connect(self.handle_player_loaded)
      self.loader_worker.load_playlists_done_signal.connect(
         self.handle_playlists_loaded)
      self.load_player_start_signal.connect(self.loader_worker.load_library)
      self.load_playlists_start_signal.connect(
         self.loader_worker.load_playlist_contents)
      self.worker_thread.start()

      if self.init_player:
         self.gui.set_loading_status("Loading library...")
         self.load_player_start_signal.emit()
      #  pdb.set_trace()
      #  self.loader_worker.load_library()

      self.custom_worker_thread = PlayerStateMonitorThread(self.player)
      self.custom_worker_thread.prog_signal.connect(self.gui.update_progress)
      self.custom_worker_thread.song_info_signal.connect(self.gui.set_song_info)
      self.custom_worker_thread.song_index_signal.connect(self.handle_song_changed)
      self.custom_worker_thread.start()

      # Connect any worker signals
      #  self.worker.signalStatus.connect(self.gui.updateStatus)
      #  self.gui.button_start.clicked.connect(self.worker.startWork)
      self.worker_interrupt_signal.connect(self.custom_worker_thread.interrupt)

   def force_worker_quit(self):
      try:
         if self.worker_thread.isRunning():
            # Gracefully quit, once the thread reaches the event loop
            self.worker_thread.quit()
            self.worker_thread.wait()

         if self.custom_worker_thread.isRunning():
            self.worker_interrupt_signal.emit()
            self.custom_worker_thread.wait()
            #  self.custom_worker_thread.terminate()
            #  if self.custom_worker_thread.isRunning():
               #  self.custom_worker_thread.wait()
      except Exception as e: # pylint: disable-msg=broad-except
         log.error("caught exception: %s", e)

   def load_playlists_and_do(self, action):
      if self.library.playlist_contents:
         action()
      else:
         self.gui.set_loading_status("Loading playlists...")
         self.pending_playlist_action = action
         self.load_playlists_start_signal.emit()

   def handle_player_loaded(self):
      self.gui.set_loading_status(None)
      self.gui.set_playlist_list_content(self.library.playlist_meta)

   def handle_playlists_loaded(self):
      self.gui.set_loading_status(None)
      if self.pending_playlist_action:
         self.pending_playlist_action()
         self.pending_playlist_action = None

   def handle_playlist_item_click(self, qindex):
      data = self.gui.playlist_list_model.item(qindex.row()).data()
      log.debug("handle_playlist_item_click: %r, data: %r", qindex, data)
      if data is WindowContent.AllSongsItem:
         self.play_all_songs()
      elif data is not None:
         _id = data['id']
         self.load_playlists_and_do(lambda: self.play_playlist(_id))

   def handle_track_item_click(self, qindex):
      self.player.play_track_at_index(qindex.row())

   def handle_song_changed(self, index):
      if index is not None:
         self.gui.set_selected_track_in_list(index)

   def set_theme(self, theme):
      if theme == "dark":
         self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
      else:
         self.app.setStyleSheet("")

      self.settings.set_theme(theme)

   def on_window_key_press(self, event):
      if event.key() == QtCore.Qt.Key_Alt:
         self.window.toggle_window_hidden()

   # ********************************************************************************
   # Player operations
   # ********************************************************************************

   def play_all_songs(self):
      log.debug("")
      track_ids = list(self.library.songs.keys())

      self.player.set_tracks_to_play(track_ids)
      self.player.shuffle_tracks()
      self.player.play_next_track()

      self.gui.set_track_list_content(track_ids, self.library)

   def play_playlist(self, playlist_id):
      log.debug(playlist_id)
      track_ids = self.library.playlist_contents.get(playlist_id)
      if track_ids is None:
         log.error("Unable to find playlist %s", playlist_id)
         return

      self.player.set_tracks_to_play(track_ids)
      self.player.shuffle_tracks()
      self.player.play_next_track()

      self.gui.set_track_list_content(track_ids, self.library)

def make_app():
   return QtWidgets.QApplication([])
