import os
import json
import threading

from gi.repository import GLib, Gtk, Adw, Gio

from MediaWidget import MediaWidget
from TagBox import TagBox

from .preferences import UI_RESOURCE, SETTINGS, get_favorites
from .danbooru import post_download

@Gtk.Template(resource_path=UI_RESOURCE + "post.ui")
class Post(Adw.Bin):
    __gtype_name__ = "Post"
    
    Overlay = Gtk.Template.Child()
    Breakpoint = Gtk.Template.Child()
    Revealer = Gtk.Template.Child()
    Duration = Gtk.Template.Child()
    Children = Gtk.Template.Child()
    Parent = Gtk.Template.Child()
    Children_2 = Gtk.Template.Child()
    Parent_2 = Gtk.Template.Child()
    Info = Gtk.Template.Child()
    Tags = Gtk.Template.Child()
    Favorite = Gtk.Template.Child()
    Download = Gtk.Template.Child()

    def __init__(self, post, catalog=True):
        self.post = post
        self.catalog = catalog
        self.preview = False
        if catalog:
            media = MediaWidget(uri=get_thumbnail(post), load=False, limit=1000)
            super().__init__()
            if post["media_asset"]["duration"] != None:
                m = post["media_asset"]["duration"] + 1
                GLib.idle_add(self.Duration.set_label, f"{int(m // 60):02}:{round(m % 60):02}")
                GLib.idle_add(self.Duration.set_visible, True)
        else:
            media = MediaWidget(uri=get_post_url(post))
            media.set_receives_default(True)
            super().__init__(margin_top=10, margin_start=10, margin_end=10, margin_bottom=10, halign=3)
            GLib.idle_add(self.Breakpoint.set_margin_bottom, 30)
            GLib.idle_add(self.Overlay.set_valign, 3)
            GLib.idle_add(self.Download.set_visible, True)
        GLib.idle_add(self.Overlay.set_child, media)
        if post["parent_id"] != None:
            GLib.idle_add(self.Parent.set_visible, True)
        if post["has_children"] == True:
            GLib.idle_add(self.Children.set_visible, True)

    @Gtk.Template.Callback()
    def parent_clicked(self, *_):
        self.get_root().new_tab(query=f"id:{self.post['parent_id']}")

    @Gtk.Template.Callback()
    def children_clicked(self, *_):
        self.get_root().new_tab(query=f"parent:{self.post['id']}")

    @Gtk.Template.Callback()
    def info_clicked(self, *_):
        page = Adw.PreferencesPage()
        post = self.post
        rating_map = {"g": "General", "s": "Sensitive", "q": "Questionable", "e": "Explicit"}
        rating = rating_map.get(post["rating"], "Unknown")
        status = "Pending" if post["is_pending"] else "Deleted" if post["is_deleted"] else "Active"
        info = [
            ("ID", post["id"]),
            ("Date", GLib.DateTime.new_from_iso8601(post["created_at"]).to_local().format("%c")),
            ("Size", f"{round(post['file_size'] / (1024 * 1024), 2)} MB {post['file_ext']} ({post['image_width']}x{post['image_height']})"),
            ("Source", GLib.Uri.escape_string(post["source"], ":/?=", True)),
            ("Rating", rating),
            ("Status", status)
        ]
        if "added" in post:
            info = [("Added", GLib.DateTime.new_from_unix_utc(post["added"]).to_local().format("%c"))] + info
        for title, _info in info:
                group = Adw.PreferencesGroup(halign=1)
                group.add(Adw.ActionRow(activatable=False, title=title, subtitle=_info, halign=1))
                page.add(group)
        dialog = Adw.Dialog(child=page, content_width=500, content_height=500, presentation_mode=2, css_classes=["osd"])
        dialog.present(self.get_root())

    @Gtk.Template.Callback()
    def tags_clicked(self, *_):
        post = self.post
        page = Adw.PreferencesPage()
        info = {"Artist": post["tag_string_artist"], "Character": post["tag_string_character"],
            "Copyright": post["tag_string_copyright"], "General": post["tag_string_general"],
            "Meta": post["tag_string_meta"]}
        for title, _tags in info.items():
            if _tags != "":
                _tags = _tags.split()
                group = Adw.PreferencesGroup(title=title, halign=1)
                tagbox = TagBox()
                for i in _tags:
                    tag = tagbox.add_tag(i)
                    tag.connect("clicked", lambda b: b.get_root().load_query(query=b.get_label()))
                    m = Gtk.GestureClick(button=2)
                    m.connect("pressed", lambda e, *_: e.get_widget().get_root().new_tab(query=e.get_widget().get_label(), skip=True))
                    tag.add_controller(m)
                group.add(Adw.PreferencesRow(activatable=False, child=tagbox))
                page.add(group)
        dialog = Adw.Dialog(child=page, content_width=500, content_height=500, presentation_mode=2, css_classes=["osd"])
        dialog.present(self.get_root())

    @Gtk.Template.Callback()
    def favorite_button_mapped(self, *_):
        GLib.idle_add(lambda: favorite_status(self.Favorite, self.post["id"]))
        
    @Gtk.Template.Callback()
    def favorite_clicked(self, *_):
        favorite(self.Favorite, self.post)

    @Gtk.Template.Callback()
    def toggle_revealer(self, *_):
        self.Revealer.set_reveal_child(not self.Revealer.get_reveal_child())

    @Gtk.Template.Callback()
    def middle_click(self, *_):
        if self.catalog or self.preview:
            self.get_root().new_tab(query=self.post, skip=True)

    @Gtk.Template.Callback()
    def download_clicked(self, *_):
        post = self.post
        response = post_download(post["file_url"])
        if response == None:
            return
        def result(dialog, result):
            file = dialog.save_finish(result)
            if file:
                file.replace_contents_bytes_async(response, None, False, 0)
        dialog = Gtk.FileDialog(initial_name=f"{post['id']}.{post['file_ext']}")
        dialog.set_title("Save File")
        dialog.save(self.get_root(), None, result)

    def load_favorite(self):
        if SETTINGS.get_boolean("save-files"):
            def do_load():
                post = get_post_url(self.post)
                thumbnail = get_thumbnail(self.post)
                jsons, posts, thumbnails = get_favorites()
                if thumbnails in thumbnail and posts in post:
                    return self.Overlay.get_child().load()
                post_file = next((i for i in os.listdir(posts) if i.rsplit(".")[0] == str(self.post["id"])), False)
                thumbnail_file = next((i for i in os.listdir(thumbnails) if i.rsplit(".")[0] == str(self.post["id"])), False)
                if thumbnail_file:
                    thumbnail_path = os.path.join(thumbnails, thumbnail_file)
                else:
                    thumbnail_file = f"{self.post['id']}.{post.rsplit('.')[-1]}"
                    thumbnail_path = os.path.join(thumbnails, thumbnail_file)
                    response = post_download(thumbnail)
                    file = Gio.File.new_for_path(thumbnail_path)
                    file.replace_contents_bytes_async(response, None, False, 0)
                if post_file:
                    post_path = os.path.join(posts, post_file)
                else:
                    post_file = f"{self.post['id']}.{post.rsplit('.')[-1]}"
                    post_path = os.path.join(posts, post_file)
                    response = post_download(post)
                    file = Gio.File.new_for_path(post_path)
                    file.replace_contents_bytes_async(response, None, False, 0)
                if self.catalog:
                    self.Overlay.get_child().set_property("uri", thumbnail_path)
                else:
                    self.Overlay.get_child().set_property("uri", post_path)
            threading.Thread(target=do_load, daemon=True).start()
        else:
            self.Overlay.get_child().load()
    
