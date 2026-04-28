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

session.cookies.update({
    "sessionid": "xqy7lkm7ztv1ar6b7nqifinoebhhu19t",
})

def search(query_val, field="last"):
    payload = {
        field: {"value": query_val},
        "col_names": ["player_id", "first", "last", "effective_school_name", "position_played", "state", "class_field"],
        "page_size": 10
    }
    response = session.post("https://ucreport.us/database/get_players", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Results for {field}='{query_val}':")
        results = data.get('results', [])
        if not results:
            print("  No matches.")
        for p in results:
            print(f"  {p.get('first')} {p.get('last')} - {p.get('position_played')} - {p.get('effective_school_name')} ({p.get('state')}) - Class {p.get('class_field')}")
    else:
        print(f"Error: {response.status_code} {response.text}")

print("Testing a few players...")
search("Deal", "last")
search("Braylon", "first")

search("Snell", "last")
search("JayQuan", "first")

search("Johnson", "last")
search("Eli", "first")

search("Lang", "last")
search("Danny", "first")
