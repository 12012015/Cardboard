import json

from gi.repository import GLib, Soup

from .preferences import SETTINGS

def post_download(url):
    session = Soup.Session()
    session.set_user_agent("cardboard")
    message = Soup.Message(method="GET",  uri=GLib.Uri.parse(url, 0))
    result = session.send_and_read(message)
    if message.get_status() == 200:
        return result
    return None

def json_request(request, params=False):
    try:
        session = Soup.Session()
        session.set_user_agent("cardboard")
        uri = f"https://danbooru.donmai.us/{request}.json"
        if params:
            uri += f"?{params}"
        message = Soup.Message(method="GET",  uri=GLib.Uri.parse(uri, 0))
        result = session.send_and_read(message)
        if message.get_status() == 200:
            return json.loads(result.get_data())
        return None
    except:
        return None

def get_post(id):
    try:
        response = json_request(f"posts/{id}")
        if "file_url" in response:
            return response
        else:
            return None
    except:
        return None

def filter_query(query):
    if SETTINGS.get_boolean("safe-mode"):
        query += " rating:g"
    if not SETTINGS.get_boolean("pending-posts"):
        query += " status:active"
    if SETTINGS.get_boolean("deleted-posts") and SETTINGS.get_boolean("pending-posts"):
        query += " status:any"
    return query

def get_catalog(query, page=1):
    try:
        query = filter_query(query)
        response = json_request("posts", f"tags={query}&page={page}&limit={SETTINGS.get_int('posts-per-page')}")
        return [i for i in response if "file_url" in i and not i["file_url"].endswith("swf")]
    except:
        return []
        
def get_count(query):
    try:
        response = json_request("counts/posts", f"tags={query}")
        return response["counts"]["posts"]
    except:
        return None

def get_suggestions(query):
    try:
        response = json_request("tags", f"search[hide_empty]=yes&search[name_matches]={query}*&search[order]=count")
        if response == None:
            return []
        return response
    except:
        return []
