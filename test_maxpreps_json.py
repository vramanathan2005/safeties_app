import requests
import json

url = "https://www.maxpreps.com/_next/data/1777311493/tx/manvel/manvel-mavericks/athletes/karnell-greedy-james-jr/football/stats.json?careerid=ln2n717i44u22"
headers = {
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'
}
try:
    r = requests.get(url, headers=headers)
    data = r.json()
    props = data.get('pageProps', {})
    if 'statsCardProps' in props:
        with open("/Users/varunramanathan/.gemini/antigravity/brain/2204b68d-5173-4469-bbf1-be0dea9e31e0/scratch/stats.json", "w") as f:
            json.dump(props['statsCardProps'], f, indent=2)
        print("Saved to stats.json")
    else:
        print("No statsCardProps")
except Exception as e:
    print(e)
