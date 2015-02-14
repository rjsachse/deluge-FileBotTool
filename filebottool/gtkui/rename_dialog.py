__author__ = 'jaredanderson'


import gtk
import webbrowser
import os

from deluge.ui.client import client

from twisted.internet import defer

from filebottool.common import Log
from filebottool.common import get_resource

log = Log()

class RenameDialog(object):
    """builds and runs the rename dialog.
    """
    def __init__(self, dialog_settings):
        """sets up the dialog using the settings supplied by the server
        Also loads relevant glade widgets as members

        Args:
         dialog_settings: A dictionary containing the settings to populate.
        """
        self.torrent_ids = dialog_settings["torrent_ids"]
        self.torrent_id = None
        self.files = []
        self.current_torrent_save_path = ""
        if len(dialog_settings["torrent_ids"]) == 1:
            self.torrent_id = dialog_settings["torrent_ids"][0]
            self.files = dialog_settings["files"]
            self.current_torrent_save_path = dialog_settings["torrent_save_path"]

        self.ui_settings = dialog_settings["rename_dialog_last_settings"]
        self.server_filebot_version = dialog_settings["filebot_version"]

        self.glade = gtk.glade.XML(get_resource("rename.glade"))
        self.window = self.glade.get_widget("rename_dialog")

        self.original_files_treeview = self.glade.get_widget("files_treeview")
        self.new_files_treeview = self.glade.get_widget("new_files_treeview")
        self.history_files_treeview = self.glade.get_widget(
            "history_files_treeview")

        if not self.torrent_id:
            self.glade.get_widget("tree_pane").hide()
            self.glade.get_widget("dialog_notebook").set_show_tabs(False)
            self.glade.get_widget("do_dry_run").hide()
            self.glade.get_widget("query_entry").set_sensitive(False)
            self.glade.get_widget("query_label").set_sensitive(False)

        self.database_combo = self.glade.get_widget("database_combo")
        self.rename_action_combo = self.glade.get_widget("rename_action_combo")
        self.on_conflict_combo = self.glade.get_widget("on_conflict_combo")
        self.episode_order_combo = self.glade.get_widget("episode_order_combo")

        self.format_string_entry = self.glade.get_widget("format_string_entry")
        self.query_entry = self.glade.get_widget("query_entry")
        self.download_subs_checkbox = self.glade.get_widget(
            "download_subs_checkbox")
        self.language_code_entry = self.glade.get_widget("language_code_entry")
        self.encoding_entry = self.glade.get_widget("encoding_entry")
        self.output_entry = self.glade.get_widget("output_entry")

        signal_dictionary = {
            "on_toggle_advanced": self.on_toggle_advanced,
            "on_do_dry_run_clicked": self.on_do_dry_run_clicked,
            "on_format_help_clicked": self.on_format_help_clicked,
            "on_execute_filebot_clicked": self.on_execute_filebot_clicked,
            "on_revert_button_clicked": self.on_revert_button_clicked
        }

        self.glade.signal_autoconnect(signal_dictionary)

        combo_data = {}
        for key in dialog_settings:
            try:
                if key.startswith('valid_'):
                    combo_data[key] = dialog_settings[key]
            except KeyError:
                pass

        self.build_combo_boxes(combo_data)
        self.populate_with_settings(self.ui_settings)

        self.init_treestore(self.original_files_treeview,
                            "Original File Structure at {}".format(
                                self.current_torrent_save_path))
        self.init_treestore(self.new_files_treeview, "New File Structure")
        self.init_treestore(self.history_files_treeview, "Current File "
            "Structure at {}".format(self.current_torrent_save_path))
        self.load_treestore((None, self.files), self.original_files_treeview)
        self.load_treestore((None, self.files), self.history_files_treeview)
        treeview = self.glade.get_widget("files_treeview")
        treeview.expand_all()

        self.window.show()

        tree_pane = self.glade.get_widget("tree_pane")
        tree_pane.set_position(tree_pane.allocation.width/2)

    def build_combo_boxes(self, combo_data):
        """builds the combo boxes for the dialog
        Args:
          combo_data: dict of data to be loaded into combo boxes
        """
        log.debug("building database combo box")
        databases = combo_data["valid_databases"]
        self.inflate_list_store_combo(databases, self.database_combo)

        log.debug("building rename action combo box")
        rename_actions = combo_data["valid_rename_actions"]
        self.inflate_list_store_combo(rename_actions, self.rename_action_combo)

        log.debug("building on conflict combo box")
        on_conflicts = combo_data["valid_on_conflicts"]
        self.inflate_list_store_combo(on_conflicts, self.on_conflict_combo)

        log.debug("building episode order combo box")
        episode_orders = combo_data["valid_episode_orders"]
        self.inflate_list_store_combo(episode_orders, self.episode_order_combo)

    def inflate_list_store_combo(self, model_data, combo_widget):
        """inflates an individual combo box
        Args:
          model_data: data to be loaded into a list store (list)
          combo_widget: the widget to load data into.
        """
        list_store = gtk.ListStore(str)
        for datum in model_data:
            list_store.append([datum])

        combo_widget.set_model(list_store)
        renderer = gtk.CellRendererText()
        combo_widget.pack_start(renderer, expand=True)
        combo_widget.add_attribute(renderer, "text", 0)

    def populate_with_settings(self, settings):
        """presets the window with the last settings used in the plugin
        Args:
          settings: The settings dict given by the server.
        """
        log.debug("Previous settings received: {}".format(settings))
        self.glade.get_widget("filebot_version").set_text(
            self.server_filebot_version)

        combo_value_pairs = [
            (self.database_combo, settings["database"]),
            (self.rename_action_combo, settings["rename_action"]),
            (self.on_conflict_combo, settings["on_conflict"]),
            (self.episode_order_combo, settings["episode_order"])
        ]

        log.debug("Setting combo boxes")
        for combo, value in combo_value_pairs:
            combo_model = combo.get_model()
            value_index = [index for index, row in enumerate(combo_model)
                           if row[0] == value][0]
            if not value_index:
                log.warning("could not set {0} to value {1}, value {1} could "
                            "not be found in {0}".format(combo, value))
            else:
                combo.set_active(value_index)

        entry_value_pairs = [
            (self.format_string_entry, settings["format_string"]),
            (self.encoding_entry, settings["encoding"]),
            (self.language_code_entry, settings["language_code"]),
            (self.query_entry, settings["query_override"]),
            (self.output_entry, settings["output"])
        ]

        log.debug("Setting entry widgets")
        for entry, value in entry_value_pairs:
            if value:
                entry.set_text(value)

        log.debug("Setting advanced and subs widgets")
        advanced_options = self.glade.get_widget("advanced_options")
        if advanced_options.get_visible() != settings["show_advanced"]:
            self.on_toggle_advanced()

        if self.download_subs_checkbox.get_active() != settings[
            "download_subs"]:
            self.on_download_subs_toggled()

    def init_treestore(self, treeview, header):
        """builds the treestore that will be used to hold the files info
        Args:
          treeview: treeview widget to initialize.
          header: the column Header to use.
        """
        model = gtk.TreeStore(str, str)
        treeview.set_model(model)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(header, renderer, text=1)
        treeview.append_column(column)

    def load_treestore(self, (save_path, file_data), treeview, clear=False):
        """populates a treestore using a torrents filedata and savepath
        Args:
          (save_path, file_data): tuple conting the save path and files dict.
          treeview: the treeview widget you would like to load data into.
          clear: a bool to notify clearing of treeview widget before writing.
        """
        # TODO: look into deluge's internal treestore functions
        if clear:
            if save_path:
                for column in treeview.get_columns():
                    treeview.remove_column(column)
                self.init_treestore(treeview, "New File Structure at {"
                                              "}".format(save_path))
            model = gtk.TreeStore(str, str)
            treeview.set_model(model)
        if not file_data:
            return
        index_path_pairs = [(f["index"], f["path"]) for f in file_data]
        model = treeview.get_model()
        folder_iterators = {}
        folder_structure = {}
        for index, path in index_path_pairs:
            path_parts = path.split('/')
            if len(path_parts) == 1:
                model.append(None, [index, path])

            else:  # not a single file, torrent is a folder.
                for path_depth in range(len(path_parts)):
                    try:
                        folder_structure[path_depth]
                    except KeyError:
                        folder_structure[path_depth] = []

                    if path_parts[path_depth] not in folder_structure[
                        path_depth]:
                        folder_structure[path_depth].append(path_parts[
                            path_depth])

                        try:
                            parent = folder_iterators[path_depth - 1]
                        except KeyError:
                            parent = None

                        if path_parts[path_depth] == os.path.basename(path):
                            model.append(parent, [str(index), path_parts[
                                path_depth]])
                        else:
                            folder_iterator = model.append(parent,
                                                           ['', path_parts[path_depth]])
                            folder_iterators[path_depth] = folder_iterator

        treeview.expand_all()

    @defer.inlineCallbacks
    def refresh_files(self, *args):
        """
        Refreshes the file data from the server and updates the treestore model
        """
        log.debug("refreshing filedata for torrent {}".format(self.torrent_id))

        torrent_data = yield client.core.get_torrent_status(self.torrent_id,
            ["save_path", "files"])
        log.debug("recieved response from server{}".format(torrent_data))
        save_path = torrent_data["save_path"]
        files = torrent_data["files"]
        self.load_treestore((save_path, files), self.original_files_treeview,
                            clear=True)
        self.load_treestore((save_path, files), self.history_files_treeview,
                            clear=True)


    def collect_dialog_settings(self):
        """collects the settings on the widgets and serializes them into
        a dict for sending to the server.
        returns: a dictionary containing the user's setting values
        """
        settings = {}

        combos = {
            "database": self.database_combo,
            "rename_action": self.rename_action_combo,
            "on_conflict": self.on_conflict_combo,
            "episode_order": self.episode_order_combo
        }
        for setting in combos:
            combo_model = combos[setting].get_model()
            iter = combos[setting].get_active_iter()
            if iter:
                settings[setting] = combo_model[iter][0]

        entries = {
            "format_string": self.format_string_entry,
            "encoding": self.encoding_entry,
            "language_code": self.language_code_entry,
            "query_override": self.query_entry,
            "output": self.output_entry
        }
        for setting in entries:
            settings[setting] = entries[setting].get_text()

        settings["show_advanced"] = self.glade.get_widget(
            "advanced_options").get_visible()
        settings["download_subs"] = self.download_subs_checkbox.get_active()

        log.debug("Collected settings for server: {}".format(settings))
        return settings

    #  Section: UI actions

    def on_download_subs_toggled(self, *args):
        """download subs has been toggled.
        toggles "greying out" of subs options.
        """
        subs_options = self.glade.get_widget("subs_options")
        if subs_options.get_sensitive():
            subs_options.set_sensitive(False)
        else:
            subs_options.set_sensitive(True)

    def on_toggle_advanced(self, *args):
        """Advanced dropdown has been toggled, Show or hide options
        """
        advanced_options = self.glade.get_widget("advanced_options")
        arrow = self.glade.get_widget("advanced_arrow")
        advanced_label = self.glade.get_widget("show_advanced_label")

        if advanced_options.get_visible():
            advanced_options.hide()
            advanced_label.set_text("Show Advanced")
            arrow.set(gtk.ARROW_RIGHT, gtk.SHADOW_NONE)
        else:
            advanced_options.show()
            advanced_label.set_text("Hide Advanced")
            arrow.set(gtk.ARROW_DOWN, gtk.SHADOW_NONE)

    def on_do_dry_run_clicked(self, button):
        """
        executes a dry run to show the user how the torrent is expected to
        look after filebot run.
        """
        handler_settings = self.collect_dialog_settings()
        log.info("sending dry run request to server for torrent {}".format(
            self.torrent_id))
        log.debug("using settings: {}".format(handler_settings))
        self.toggle_button(button)
        d = client.filebottool.do_dry_run(self.torrent_id, handler_settings)
        d.addCallback(self.log_response)
        d.addCallback(self.load_treestore, self.new_files_treeview, clear=True)
        d.addCallback(self.toggle_button, button)

    def on_execute_filebot_clicked(self, button):
        """collects and sends settings, and tells server to execute run using
         them.
        """
        handler_settings = self.collect_dialog_settings()
        log.info("Sending execute request to server for torrents {}".format(
            self.torrent_ids))
        log.debug("Using settings: {}".format(handler_settings))
        self.toggle_button(button)

        client.filebottool.save_rename_dialog_settings(handler_settings)
        d = client.filebottool.do_rename(self.torrent_ids, handler_settings)
        d.addCallback(self.log_response)
        d.addCallback(self.rename_complete)
        d.addCallback(self.toggle_button, button)

    def on_revert_button_clicked(self, button):
        log.info("Sending revert request to server for torrent {}".format(
            self.torrent_id))
        self.toggle_button(button)

        d = client.filebottool.do_revert(self.torrent_id)
        d.addCallback(self.log_response)
        d.addCallback(self.toggle_button, button)
        d.addCallback(self.refresh_files)


    def on_format_help_clicked(self, *args):
        webbrowser.open(r'http://www.filebot.net/naming.html', new=2)
        log.debug('Format expression info button was clicked')

    def rename_complete(self, (success, msg)):
        if success:
            log.debug("Rename Completed.")
            self.window.destroy()
        else:
            log.warning("rename failed with message: {}".format(msg))

    def log_response(self, response):
        log.debug("response from server: {}".format(response))
        return response

    def toggle_button(self, *args):
        """
        toggles the sensitivity of a given button widget.
        NOTE: The final argument passed is the button widget to toggle!!!
        """
        button_widget = args[-1] # workaround for deferd argument passing
        if button_widget.get_sensitive():
            button_widget.set_sensitive(False)
        else:
            button_widget.set_sensitive(True)