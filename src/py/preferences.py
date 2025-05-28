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
    
    CustomFavorites = Gtk.Template.Child()
    Custom = Gtk.Template.Child()
    Query = Gtk.Template.Child()

    Blacklist = Gtk.Template.Child()
    SavedSearches = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        blacklist = TagBox(tags=SETTINGS.get_strv("blacklist"), editable=True)
        blacklist.set_name("blacklist")
        self.bind_setting(blacklist)
        self.Blacklist.set_child(blacklist)
        saved_searches = saved_seaches_tag()
        self.bind_setting(saved_searches)
        self.SavedSearches.set_child(saved_searches)
        self.CustomFavorites.set_subtitle(os.path.basename(SETTINGS.get_string("favorites")))

    @Gtk.Template.Callback()
    def bind_setting(self, widget):
        widget_signal_map = {Adw.EntryRow: "text", Gtk.Entry: "text", Adw.SwitchRow: "active", Adw.ComboRow: "selected", Adw.SpinRow: "value", TagBox: "tags"}
        signal = widget_signal_map.get(type(widget), None)
        SETTINGS.bind(widget.get_name(), widget, signal, 0)

    @Gtk.Template.Callback()
    def custom_active(self, *_):
        GLib.idle_add(self.Query.set_sensitive, self.Custom.get_active())

    @Gtk.Template.Callback()
    def select_folder(self, *_):
        def set_favorites(dialog, result):
            try:
                folder = dialog.select_folder_finish(result)
                if not hasattr(folder, "get_path"):
                    return
            except:
                return
            SETTINGS.set_string("favorites", folder.get_path())
            self.CustomFavorites.set_subtitle(os.path.basename(folder.get_path()))
        Gtk.FileDialog().select_folder(self.get_root(), callback=set_favorites)

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

def filter_term(terms, post):
    status = []
    tag_string = post["tag_string"].split()
    for term in terms:
        if ":" in term:
            key, value = term.rsplit(":", 1)
            if key in post:
                if str(post[key]).lower() == value or (value == "*" or value == "" and not (post[key] == None or post[key] == False)):
                    status.append(True)
                else:
                    status.append(False)
            else:
                status.append(False)
        else:
            status.append(term in tag_string)
    return all(status)

def filter_func(child, self):
    valid_terms = [t for t in self.Search.get_text().lower().split() if not t.strip().startswith("-")]
    invalid_terms = [t.lstrip("-") for t in self.Search.get_text().lower().split() if t.strip().startswith("-")]
    invalid_terms.extend(SETTINGS.get_strv("blacklist"))
    if SETTINGS.get_boolean("safe-mode") and not child.post["rating"] == "g":
        return False
    status = False if valid_terms else True
    if valid_terms:
        status = filter_term(valid_terms, child.post)
    if invalid_terms:
        if status:
            status = not filter_term(invalid_terms, child.post)
    return status

def sort_func(children):
    s = SETTINGS.get_string("sort")
    if s in ["first-added", "last-added"]:
        children.sort(key=lambda c: c.post["added"], reverse=s == "last-added")
    if s in ["newest", "oldest"]:
        children.sort(key=lambda c: c.post["id"], reverse=s == "newest")
    if s == "random":
        random.shuffle(children)

def searches_sort_func(children):
    children.sort(key=lambda c: c.post["id"], reverse=True)
