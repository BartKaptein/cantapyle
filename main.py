#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets

from mpd import MPDClient
from os import path as os_path

class Playlist(object):
	"""
	Simple playlist object to contain the
	current playlist.
	"""
	def add(self, items = []):
		self.items = items
	
	def get(self, num = None):
		if num != None:
			return(self.items[num])
		else:
			return(self.items)
	
	def reset(self):
		self.items = []
		self.lastversion = 0
	
	def __init__(self):
		self.items = []
		
		# Save the last playlist version so
		# Playlist changes are detectable.
		self.lastversion = 0

Playlist = Playlist()



class Library(object):
	"""
	Simple library object to contain the
	current MPD library view.
	"""
	def add(self, items = []):
		dirs = [
			{"directory" : ""},
			{"directory" : ".."}
		]
		fils = []
		
		for item in items:
			if item.get("directory"):
				dirs.append(item)
			else:
				fils.append(item)
		
		dirs.extend(fils)
		self.items = dirs
	
	def get(self, num = None):
		if num != None:
			return(self.items[num])
		else:
			return(self.items)
	
	def reset(self):
		self.items = []
		self.lastroot = ""
	
	def __init__(self):
		self.items = []
		# Save the last location into this so ".." works
		self.lastroot = ""

Library = Library()



class SettingsObj(QtCore.QSettings):
	"""
	Get and set application settings persistently
	by using QSettings.
	"""
	def __init__(self):
		super(SettingsObj, self).__init__("Cantapyle Project", "Cantapyle")
	
	def setValue(self, key, value):
		"""
		Override setValue to make it sync on every setting.
		"""
		super(SettingsObj, self).setValue(key, value)
		self.sync()
	
	@property
	def winsize(self):
		return self.value(
			"MainWindow/size",
			QtCore.QSize(360, 275)
		)
	
	@winsize.setter
	def winsize(self, size):
		self.setValue("MainWindow/size", size)
	
	@property
	def winpos(self):
		return self.value(
			"MainWindow/pos",
			QtCore.QPoint(200, 200)
		)
	
	@winpos.setter
	def winpos(self, pos):
		self.setValue("MainWindow/pos", pos)
	
	@property
	def server(self):
		return str(self.value(
			"MPDServer",
			"127.0.0.1"
		))
	
	@server.setter
	def server(self, ip):
		self.setValue("MPDServer", ip)
	
	@property
	def port(self):
		return str(self.value(
			"MPDPort",
			"6600"
		))
	
	@port.setter
	def port(self, port):
		self.setValue("MPDPort", port)
	
	@property
	def musicdir(self):
		return self.value(
			"MusicDir",
			"/"
		)
	
	@musicdir.setter
	def musicdir(self, path):
		self.setValue("MusicDir", path)
	
	@property
	def autoconn(self):
		val = self.value(
			"AutoConn",
			"0"
		)
		
		if val == "0": return QtCore.Qt.Unchecked
		if val == "2": return QtCore.Qt.Checked
	
	@autoconn.setter
	def autoconn(self, val):
		self.setValue("AutoConn", val)

Settings = SettingsObj()



class PlayerObj(MPDClient):
	"""
	Wrapper for the MPDClient object.
	"""
	def connect(self, host, port):
		super(PlayerObj, self).connect(host, port)
		self.connected = True

	def disconnect(self):
		self.connected = False
		super(PlayerObj, self).disconnect()
	
	def reset(self):
		self.lastsong = -1
		self.laststate = None
	
	def __init__(self):
		super(PlayerObj, self).__init__()

		self.timeout = 10 # Timeout for connecting
		
		# Used to detect when song changes,
		# Updated by GUI timer.
		self.lastsong = -1
		
		# Used to detect when MPD state changes.
		# (Playing,Paused,Stopped).
		# Updated by GUI timer.
		self.laststate = None
		
		self.connected = False

Player = PlayerObj()



# This would support displaying hours, not what I want currently.
#def propertime(secs = 0):
	#m, s = divmod(secs, 60)
	#h, m = divmod(m, 60)
	
	#return "%02d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)

