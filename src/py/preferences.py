import os
import re
import json
import random

from gi.repository import GLib, Gtk, Gio, Adw

from TagBox import TagBox

APP_ID = "io.github._12012015.Cardboard"
APP_NAME = APP_ID.rsplit(".")[-1]

UI_RESOURCE = "/" + APP_ID.replace(".", "/") + "/gtk/"

SETTINGS = Gio.Settings(schema_id=APP_ID)

@Gtk.Template(resource_path=UI_RESOURCE + "preferences.ui")
class Preferences(Adw.PreferencesDialog):
    __gtype_name__ = "Preferences"
    
    RestoreTabs = Gtk.Template.Child()
    Autocomplete = Gtk.Template.Child()
    SaveFavorites = Gtk.Template.Child()
    CustomFavorites = Gtk.Template.Child()
    Select = Gtk.Template.Child()
    Blank = Gtk.Template.Child()
    Random = Gtk.Template.Child()
    Custom = Gtk.Template.Child()
    Query = Gtk.Template.Child()
    SafeMode = Gtk.Template.Child()
    DeletedPosts = Gtk.Template.Child()
    PendingPosts = Gtk.Template.Child()
    PostsperPage = Gtk.Template.Child()
    ThumbnailSize = Gtk.Template.Child()
    Blacklist = Gtk.Template.Child()
    SavedSearches = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self._Blacklist = TagBox(tags=SETTINGS.get_strv("blacklist"), editable=True)
        self._Blacklist.set_name("blacklist")
        self.Blacklist.set_child(self._Blacklist)
        self._SavedSearches = saved_seaches_tag()
        self.SavedSearches.set_child(self._SavedSearches)
        self.Custom.connect("notify::active", lambda *_: self.Query.set_sensitive(self.Custom.get_active()))
        for widget in ["RestoreTabs", "Autocomplete", "SaveFavorites", "CustomFavorites", "Query", "SafeMode", "DeletedPosts", "PendingPosts", "PostsperPage", "ThumbnailSize", "_Blacklist", "_SavedSearches"]:
            bind_setting(getattr(self, widget))
        self.Select.connect("clicked", select_folder)
        self.Query.set_sensitive(self.Custom.get_active())
        self.CustomFavorites.set_subtitle(os.path.basename(SETTINGS.get_string("favorites")))

def saved_seaches_tag():
    tagbox = TagBox(editable=True)
    tagbox.set_name("saved-searches")
    tags = SETTINGS.get_strv("saved-searches")
    def add_tag(tag):
        widget = Gtk.Box(css_classes=["pill"], css_name="editabletag")
        button = Gtk.Button(icon_name="window-close-symbolic", css_classes=["flat", "circular"], tooltip_text="Remove Tag")
        button.tag = tag
        button.connect("clicked", lambda b: b.get_ancestor(TagBox).remove(b.tag))
        label = Gtk.Label(label=tag)
        label.set_sensitive(not tag in SETTINGS.get_strv("disabled-searches"))
        widget.append(label)
        widget.append(button)
        m = Gtk.GestureClick(button=0)
        m.connect("pressed", toggle_search)
        widget.add_controller(m)
        widget.tag = tag
        tagbox.get_child().append(widget)
        return widget
    tagbox.add_tag = add_tag
    return tagbox

def toggle_search(e, *_):
    widget = e.get_widget().get_first_child()
    state = not widget.get_sensitive()
    widget.set_sensitive(state)
    value = SETTINGS.get_strv("disabled-searches")
    if not state:
        value.append(widget.get_label())
    else:
        value.remove(widget.get_label())
    SETTINGS.set_strv("disabled-searches", value)

def bind_setting(Widget):
    widget_signal_map = {Adw.EntryRow: "text", Gtk.Entry: "text", Adw.SwitchRow: "active", Adw.ComboRow: "selected", Adw.SpinRow: "value", TagBox: "tags"}
    signal = widget_signal_map.get(type(Widget), None)
    SETTINGS.bind(Widget.get_name(), Widget, signal, 0)

def select_folder(button):
    def set_favorites(dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if not hasattr(folder, "get_path"):
                return
        except:
            return
        SETTINGS.set_string("favorites", folder.get_path())
        button.get_ancestor(Adw.ActionRow).set_subtitle(os.path.basename(folder.get_path()))
    Gtk.FileDialog().select_folder(button.get_root(), callback=set_favorites)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text for text in re.split(r"(\d+)", s)]

def get_favorites():
    favdir = SETTINGS.get_string("favorites") if SETTINGS.get_boolean("custom-favorites") else GLib.get_user_data_dir()
    if not os.path.exists(favdir):
        favdir = GLib.get_user_data_dir()
    os.makedirs(GLib.get_user_data_dir(), exist_ok=True)
    jsons = os.path.join(favdir, "jsons")
    posts = os.path.join(favdir, "posts")
    thumbnails = os.path.join(favdir, "thumbnails")
    os.makedirs(jsons, exist_ok=True)
    os.makedirs(posts, exist_ok=True)
    os.makedirs(thumbnails, exist_ok=True)
    return jsons, posts, thumbnails

def tab_filter_func(child):
    if any(tag in child.post["tag_string"].split() for tag in SETTINGS.get_strv("blacklist")):
        return False
    return True

def filter_func(child, self):
    terms = self.Search.get_text().lower().split()
    valid_terms = [t for t in terms if not t.strip().startswith("-")]
    invalid_terms = [t.lstrip("-") for t in terms if t.strip().startswith("-")]
    post = child.post
    string = f"{post['tag_string']} {post['id']} rating:{post['rating']}".lower().split()
    status = False
    if not terms:
        status = True
    if all(t in string for t in valid_terms):
        status = True
    if any(t in item for t in invalid_terms) and invalid_terms:
        status = False
    if any(tag in post["tag_string"].split() for tag in SETTINGS.get_strv("blacklist")):
        status = False
    if SETTINGS.get_boolean("safe-mode") and not post["rating"] == "g":
        status = False
    return status

def sort_func(child1, child2):
    s = SETTINGS.get_string("sort")
    if s == "first-added":
        return (child1.post["added"] > child2.post["added"]) - (child1.post["added"] < child2.post["added"])
    if s == "last-added":
        return (child1.post["added"] < child2.post["added"]) - (child1.post["added"] > child2.post["added"])
    if s == "newest":
        return (child1.post["id"] < child2.post["id"]) - (child1.post["id"] > child2.post["id"])
    if s == "oldest":
        return (child1.post["id"] > child2.post["id"]) - (child1.post["id"] < child2.post["id"])
    if s == "random":
        return random.choice([-1, 0, 1])

def searches_sort_func(child1, child2):
    return (child1.post["id"] < child2.post["id"]) - (child1.post["id"] > child2.post["id"])
