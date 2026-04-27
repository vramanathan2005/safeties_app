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

def custom_search(first_val, last_val):
    payload = {
        "col_names": ["player_id", "first", "last", "position_played", "effective_school_name", "state"],
        "page_size": 200
    }
    if last_val:
        payload["last"] = {"value": last_val.lower()}
    if first_val:
        payload["first"] = {"value": first_val.lower()}
        
    response = session.post("https://ucreport.us/database/get_players", json=payload)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            players_data = data
        elif isinstance(data, dict):
            players_data = data.get('content', data.get('results', []))
        else:
            players_data = []
            
        print(f"Search (first='{first_val}', last='{last_val}'): Found {len(players_data)} results.")
        for p in players_data[:5]:
            print(f"  {p.get('first')} {p.get('last')} - {p.get('position_played')} - {p.get('effective_school_name')}")
    else:
        print("Error")

print("--- Gavin Williams ---")
custom_search("gavin", "williams")

print("\n--- Honor Fa’alave-Johnson ---")
custom_search("honor", "johnson")
custom_search("honor", "fa")
custom_search(None, "faalave")

print("\n--- Ta’Shawn Poole ---")
custom_search("tashawn", "poole")
custom_search("ta", "poole")

print("\n--- Junior Tu’upo ---")
custom_search("junior", "tuupo")
custom_search("junior", "tu")

print("\n--- Greedy James ---")
custom_search("greedy", "james")

print("\n--- Semaj Stanford ---")
custom_search("semaj", "stanford")
custom_search(None, "stanford")