# Turn seconds into M:SS format.
def propertime(sec=0): return "{0}:{1:02d}".format(int(sec / 60), sec % 60)

def require_connected(func):
	def run(*args, **kwargs):
		#print("args: %s, %s") % (repr(args), repr(kwargs))
		if Player.connected:
			try: return(func(*args, **kwargs))
			except Exception as e:
				QtWidgets.QMessageBox.warning(mwin,
					str(e),
					str(e)
				)
				mwin.disconnect_mpd()
		else:
			QtWidgets.QMessageBox.warning(mwin, "Not connected", "Not connected!")

	return(run)

class MainWindow(QtWidgets.QMainWindow):
	def toggle_visibility(self):
		"""
		Hide/show main window.
		"""
		if self.isHidden():
			self.show()
		else:
			if not app.activeWindow(): self.activateWindow()
			else: self.hide()
	
	def closeEvent(self, event):
		"""
		Gets called when the window is closing.
		Save size and position.
		"""
		
		Settings.winsize = self.size()
		Settings.winpos  = self.pos()
		
		self.timer.stop()
		
		event.accept()
	
	def connect_mpd(self):
		"""
		Connect to MPD server.
		"""
		try: Player.connect(Settings.server, Settings.port)
		except Exception as e:
			# Just show a warning
			QtWidgets.QMessageBox.warning(self,
				str(e),
				str(e)
			)
			return
		
		Playlist.reset()
		Library.reset()
		Player.reset()
		
		self.populate_library()
		
		self.timer.start(500)
	
	def disconnect_mpd(self):
		"""
		Disconnect from MPD server.
		"""
		try: Player.disconnect()
		except Exception as e:
			# Just show a warning
			QtWidgets.QMessageBox.warning(self,
				str(e),
				str(e)
			)
		
		self.timer.stop()
		
		self.playlist.clear()
		self.liblist.clear()
		
		self.albumcover.setPixmap(self.nocover)
		self.songtitle.setText("Disconnected")
		self.songwriter.setText("")
		self.songlength.setText("")
		
		self.playbutton.setIcon(self.starticon)
		
		self.songslider.setValue(0)
	
	@require_connected
	def prevsong(self, *args):
		"""
		Go to previous song in playlist.
		"""
		Player.previous()
	
	@require_connected
	def playsong(self, *args):
		"""
		Play or pause current song.
		"""
		if Player.laststate == "play":
			Player.pause()
		else:
			Player.play()
	
	@require_connected
	def stopsong(self, *args):
		"""
		Stop playing current song.
		"""
		Player.stop()
	
	@require_connected
	def nextsong(self, *args):
		"""
		Skip to next song in playlist.
		"""
		Player.next()
	
	def showsearch(self):
		"""
		Show/Hide the search box.
		"""
		if self.searchbox.isHidden():
			self.searchbox.clear()
			self.searchbox.show()
			self.searchbox.setFocus()
		else:
			self.searchbox.hide()
			self.playlistview.setFocus()
	
	def searchsong(self):
		"""
		Search for song from playlist and set focus to it.
		"""
		# Returns a list but we only want one item
		i = self.playlist.match(
			self.playlist.index(0,0),
			QtCore.Qt.DisplayRole,
			self.searchbox.text(), # value
			1, # number of items
			QtCore.Qt.MatchContains
		)
		# No match, do nothing
		if not i: return
		
		self.playlistview.scrollTo(
			i[0],
			QtWidgets.QAbstractItemView.PositionAtCenter
		)
		self.playlistview.setCurrentIndex(i[0])
		
		self.showsearch()
	
	def jumptosong(self):
		"""
		Jump to currently playing song in playlist.
		"""
		self.playlistview.scrollTo(
			self.playlist.index(Player.lastsong, 0),
			QtWidgets.QAbstractItemView.PositionAtCenter
		)
		
		self.playlistview.setCurrentIndex(
			self.playlist.index(Player.lastsong, 0)
		)
		
	@require_connected
	def addplaylist(self, *args):
		"""
		Add current library selection to
		playlist.
		"""
		entry = Library.get(self.libview.currentIndex().row())
		
		if entry.get("directory"):
			Player.add(entry["directory"])
				
		else:
			Player.add(entry["file"])
	
	@require_connected
	def replaceplaylist(self):
		"""
		Replace current playlist with library selection.
		"""
		Player.clear()
		self.addplaylist()

	@require_connected
	def updatelibrary(self):
		"""
		Update current library selection in MPD database.
		"""
		sel = Library.get(self.libview.currentIndex().row())

		Player.update(sel["directory"])
	
	@require_connected
	def rescanlibrary(self):
		"""
		Rescan current library selection into the
		MPD database.
		"""
		sel = Library.get(self.libview.currentIndex().row())

		Player.rescan(sel["directory"])
	
	@require_connected
	def clearplaylist(self):
		"""
		Simply clears the current playlist.
		"""
		Player.clear()
	
	def populate_playlist(self):
		"""
		Adds entries into the playlist model.
		"""
		Playlist.add(Player.playlistinfo())
		self.playlist.clear()
		
		for item in Playlist.get():
			artist = item.get("artist", False)
			title = item.get("title", False)
			length = propertime(int(item["time"]))

			if all([artist, title]):
				song = "{0} - {1}".format(artist, title)
			# Tags missing
			else:
				song = item["file"]
			
			col1 = QtGui.QStandardItem(song)
			col2 = QtGui.QStandardItem(length)
			
			col1.setEditable(False)
			col2.setEditable(False)
			
			self.playlist.appendRow([col1, col2])
		
		self.playlistview.resizeColumnToContents(0)
		self.playlistview.resizeColumnToContents(1)
		
		self.playlist.setHorizontalHeaderLabels(["Song", "Len"])
	
	def populate_library(self, root=""):
		"""
		Adds entries into the library model.
		"""
		Library.add(Player.lsinfo(root))
		Library.lastroot = root # Save root so ".." works
		self.liblist.clear()
		
		# Add dirs and files with different icons.
		# Dirs will be listed first because the listing
		# is sorted during .add().
		# Dir listing will also always have special items "/" and "..".
		for item in Library.get():
			# Directory
			if item.get("directory") != None:
				if item.get("directory") == "":
					name = "/"
				elif item.get("directory") == "..":
					name = ".."
				else:
					name = item["directory"].split("/")[-1]
				
				row = QtGui.QStandardItem(
					QtGui.QIcon("artwork/inode-directory.png"),
					name
				)
			# File
			else:
				row = QtGui.QStandardItem(
					QtGui.QIcon("artwork/audio-x-generic.png"),
					item["file"].split("/")[-1]
				)
			
			row.setEditable(False)
			
			self.liblist.appendRow(row)
	
	@require_connected
	def play_selection(self, selection):
		"""
		Play the selected song from the playlist.
		
		Selection/.row() is only available when clicking on an index,
		so use .currentIndex from view.
		"""
		Player.play(self.playlistview.currentIndex().row())
		
	
	def libitem_clicked(self, selection):
		"""
		Triggered when an library item is clicked,
		Generate the new library view.
		
		Selection/.row() is only available when clicking on an index,
		so use .currentIndex from view.
		"""
		sel = Library.get(self.libview.currentIndex().row())
		
		if sel.get("directory") != None:
			# Special case is needed for ".."
			if sel.get("directory") == "..":
				root = os_path.dirname(Library.lastroot)
			else:
				root = sel.get("directory")
			
			self.populate_library(root)
		else:
			# Do nothing when clicking on files
			pass
	
	def populatemenu(self, menu, entries):
		"""
		Populates given menu object with given entries.
		"""
		for entry in entries:
			name, shortcut, icon, trigger = entry
			
			if name == "separator":
				menu.addSeparator()
				continue
			
			action = menu.addAction(QtGui.QIcon(icon), name, trigger, shortcut)
			action.setShortcut(shortcut)
			action.triggered.connect(lambda: trigger) # Otherwise it's run twice?!
	
	def playlistmenu(self, origin):
		"""
		The menu that is displayed when right clicking
		on the playlist.
		"""
		menu = QtWidgets.QMenu()
		
		entries = (
			#("Name", "Shortcut", "icon", action),
			("Clear", "", "artwork/edit-clear-list.png", self.clearplaylist),
			("separator", None, None, None),
			("Connect", "", "artwork/network-connect.png", self.connect_mpd),
			("Disconnect", "", "artwork/network-disconnect.png", self.disconnect_mpd)
		)
		
		self.populatemenu(menu, entries)
		
		menu.exec_(self.playlistview.mapToGlobal(origin))
	
	def librarymenu(self, origin):
		"""
		The menu that is displayed when right clicking
		on the library.
		"""
		menu = QtWidgets.QMenu()
		
		entries = (
			("Add", "", "artwork/list-add.png", self.addplaylist),
			("Replace", "", "artwork/edit-redo.png", self.replaceplaylist),
			("separator", None, None, None),
			("Update", "", "artwork/folder-new.png", self.updatelibrary),
			("Rescan", "", "artwork/folder-sync.png", self.rescanlibrary)
		)
		
		self.populatemenu(menu, entries)
		
		menu.exec_(self.libview.mapToGlobal(origin))
	
	def mdir_changed(self):
		"""
		Run when return is pressed on
		Settings->Music dir
		"""
		Settings.musicdir = self.mdirinput.text()
	
	def server_changed(self):
		"""
		Run when return is pressed on
		Settings->Server
		"""
		Settings.server = self.serverinput.text()
	
	def port_changed(self):
		"""
		Run when return is pressed on
		Settings->Port
		"""
		Settings.port = self.portinput.text()
	
	def autoconn_checked(self, value):
		"""
		Run when Settings->Auto is checked
		Also connect when setting to enabled
		"""
		Settings.autoconn = value
		
		if value and not Player.connected:
			self.connect_mpd()
	
	@require_connected
	def songslider_changed(self):
		"""
		Run when the song slider is dragged and released.
		"""
		Player.seekcur(self.songslider.value())

	@require_connected
	def volbutton_changed(self, event):
		"""
		Run when mousewheel is used over volume button.
		Update MPD volume in in-/decrements of 5.
		Round the change if necessary.
		"""
		# Always get current value instead of saving in update loop,
		# otherwise this doesn't work properly when spamming changes.
		curvol = int(Player.status().get("volume"))

		if event.angleDelta().y() > 0:
			newvol = curvol + 5
			
			if newvol % 5: newvol -= newvol % 5
		else:
			newvol = curvol
			
			if newvol % 5: newvol -= newvol % 5
			else: newvol -= 5
		
		if 0 <= newvol <= 100:
			Player.setvol(newvol)
			QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), str(newvol))
			self.update_volbutton(newvol)

	def update_volbutton(self, val):
		"""
		Change the volbutton's icon to the appropriate one
		based on MPD volume.
		"""
		if 70 <= val <= 100:
			self.volbutton.setIcon(self.volhighicon)
		elif 40 <= val <= 65:
			self.volbutton.setIcon(self.volmidicon)
		elif 5 <= val <= 35:
			self.volbutton.setIcon(self.vollowicon)
		elif val == 0:
			self.volbutton.setIcon(self.volmuteicon)
		
		self.volbutton.setToolTip(str(val))
		
	def update_songchanged(self, song={}, now=0, prev=0):
		"""
		Update required GUI components when the current
		song changes in MPD.
		"""
		coverpath = os_path.join(
			Settings.musicdir,
			os_path.dirname(song["file"]),
			"cover.jpg"
		)
		
		if os_path.exists(coverpath):
			self.albumcover.setPixmap(QtGui.QPixmap(coverpath))
		else:
			self.albumcover.setPixmap(self.nocover)

		title = song.get("title", song["file"])
		artist = song.get("artist", False)
		album = song.get("album", False)
	
		self.songtitle.setText(title)
		
		if all([artist, album]):
			text = "{0} (on {1})".format(
				song["artist"],
				song["album"]
			)
		# Tags missing
		else:
			text = "Tags missing!"

		self.songwriter.setText(text)
		
		self.songslider.setRange(0, int(song["time"]))
		
		# Bold current song
		# Don't unbold if no last song
		if prev >= 0:
			text = self.playlist.item(prev, 0)
			font = text.font()
			font.setBold(False)
			text.setFont(font)
		
		text = self.playlist.item(now, 0)
		font = text.font()
		font.setBold(True)
		text.setFont(font)
	
	def update_playing(self, time=""):
		"""
		Update required GUI components during playing.
		"""
		now, end = [int(i) for i in time.split(":")]
		
		self.songlength.setText(
			"{0} / {1}".format(
				propertime(now),
				propertime(end)
			)
		)
		
		# Don't update when dragging, causes jerking.
		if not self.songslider.isSliderDown():
			self.songslider.setValue(now)
	
	def update_stopped(self):
		"""
		Update required GUI components when MPD is stopped.
		"""
		self.songtitle.setText("Stopped")
		self.songwriter.setText("")
		self.songlength.setText("")
		
		self.albumcover.setPixmap(self.nocover)
		
		self.songslider.setValue(0)
	
	@require_connected
	def update(self):
		"""
		This is the main loop that is run by a timer.
		Detect changes in MPD status:
		- playlist is changed
		- current song is changed
		- state changes (playing/paused/stopped)
		"""
		status = Player.status()

		# This key is missing if MPD hasn't played anything yet,
		# prevents a KeyError.
		song = int(status.get("song", "0"))	

		# --- Update playlist if changed.
		if status["playlist"] != Playlist.lastversion:
			self.populate_playlist()

			# Bold current song again since the playlist was
			# recreated.
			# Skip on empty playlist
			if self.playlist.rowCount():
				text = self.playlist.item(song, 0)
				font = text.font()
				font.setBold(True)
				text.setFont(font)
		
		Playlist.lastversion = status["playlist"]
		
		# --- Update song information if changed.
		
		if song != Player.lastsong or \
		status["state"] == "play" and Player.laststate == "stop":
			try: self.update_songchanged(
				Playlist.get(song),
				song,
				Player.lastsong
			)
			except: pass # Fails on cleared playlist.
		
		Player.lastsong = song
		
		# --- Update basic information if changed.
		
		state = status.get("state")
		
		if state == "play":
			self.playbutton.setIcon(self.pauseicon)
			self.update_playing(status["time"])
		
		elif state == "pause":
			self.playbutton.setIcon(self.starticon)
		
		elif state == "stop":
			self.playbutton.setIcon(self.starticon)
			self.update_stopped()
		
		Player.laststate = state
		
		# --- Update volume button
		self.update_volbutton(int(status["volume"]))
		
	def __init__(self, parent=None, app=None):
		super(MainWindow, self).__init__()
		
		icon = QtGui.QIcon("artwork/icon.png")
		
		self.setWindowTitle("Cantapyle")
		self.setWindowIcon(icon)
		
		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.update)
		
		# Set size and position from memory
		self.resize(Settings.winsize)
		
		self.move(Settings.winpos)
		
		# Add shortcuts
		exit = QtWidgets.QAction("Exit", self)
		exit.setShortcut("Ctrl+Q")
		exit.triggered.connect(self.close)
		self.addAction(exit)
		
		prev = QtWidgets.QAction("Previous", self)
		prev.setShortcut("F5")
		prev.triggered.connect(self.prevsong)
		self.addAction(prev)
		
		play = QtWidgets.QAction("Play/Pause", self)
		play.setShortcut("F6")
		play.triggered.connect(self.playsong)
		self.addAction(play)
		
		stop = QtWidgets.QAction("Stop", self)
		stop.setShortcut("F7")
		stop.triggered.connect(self.stopsong)
		self.addAction(stop)
		
		next_ = QtWidgets.QAction("Next", self)
		next_.setShortcut("F8")
		next_.triggered.connect(self.nextsong)
		self.addAction(next_)
		
		
		
		# --- Create our player widgets
		
		# Album cover
		self.albumcover = QtWidgets.QLabel()
		
		self.albumcover.setFixedSize(100, 100)
		self.albumcover.setScaledContents(True)
		
		self.nocover = QtGui.QPixmap("artwork/nocover.png")
		self.albumcover.setPixmap(self.nocover)
		
		# Song name
		self.songtitle  = QtWidgets.QLabel()
		self.songtitle.setText("Disconnected")
		self.songtitle.setStyleSheet("font-weight: bold; font-size: 12px;")

		self.songtitle.setSizePolicy(
			QtWidgets.QSizePolicy.Ignored,
			QtWidgets.QSizePolicy.Fixed
		) # Don't resize window to make it fit!

		# Artist (album)
		self.songwriter = QtWidgets.QLabel()
		
		self.songwriter.setSizePolicy(
			QtWidgets.QSizePolicy.Ignored,
			QtWidgets.QSizePolicy.Fixed
		) # Don't resize window to make it fit!
		
		# Song length
		self.songlength = QtWidgets.QLabel()
		
		# Control buttons
		prevbutton = QtWidgets.QPushButton()
		prevbutton.setFocusPolicy(QtCore.Qt.NoFocus)
		prevbutton.setIconSize(QtCore.QSize(24, 24))
		prevbutton.setFixedWidth(32)
		prevbutton.setFlat(True)
		prevbutton.setIcon(QtGui.QIcon("artwork/media-skip-backward.png"))
		
		prevbutton.clicked.connect(self.prevsong)
		
		self.playbutton = QtWidgets.QPushButton()
		self.playbutton.setFocusPolicy(QtCore.Qt.NoFocus)
		self.playbutton.setIconSize(QtCore.QSize(24, 24))
		self.playbutton.setFixedWidth(32)
		self.playbutton.setFlat(True)
		
		# Save these because they're updated often
		self.starticon = QtGui.QIcon("artwork/media-playback-start.png")
		self.pauseicon = QtGui.QIcon("artwork/media-playback-pause.png")
		
		self.playbutton.setIcon(self.starticon)
		
		self.playbutton.clicked.connect(self.playsong)
		
		stopbutton = QtWidgets.QPushButton()
		stopbutton.setFocusPolicy(QtCore.Qt.NoFocus)
		stopbutton.setIconSize(QtCore.QSize(24, 24))
		stopbutton.setFixedWidth(32)
		stopbutton.setFlat(True)
		stopbutton.setIcon(QtGui.QIcon("artwork/media-playback-stop.png"))
		
		stopbutton.clicked.connect(self.stopsong)
		
		nextbutton = QtWidgets.QPushButton()
		nextbutton.setFocusPolicy(QtCore.Qt.NoFocus)
		nextbutton.setIconSize(QtCore.QSize(24, 24))
		nextbutton.setFixedWidth(32)
		nextbutton.setFlat(True)
		nextbutton.setIcon(QtGui.QIcon("artwork/media-skip-forward.png"))
		
		nextbutton.clicked.connect(self.nextsong)
		
		# Song slider
		self.songslider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
		
		self.songslider.setFocusPolicy(QtCore.Qt.NoFocus)
		
		self.songslider.sliderReleased.connect(self.songslider_changed)
		
		# Volume button
		self.volbutton = QtWidgets.QPushButton()
		self.volbutton.setFocusPolicy(QtCore.Qt.NoFocus)
		self.volbutton.setIconSize(QtCore.QSize(24, 24))
		self.volbutton.setFixedWidth(32)
		self.volbutton.setFlat(True)
		
		# Save these
		self.volhighicon = QtGui.QIcon("artwork/audio-volume-high.png")
		self.volmuteicon = QtGui.QIcon("artwork/audio-volume-muted.png")
		self.volmidicon  = QtGui.QIcon("artwork/audio-volume-medium.png")
		self.vollowicon  = QtGui.QIcon("artwork/audio-volume-low.png")
		
		self.volbutton.setIcon(self.volhighicon)
		
		self.volbutton.wheelEvent = self.volbutton_changed
		
		# TabWidget and Views
		tabs = QtWidgets.QTabWidget()
		
		self.playlist = QtGui.QStandardItemModel()
		self.playlist.setColumnCount(2)
		self.playlist.setHorizontalHeaderLabels(["Song", "Len"])
		
		self.playlistview = QtWidgets.QTreeView()
		
		self.playlistview.setRootIsDecorated(False)
		self.playlistview.setAlternatingRowColors(True)
		self.playlistview.header().setSectionsMovable(False)
		self.playlistview.header().setStretchLastSection(True)
		self.playlistview.setModel(self.playlist)
		
		self.playlistview.activated.connect(self.play_selection)
		self.playlistview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.playlistview.customContextMenuRequested.connect(self.playlistmenu)
		
		self.liblist = QtGui.QStandardItemModel()
		
		self.libview = QtWidgets.QListView()
		self.libview.setAlternatingRowColors(True)
		self.libview.setModel(self.liblist)
		
		self.libview.activated.connect(self.libitem_clicked)
		self.libview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.libview.customContextMenuRequested.connect(self.librarymenu)
		
		
		
		# Add hotkeys to playlist, library
		search = QtWidgets.QAction("Search", self.playlistview)
		search.setShortcut("F")
		search.triggered.connect(self.showsearch)
		self.playlistview.addAction(search)
		
		jump = QtWidgets.QAction("Goto", self.playlistview)
		jump.setShortcut("G")
		jump.triggered.connect(self.jumptosong)
		self.playlistview.addAction(jump)
		
		play = QtWidgets.QAction("Play", self.playlistview)
		play.setShortcut("Space")
		play.triggered.connect(self.play_selection)
		self.playlistview.addAction(play)
		
		libsel = QtWidgets.QAction("Select", self.libview)
		libsel.setShortcut("Space")
		libsel.triggered.connect(self.addplaylist)
		self.libview.addAction(libsel)
		
		# Search box
		self.searchbox = QtWidgets.QLineEdit()
		self.searchbox.hide()
		
		self.searchbox.returnPressed.connect(self.searchsong)
		
		sbhide = QtWidgets.QAction("Hide", self.searchbox)
		sbhide.setShortcut("Escape")
		sbhide.triggered.connect(self.showsearch)
		self.searchbox.addAction(sbhide)

		# Widgets for Settings
		settingsctr = QtWidgets.QWidget(self)
		settingstab = QtWidgets.QFormLayout(settingsctr)
		
		settingsctr.setLayout(settingstab)
		
		self.mdirinput   = QtWidgets.QLineEdit(settingsctr)
		self.serverinput = QtWidgets.QLineEdit(settingsctr)
		self.portinput   = QtWidgets.QLineEdit(settingsctr)
		
		self.mdirinput.setText(Settings.musicdir)
		self.serverinput.setText(Settings.server)
		self.portinput.setText(Settings.port)
		
		self.mdirinput.returnPressed.connect(self.mdir_changed)
		self.serverinput.returnPressed.connect(self.server_changed)
		self.portinput.returnPressed.connect(self.port_changed)
		
		autoconn = QtWidgets.QCheckBox(settingsctr)
		
		autoconn.setToolTip("Automatically connect to MPD?")
		autoconn.setCheckState(Settings.autoconn)
		
		autoconn.stateChanged.connect(self.autoconn_checked)
		
		settingstab.addRow("Cover dir:", self.mdirinput)
		settingstab.addRow("Server:", self.serverinput)
		settingstab.addRow("Port:", self.portinput)
		settingstab.addRow("Auto:", autoconn)
		
		
		
		tabs.addTab(
			self.playlistview,
			QtGui.QIcon("artwork/media-playlist-repeat.png"),
			"Playlist"
		)
		
		tabs.addTab(
			self.libview,
			QtGui.QIcon("artwork/folder-sound.png"),
			"Library"
		)
		
		tabs.addTab(
			settingsctr,
			QtGui.QIcon("artwork/preferences-other.png"),
			"Settings"
		)
		
		# Essentially sets the main window's minimum size
		tabs.setMinimumSize(350, 150)
		
		# Add hotkeys to tabs
		
		tab1 = QtWidgets.QAction("Tab1", tabs)
		tab1.setShortcut("F1")
		tab1.triggered.connect(lambda: tabs.setCurrentWidget(self.playlistview))
		tabs.addAction(tab1)
		
		tab2 = QtWidgets.QAction("Tab2", tabs)
		tab2.setShortcut("F2")
		tab2.triggered.connect(lambda: tabs.setCurrentWidget(self.libview))
		tabs.addAction(tab2)
		
		tab3 = QtWidgets.QAction("Tab3", tabs)
		tab3.setShortcut("F3")
		tab3.triggered.connect(lambda: tabs.setCurrentWidget(settingsctr))
		tabs.addAction(tab3)
		
		# TODO
		#tab4 = QtWidgets.QAction("", tabs)
		#tab4.setShortcut("")
		#tab4.triggered.connect()
		#tabs.addAction(tab4)
		
		
		# --- Create our layouts
		
		mainwidget = QtWidgets.QWidget(self)
		mainlayout = QtWidgets.QVBoxLayout(mainwidget)
		
		mainwidget.setLayout(mainlayout)
		
		# Layout for top part of application (album cover,
		# song title, artist and duration)
		topwidget = QtWidgets.QWidget(mainwidget)
		toplayout = QtWidgets.QHBoxLayout(topwidget)
		
		topwidget.setLayout(toplayout)
		
		toplayout.addWidget(self.albumcover)
		
		toplayout.setContentsMargins(0,0,0,0)
		
		# Additional layout for text widgets
		textwidgets = QtWidgets.QWidget(topwidget)
		textlayout  = QtWidgets.QVBoxLayout(textwidgets)
		
		textwidgets.setLayout(textlayout)
		
		textwidgets.setSizePolicy(
			QtWidgets.QSizePolicy.Minimum,
			QtWidgets.QSizePolicy.Fixed
		)
		
		textlayout.setContentsMargins(0,0,0,0)
		
		textlayout.addWidget(self.songtitle)
		textlayout.addWidget(self.songwriter)
		textlayout.addWidget(self.songlength)
		
		toplayout.addWidget(textwidgets)
		
		# Layout for control buttons
		ctrlwidgets = QtWidgets.QWidget(mainwidget)
		ctrllayout  = QtWidgets.QHBoxLayout(ctrlwidgets)
		
		ctrlwidgets.setLayout(ctrllayout)
		
		ctrlwidgets.setSizePolicy(
			QtWidgets.QSizePolicy.Minimum,
			QtWidgets.QSizePolicy.Fixed
		)
		
		ctrllayout.setContentsMargins(0,0,0,0)
		ctrllayout.setSpacing(0)
		
		ctrllayout.addWidget(prevbutton)
		ctrllayout.addWidget(self.playbutton)
		ctrllayout.addWidget(stopbutton)
		ctrllayout.addWidget(nextbutton)
		ctrllayout.addWidget(self.volbutton)
		
		ctrllayout.setAlignment(self.volbutton, QtCore.Qt.AlignRight)
		
		# --- Done!
		
		mainlayout.addWidget(topwidget)
		textlayout.addWidget(ctrlwidgets)
		mainlayout.addWidget(self.songslider)
		mainlayout.addWidget(tabs)
		mainlayout.addWidget(self.searchbox)
		
		self.setCentralWidget(mainwidget)
		
		if autoconn.isChecked():
			self.connect_mpd()



if __name__ == "__main__":
	app = QtWidgets.QApplication([])
	
	mwin = MainWindow(app=app)
	mwin.show()
	
	exit(app.exec_())