def get_post_url(post):
    url = post["file_url"] if not post["file_url"].endswith("zip") else post["large_file_url"]
    if SETTINGS.get_boolean("save-files"):
        jsons, posts, thumbnails = get_favorites()
        file = next((i for i in os.listdir(posts) if i.rsplit(".")[0] == str(post["id"])), False)
        if file:
            url = os.path.join(posts, file)
    return url

def get_thumbnail(post):
    size_map = {0: "180x180", 1: "360x360", 2: "720x720"}
    size = size_map.get(SETTINGS.get_int("thumbnail-size"), "720x720")
    url = next((v["url"] for v in post["media_asset"]["variants"] if v["type"] == size), False)
    if SETTINGS.get_boolean("save-files"):
        jsons, posts, thumbnails = get_favorites()
        file = next((i for i in os.listdir(thumbnails) if i.rsplit(".")[0] == str(post["id"])), False)
        if file:
            url = os.path.join(thumbnails, file)
    return url

def activate(listbox, row):
    def check_widget_loaded(dialog, widget):
        def check():
            content = dialog.get_child()
            if content == widget:
                return False
            if dialog.get_root() == None:
                return False
            if not (hasattr(widget, "Overlay") and isinstance(widget.Overlay.get_child().get_child(), Adw.Spinner)):
                GLib.idle_add(dialog.set_child, widget)
            return True
        GLib.timeout_add(100, check)
    post = Post(row.get_child().post, False)
    post.preview = True
    dialog = Adw.Dialog(child=Adw.Spinner(height_request=360), follows_content_size=True, presentation_mode=2)
    check_widget_loaded(dialog, post)
    dialog.connect("notify::css-classes", center)
    dialog.present(listbox.get_root())

def center(dialog, *_):
    stack = dialog.get_child().get_ancestor(Gtk.Stack)
    if stack != None:
        stack.get_parent().set_halign(3)
    gizmo = dialog.get_child().get_parent().get_parent()
    if gizmo != None:
        gizmo.set_halign(3)

def favorite_status(button, id):
    jsons, posts, thumbnails = get_favorites()
    if os.path.exists(os.path.join(jsons, f"{id}.json")):
        button.set_icon_name("starred-symbolic")
        button.set_tooltip_text("Remove Favorite")
    else:
        button.set_icon_name("star-new-symbolic")
        button.set_tooltip_text("Add Favorite")

def favorite(button, post, skip=False):
    jsons, posts, thumbnails = get_favorites()
    file = os.path.join(jsons, f"{post['id']}.json")
    if os.path.exists(file):
        media = next((i for i in os.listdir(posts) if i.rsplit(".")[0] == str(post["id"])), False)
        thumbnail = next((i for i in os.listdir(thumbnails) if i.rsplit(".")[0] == str(post["id"])), False)
        if media:
            os.remove(os.path.join(posts, media))
        if thumbnail:
            os.remove(os.path.join(thumbnails, thumbnail))
        os.remove(file)
    else:
        post["added"] = GLib.DateTime.new_now_utc().to_unix()
        with open(file, "w") as f:
            json.dump(post, f, separators=(",", ":"))
    if not skip:
        favorite_status(button, post["id"])
