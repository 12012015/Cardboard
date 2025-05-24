import random
import threading

from gi.repository import GLib, Gio, Gtk, Adw

from MasonryBox import MasonryBox
from MediaWidget import MediaWidget

from .post import Post, activate
from .danbooru import get_post, get_catalog, get_count, filter_query
from .preferences import APP_ID, SETTINGS, tab_filter_func

def new_page(tabview, query=None, skip=True):
    page = tabview.append(Adw.Bin())
    if query == None:
        state = SETTINGS.get_string("new-tab-option")
        if state == "blank":
            query = None
        if state == "random":
            query = f"id:{random.randint(1, 9000000)}"
        if state == "custom":
            query = SETTINGS.get_string("new-tab-query")
    page.query = query
    update_title(page)
    page.get_child().connect("map", lambda *_: GLib.idle_add(do_load_page, page))
    return page

def do_load_page(page):
    if page.get_child().get_child():
        return
    else:
        load_page(page)

def load_page(page, query=False, history=True):
    content = page.get_child()
    GLib.idle_add(content.set_child, Adw.Spinner())
    content.get_root().hide_popovers()
    if query == False:
        query = page.query
    else:
        page.query = query
    if query == None:
        GLib.idle_add(content.set_child, Adw.StatusPage(icon_name=APP_ID, title="Search Danbooru"))
        return GLib.idle_add(content.get_root().update_tab)
    if not hasattr(page, "index") or not hasattr(page, "queries"):
        page.queries = [page.query]
        page.index = 0
    elif history:
        page.queries.append(page.query)
        page.index = len(page.queries) - 1
    GLib.idle_add(content.get_root().set_loading, True)
    GLib.idle_add(page.set_loading, True)
    if isinstance(query, dict):
        check_widget_loaded(page, Post(query, False))
    else:
        def do_load():
            if query.startswith("id:"):
                try:
                    post = get_post(query.lstrip("id:"))
                    widget = Post(post, False)
                    page.query = post
                    update_title(page)
                except:
                    widget = Adw.StatusPage(icon_name="dialog-question-symbolic", title="404", description="Not Found")
                check_widget_loaded(page, widget)
            else:
                data = get_catalog(query)
                if data != []:
                    n = get_count(query)
                def do_show():
                    if not content.get_root():
                        return
                    if data != []:
                        widget = MasonryBox(max_columns=4, child_activate=activate, pairs_only=False, load_in_view=lambda c: c.Overlay.get_child().load())
                        widget.set_filter_func(tab_filter_func)
                        widget.query = query
                        widget.extend(Post(i) for i in data)
                        widget.get_child().connect("edge-reached", next_page)
                        if n == len(widget.children):
                            widget.end = True
                        GLib.idle_add(page.set_title, f"{query} ({n})")
                    else:
                        widget = Adw.StatusPage(icon_name="dialog-question-symbolic", title="404", description="Not Found")
                    GLib.idle_add(content.set_child, widget)
                    GLib.idle_add(content.get_root().set_loading, False)
                    GLib.idle_add(page.set_loading, False)
                    GLib.idle_add(content.get_root().update_tab)
                GLib.idle_add(do_show)
            return False
        threading.Thread(target=do_load, daemon=True).start()

def update_title(page):
    query = page.query
    if isinstance(query, dict):
        title = None
        if query["tag_string_character"]:
            title = query["tag_string_character"].replace(' ', ', ')
        if query["tag_string_artist"]:
            title = (f"{title} by {query['tag_string_artist']}" if title else query["tag_string_artist"])
        if query["tag_string_copyright"] and not title:
            title = query["tag_string_copyright"].replace(' ', ', ')
        title = title or f"{query['id']}"
        keyword = query["tag_string"]
    else:
        title = query if query != None else "Cardboard"
        keyword = query if query != None else "Cardboard"
    GLib.idle_add(page.set_title, title)
    GLib.idle_add(page.set_keyword, keyword)

def check_widget_loaded(page, widget):
    def check():
        content = page.get_child()
        if content.get_child() == widget:
            return False
        if content.get_root() == None:
            return False
        if hasattr(widget, "Overlay") and isinstance(widget.Overlay.get_child().get_child(), Adw.StatusPage):
            GLib.idle_add(content.set_child, Adw.StatusPage(title="404", description="Not Found"))
            GLib.idle_add(content.get_root().set_loading, False)
            GLib.idle_add(page.set_loading, False)
            return False
        if not (hasattr(widget, "Overlay") and isinstance(widget.Overlay.get_child().get_child(), Adw.Spinner)):
            GLib.idle_add(content.set_child, widget)
            GLib.idle_add(content.get_root().set_loading, False)
            GLib.idle_add(page.set_loading, False)
        return True
    GLib.timeout_add(100, check)

def next_page(scrolledwindow, pos):
    masonrybox = scrolledwindow.get_parent()
    if pos == 3 and not hasattr(masonrybox, "end"):
        masonrybox.get_root().set_loading(True)
        _page = masonrybox.get_root().TabView.get_selected_page()
        _page.set_loading(True)
        def do_load():
            page = 2 if not hasattr(masonrybox, "page") else masonrybox.page + 1
            data = get_catalog(masonrybox.query, page)
            if data == None:
                return False
            if data == []:
                masonrybox.end = True
            else:
                def do_add():
                    masonrybox.page = page
                    children = []
                    for i in data:
                        children.append(Post(i))
                    masonrybox.extend(children)
                GLib.idle_add(do_add)
            GLib.idle_add(masonrybox.get_root().set_loading, False)
            GLib.idle_add(_page.set_loading, False)
            return False
        threading.Thread(target=do_load, daemon=True).start()

def tab_ops(window, action):
    if window.Stack.get_page(window.Stack.get_visible_child()).get_title() != "Browse":
        return
    page = window.TabView.get_selected_page()
    if action.props.name == "close":
        if page:
            window.TabView.close_page(page)
    if action.props.name == "reopen-tab":
        if window.closed_tabs == []:
            return
        query = window.closed_tabs[-1]
        window.closed_tabs.remove(query)
        window.new_tab(query=query)
    if action.props.name == "open-in-browser":
        url = "https://danbooru.donmai.us/posts"
        url += f"/{page.query['id']}" if isinstance(page.query, dict) else f"/{page.query.lstrip('id:')}" if isinstance(page.query, str) and page.query.startswith("id:") else f"?tags={filter_query(page.query)}"
        Gio.AppInfo.launch_default_for_uri(url)
    if action.props.name == "backward" or action.props.name == "forward":
        if action.props.name == "backward":
            if page.index > 0:
                page.index -= 1
        if action.props.name == "forward":
            if page.index < len(page.queries) - 1:
                page.index += 1
        load_page(page, page.queries[page.index], False)
    if window.TabView.get_selected_page() == None:
        window.get_application().quit()
