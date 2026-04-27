import requests
import json

session = requests.Session()
session.headers.update({
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://ucreport.us",
    "referer": "https://ucreport.us/dashboard/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-csrftoken": "TPwxt7v2mFUyUWWdL7WynvkChRYdgC2K1xwiLcKSnWxhK4gh3pilnXXFTSE4YRnL",
})
session.cookies.update({"sessionid": "xqy7lkm7ztv1ar6b7nqifinoebhhu19t"})

payload = {
    "last": {"value": "snell"},
    "col_names": ["player_id", "first", "last", "position_played", "effective_school_name"],
    "page_size": 10
}
response = session.post("https://ucreport.us/database/get_players", json=payload)
print(response.json())
