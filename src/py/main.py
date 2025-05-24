import os
import json
import time
import random
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Soup", "3.0")
from gi.repository import GLib, Gio, Gtk, Adw

from MasonryBox import MasonryBox
from .post import Post, activate, favorite

from .preferences import *
from .danbooru import *
from .tab import new_page, load_page, tab_ops

class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", lambda *_: self.dialog(Adw.AboutDialog(application_name=APP_NAME, application_icon=APP_ID, developer_name="12012015", issue_url=f"https://github.com/12012015/{APP_NAME}/issues", license_type=7, version="1.0.0")))
        self.create_action("preferences", lambda *_: self.dialog(Preferences()))
        
    def do_activate(self):
        if not self.props.active_window:
            Window(self).present()
        
    def dialog(self, dialog):
        self.props.active_window.Popover.set_visible(False)
        dialog.present(self.props.active_window)
        
    def create_action(self, name, callback, shortcuts=False, stateful=None):
        if stateful != None:
            if isinstance(stateful, bool):
                action = Gio.SimpleAction.new_stateful(name, None, GLib.Variant.new_boolean(False))
            else:
                action = Gio.SimpleAction.new_stateful(name, GLib.VariantType.new("s"), stateful)
        else:
            action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
        return action

@Gtk.Template(resource_path=UI_RESOURCE + "window.ui")
class Window(Adw.ApplicationWindow):
    __gtype_name__ = "Window"
    
    ToolbarView = Gtk.Template.Child()
    Stack = Gtk.Template.Child()
    TabView = Gtk.Template.Child()
    TabOverview = Gtk.Template.Child()
    FavOverlay = Gtk.Template.Child()
    SearchOverlay = Gtk.Template.Child()
    Add = Gtk.Template.Child()
    Search = Gtk.Template.Child()
    Search_2  = Gtk.Template.Child()
    Overview = Gtk.Template.Child()
    Menu = Gtk.Template.Child()
    DefaultMenu = Gtk.Template.Child()
    FavMenu = Gtk.Template.Child()
    TabMenu = Gtk.Template.Child()
    Reload = Gtk.Template.Child()
    Popover = Gtk.Template.Child()
    Popover_2 = Gtk.Template.Child()
    Suggestions = Gtk.Template.Child()
    
    def __init__(self, app):
        self.closed_tabs = []
        self.restore = SETTINGS.get_boolean("restore-tabs")
        super().__init__(application=app)
        for attribute in ["default-width", "default-height", "maximized"]:
            SETTINGS.bind(attribute, self, attribute, 0)
        action = self.get_application().create_action
        action("fullscreen", self.fullscreen_action, ["F11"])
        action("overview", lambda *_: self.TabOverview.set_open(not self.TabOverview.get_open()), ["<shift><primary>o"])
        action("new-tab", self.new_tab, ["<primary>t"])
        action("sort", lambda a, s, *_: (a.set_state(s), SETTINGS.set_string("sort", str(s).strip("'"))), stateful=GLib.Variant("s", SETTINGS.get_string("sort")))
        action("new-tab-option", lambda a, s, *_: (a.set_state(s), SETTINGS.set_string("new-tab-option", str(s).strip("'"))), stateful=GLib.Variant("s", SETTINGS.get_string("new-tab-option")))
        action("reload", self.reload, ["<primary>r", "F5"])
        forward = action("forward", lambda a, d: tab_ops(self, a))
        back = action("backward", lambda a, d: tab_ops(self, a))
        action("close", lambda a, d: tab_ops(self, a), ["<primary>w"])
        action("reopen-tab", lambda a, d: tab_ops(self, a), ["<primary><shift>t"])
        action("open-in-browser", lambda a, d: tab_ops(self, a), ["<primary>o"])
        action("add-favorite", self.add_favorite, ["<primary>d"])
        back.set_enabled(False)
        forward.set_enabled(False)
        SETTINGS.connect("changed::sort", lambda *_: self.FavOverlay.get_child().invalidate_sort() if hasattr(self.FavOverlay.get_child(), "invalidate_sort") else None)
        app.connect("shutdown", self.get_pages)
        if SETTINGS.get_boolean("restore-tabs"):
            try:
                tabs = json.loads(SETTINGS.get_string("restore"))
            except:
                tabs = []
        else:
            tabs = []
        if tabs == []:
            page = new_page(self.TabView, skip=True)
        else:
            for query in tabs:
                page = new_page(self.TabView, query, skip=True)
            self.TabView.set_selected_page(page)
        self.Stack.set_visible_child_name(SETTINGS.get_string("stack"))
        self.update_stack(skip=True)

    def get_pages(self, *_):
        pages = self.TabView.get_pages()
        if pages.get_n_items() > 1 and SETTINGS.get_boolean("restore-tabs") and self.restore:
            pages_array = []
            for i in range(pages.get_n_items()):
                page = pages.get_item(i)
                query = page.query
                if query != None:
                    pages_array.append(query)
            var = json.dumps(pages_array, separators=(',', ':'))
            SETTINGS.set_string("restore", var)
    
    @Gtk.Template.Callback()
    def new_tab(self, *_, query=None, skip=False):
        page = new_page(self.TabView, query)
        if not skip:
            current = self.Stack.get_page(self.Stack.get_visible_child()).get_title()
            if current != "Browse":
                self.Stack.set_visible_child_name("Browse")
            self.TabView.set_selected_page(page)
        return page
        
    def load_query(self, *_, search=False, query=False):
        current = self.Stack.get_page(self.Stack.get_visible_child()).get_title()
        if search:
            query = self.Search.get_text()
        if query and current != "Browse":
            page = self.new_tab(query=query)
        else:
            page = self.TabView.get_selected_page()
            load_page(page, query)
        if isinstance(page.query, dict):
            page.text = f"id:{page.query['id']}"
        else:
            page.text = page.query
        
    @Gtk.Template.Callback()
    def append_closed(self, view, page):
        if page.query != None:
            self.closed_tabs.append(page.query)
        page.get_child().set_child(None)
        page.get_child().unparent()
    
    @Gtk.Template.Callback()
    def update_tab(self, *_):
        text = None
        self.hide_popovers()
        page = self.TabView.get_selected_page()
        if self.Stack.get_page(self.Stack.get_visible_child()).get_title() == "Browse" and page:
            back = self.get_application().lookup_action("backward")
            forward = self.get_application().lookup_action("forward")
            if hasattr(page, "index") and hasattr(page, "queries"):
                back.set_enabled(page.index > 0 and len(page.queries) - 1 > 0)
                forward.set_enabled(len(page.queries) - 1 > page.index and len(page.queries) -1 != page.index)
            else:
                back.set_enabled(False)
                forward.set_enabled(False)
            if not hasattr(page, "query"):
                return
            if not hasattr(page, "text"):
                if isinstance(page.query, dict):
                    page.text = f"id:{page.query['id']}"
                else:
                    page.text = page.query
            text = page.text
            text = text if text != None else ""
            page.text = text
            self.Search.set_text(text)
            page.text = text
            self.Search.set_position(-1)
            self.Search_2.set_position(-1)
    
    def fullscreen_action(self, *_):
        if not self.is_fullscreen():
            self.fullscreen()
            self.ToolbarView.set_reveal_bottom_bars(False)
            self.ToolbarView.set_reveal_top_bars(False)
            return
        self.unfullscreen()
        if self.TabOverview.get_open():
            return
        self.ToolbarView.set_reveal_bottom_bars(True)
        self.ToolbarView.set_reveal_top_bars(True)
    
    @Gtk.Template.Callback()
    def update_stack(self, *_, skip=False):
        current = self.Stack.get_page(self.Stack.get_visible_child()).get_title()
        if not skip:
            SETTINGS.set_string("stack", current)
        self.hide_popovers()
        text = ""
        if current == "Browse":
            self.Overview.set_visible(True)
            self.Menu.set_menu_model(self.TabMenu)
            if hasattr(self.TabView.get_selected_page(), "text"):
                text = self.TabView.get_selected_page().text
        if current == "Saved Searches":
            self.Menu.set_menu_model(self.DefaultMenu)
            if hasattr(self.SearchOverlay, "text"):
                text = self.SearchOverlay.text
            if not self.SearchOverlay.get_child() and not skip:
                GLib.idle_add(self.reload)
        if current == "Favorites":
            self.Add.set_visible(True)
            self.Menu.set_menu_model(self.FavMenu)
            if hasattr(self.FavOverlay, "text"):
                text = self.FavOverlay.text
            if not self.FavOverlay.get_child() and not skip:
                GLib.idle_add(self.reload)
        text = text if text != None else ""
        context = self.get_context()
        context.text = text
        self.Search.set_text(text)
        context.text = text
        self.Search.set_position(-1)
        self.Search_2.set_position(-1)
        if current != "Browse":
            self.Overview.set_visible(False)
        if current != "Favorites":
            self.Add.set_visible(False)
    
    def set_loading(self, status):
        if status:
            GLib.idle_add(self.Reload.set_icon_name, "process-stop-symbolic")
        else:
            GLib.idle_add(self.Reload.set_icon_name, "view-refresh-symbolic")
    
    def reload(self, *_):
        if self.Reload.get_icon_name() == "process-stop-symbolic":
            return
        current = self.Stack.get_page(self.Stack.get_visible_child()).get_title()
        if current == "Browse":
            load_page(self.TabView.get_selected_page(), history=False)
        if current == "Favorites":
            GLib.idle_add(self.load_favorites)
        if current == "Saved Searches":
            GLib.idle_add(self.load_searches)
    
    def load_favorites(self, *_):
        self.set_loading(True)
        jsons, posts, thumbnails = get_favorites()
        posts = [i for i in os.listdir(jsons) if i.endswith(".json")]
        if posts == []:
            GLib.idle_add(self.FavOverlay.set_child, Adw.StatusPage(title="No Favorites"))
        else:
            GLib.idle_add(self.FavOverlay.set_child, Adw.Spinner())
            def do_load():
                masonrybox = MasonryBox(child_activate=activate, max_columns=4, lazy_load=SETTINGS.get_int("posts-per-page"), pairs_only=False, load_in_view=lambda c: c.load_favorite())
                start = time.time()
                masonrybox.children = [Post(json.load(open(os.path.join(jsons, post), "r"))) for post in posts]
                print(len(masonrybox.children), "posts in", int(time.time() - start), "seconds")
                GLib.idle_add(self.FavOverlay.set_child, masonrybox)
                masonrybox.set_sort_func(sort_func)
                masonrybox.set_filter_func(filter_func, self)
                GLib.idle_add(masonrybox.order_children)
                self.set_loading(False)
                return False
        if posts != []:
            threading.Thread(target=do_load, daemon=True).start()
        else:
            GLib.idle_add(self.set_loading, False)

    def load_searches(self, *_):
        self.set_loading(True)
        searches = [i for i in SETTINGS.get_strv("saved-searches") if not i in SETTINGS.get_strv("disabled-searches")]
        if searches == []:
            GLib.idle_add(self.SearchOverlay.set_child, Adw.StatusPage(title="No Searches"))
        else:
            GLib.idle_add(self.SearchOverlay.set_child, Adw.Spinner())
        def do_load():
            masonrybox = MasonryBox(child_activate=activate, lazy_load=SETTINGS.get_int("posts-per-page"), max_columns=4, pairs_only=False, load_in_view=lambda c: c.Overlay.get_child().load())
            for tag in searches:
                data = get_catalog(tag)
                for post in data:
                    masonrybox.children.append(Post(post))
            GLib.idle_add(self.SearchOverlay.set_child, masonrybox)
            masonrybox.set_filter_func(filter_func, self)
            masonrybox.set_sort_func(searches_sort_func)
            GLib.idle_add(masonrybox.order_children)
            self.set_loading(False)
            return False
        if SETTINGS.get_strv("saved-searches") != []:
            threading.Thread(target=do_load, daemon=True).start()
        else:
            GLib.idle_add(self.set_loading, False)
    
    @Gtk.Template.Callback()
    def activate_search(self, *_):
        current = self.Stack.get_page(self.Stack.get_visible_child()).get_title()
        row = self.Suggestions.get_child().get_child().get_selected_row()
        if row != None and self.Suggestions.get_mapped() and SETTINGS.get_boolean("autocomplete"):
            self.hide_popovers()
            query = row.get_child().get_first_child().get_label()
            if " " in self.Search.get_text():
                query = f"{' '.join(self.Search.get_text().split()[:-1])} {query}"
            context = self.get_context()
            context.text = query
            self.Search.set_text(query)
            context.text = query
            self.Search.set_position(-1)
            self.Search_2.set_position(-1)
        else:
            self.hide_popovers()
            if current == "Browse":
                self.load_query(search=True)
            else:
                if current == "Favorites":
                    child = self.FavOverlay.get_child()
                if current == "Saved Searches":
                    child = self.SearchOverlay.get_child()
                if hasattr(child, "invalidate_filter"):
                    child.invalidate_filter()
                    visible = [i for i in child.children if hasattr(i, "_filtered") and i._filtered]
                    if visible == []:
                        child.get_parent().get_last_child().set_visible(True)
                    else:
                        child.get_parent().get_last_child().set_visible(False)
        self.hide_popovers()
                
    @Gtk.Template.Callback()
    def hide_popovers(self, *_):
        GLib.idle_add(self.Popover.set_visible, False)
        GLib.idle_add(self.Popover_2.set_visible, False)
    
    def get_context(self):
        if self.Stack.get_page(self.Stack.get_visible_child()).get_title() == "Browse":
            context = self.TabView.get_selected_page()
        if self.Stack.get_page(self.Stack.get_visible_child()).get_title() == "Favorites":
            context = self.FavOverlay
        if self.Stack.get_page(self.Stack.get_visible_child()).get_title() == "Saved Searches":
            context = self.SearchOverlay
        return context
    
    @Gtk.Template.Callback()
    def search_changed(self, *_):
        text = self.Search.get_text()
        popover = self.Popover if self.Search.get_visible() else self.Popover_2
        previous_popover = self.Popover if not self.Search.get_visible() else self.Popover_2
        context = self.get_context()
        if context == None:
            return
        if SETTINGS.get_boolean("autocomplete"):
            def do_load():
                data = get_suggestions(text.rsplit(" ")[-1])
                def do_show():
                    if data != []:
                        self.Suggestions.get_child().get_child().remove_all()
                        for tag in data:
                            box = Gtk.Box(height_request=30, margin_start=6, margin_end=6, spacing=6)
                            for index, text in enumerate([tag["name"], tag["post_count"]]):
                                if index > 0:
                                    text = f"({text})"
                                label = Gtk.Label(label=text)
                                if index > 0:
                                    label.add_css_class("dimmed")
                                box.append(label)
                            self.Suggestions.get_child().get_child().append(box)
                        if not hasattr(self.Suggestions, "popover") or self.Suggestions.popover != popover:
                            self.Suggestions.popover = popover
                            previous_popover.set_child(None)
                            popover.set_child(self.Suggestions)
                        if not popover.get_visible():
                            popover.set_visible(True)
                    else:
                        self.hide_popovers()
                GLib.idle_add(do_show)
            last_term = text.split()[-1] if text else []
            if len(last_term) > 1 and hasattr(context, "text") and text and context.text != text and not text.endswith(" ") and not text.startswith(" "):
                threading.Thread(target=do_load, daemon=True).start()
            else:
                popover.set_visible(False)
        context.text = text
        
    @Gtk.Template.Callback()
    def move_rows(self, a, b, c, e):
        if SETTINGS.get_boolean("autocomplete"):
            selected = self.Suggestions.get_child().get_child().get_selected_row()
            if c == 111 or c == 116:
                new = (selected.get_prev_sibling() if c == 111 and selected else 
                       selected.get_next_sibling() if c == 116 and selected else 
                       self.Suggestions.get_child().get_child().get_first_child())
                if new == None:
                    new = self.Suggestions.get_child().get_child().get_first_child()
                else:
                    self.Suggestions.get_child().get_child().select_row(new)
                return True
        
    def add_favorite(self, *_):
        if self.Stack.get_page(self.Stack.get_visible_child()).get_title() == "Browse" and hasattr(self.TabView.get_selected_page(),"query") and isinstance(self.TabView.get_selected_page().query, dict):
            return self.TabView.get_selected_page().get_child().get_child().Favorite.activate()
        dialog = Adw.AlertDialog(heading="Add Favorite Post", close_response="cancel", default_response="add")
        entry = Adw.EntryRow(title="ID or URL")
        group = Adw.PreferencesGroup()
        group.add(entry)
        dialog.set_extra_child(group)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", 1)
        def do_add():
            post = entry.get_text()
            id = post.split("/posts/")[1].split("?")[0] if post.startswith("https://danbooru.donmai.us/posts/") else post if post.isdigit() else None
            _post = get_post(id)
            if _post != None:
                favorite(None, _post, True)
            dialog.close()
        entry.connect("entry-activated", lambda *_: do_add())
        dialog.connect("response", lambda d, r: do_add() if r == "add" else None)
        dialog.present(self)
        entry.grab_focus()
