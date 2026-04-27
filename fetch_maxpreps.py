import pandas as pd
import requests
import json
import re
import time
import os

csv_path = 'ucreport_data.csv'
if not os.path.exists(csv_path):
    print(f"Error: {csv_path} not found.")
    exit(1)

df = pd.read_csv(csv_path)

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
}

maxpreps_results = []

for index, row in df.iterrows():
    first = str(row.get('first', '')).strip()
    last = str(row.get('last', '')).strip()
    player_id = row.get('player_id')
    
    print(f"\n[{index+1}/{len(df)}] Searching MaxPreps for: {first} {last}...")
    
    search_url = f"https://www.maxpreps.com/search/?q={first}+{last}"
    
    try:
        r = requests.get(search_url, headers=headers)
        if r.status_code != 200:
            print(f"  -> Search failed with status {r.status_code}")
            time.sleep(1)
            continue
            
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
        if not match:
            print(f"  -> Could not find __NEXT_DATA__ in search results.")
            time.sleep(1)
            continue
            
        data = json.loads(match.group(1))
        props = data.get("props", {}).get("pageProps", {})
        careers = props.get("initialCareerResults", [])
        
        if not careers:
            print(f"  -> No career results found.")
            time.sleep(1)
            continue
            
        football_careers = [c for c in careers if "Boys Football" in c.get('sports', [])]
        best_career = football_careers[0] if football_careers else careers[0]
        
        canonical_url = best_career.get('careerCanonicalUrl')
        if not canonical_url:
            print(f"  -> No canonical URL found for the best career match.")
            time.sleep(1)
            continue
            
        if '?' in canonical_url:
            base, query = canonical_url.split('?', 1)
            stats_url = f"https://www.maxpreps.com{base}football/stats/?{query}"
        else:
            stats_url = f"https://www.maxpreps.com{canonical_url}football/stats/"
            
        print(f"  -> Fetching stats from: {stats_url}")
        
        time.sleep(0.5) 
        
        r_stats = requests.get(stats_url, headers=headers)
        if r_stats.status_code != 200:
            print(f"  -> Stats fetch failed with status {r_stats.status_code}")
            continue
            
        match_stats = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r_stats.text)
        if not match_stats:
            print(f"  -> Could not find __NEXT_DATA__ in stats page.")
            continue
            
        stats_data = json.loads(match_stats.group(1))
        stats_props = stats_data.get("props", {}).get("pageProps", {})
        
        card_props = stats_props.get("statsCardProps", {})
        career_rollup = card_props.get("careerRollup", {})
        groups = career_rollup.get("groups", [])
        
        gp = ""
        solo = ""
        asst = ""
        total_tackles = ""
        t_g = ""
        tfl = ""
        ints = ""
        pd_stat = ""
        
        for group in groups:
            if group.get("name") == "Defense":
                for subgroup in group.get("subgroups", []):
                    if subgroup.get("name") == "Tackles":
                        seasons = subgroup.get("stats", [])
                        if seasons:
                            recent_season = seasons[0].get("stats", [])
                            for stat in recent_season:
                                if stat.get("name") == "GamesPlayed":
                                    gp = stat.get("value")
                                elif stat.get("name") == "Tackles":
                                    solo = stat.get("value")
                                elif stat.get("name") == "Assists":
                                    asst = stat.get("value")
                                elif stat.get("name") == "TotalTackles":
                                    total_tackles = stat.get("value")
                                elif stat.get("name") == "TacklesPerGame":
                                    t_g = stat.get("value")
                                elif stat.get("name") == "TacklesForLoss":
                                    tfl = stat.get("value")
                                    
                    elif subgroup.get("name") == "Defensive Statistics":
                        seasons = subgroup.get("stats", [])
                        if seasons:
                            recent_season = seasons[0].get("stats", [])
                            for stat in recent_season:
                                if stat.get("name") == "INTs":
                                    ints = stat.get("value")
                                elif stat.get("name") == "PassesDefensed":
                                    pd_stat = stat.get("value")
                                    
        print(f"  -> Extracted: GP={gp}, SOLO={solo}, ASST={asst}, TKLS={total_tackles}, T/G={t_g}, TFL={tfl}, INTs={ints}, PD={pd_stat}")
        
        maxpreps_results.append({
            'player_id': player_id,
            'maxpreps_gp': gp,
            'maxpreps_solo': solo,
            'maxpreps_asst': asst,
            'maxpreps_total_tackles': total_tackles,
            'maxpreps_t_g': t_g,
            'maxpreps_tfl': tfl,
            'maxpreps_ints': ints,
            'maxpreps_pd': pd_stat,
            'maxpreps_url': stats_url
        })
        
    except Exception as e:
        print(f"  -> Exception: {e}")
        
    time.sleep(1) 

df_maxpreps = pd.DataFrame(maxpreps_results)
df_maxpreps.to_csv("maxpreps_data.csv", index=False)
print("\nDone! Saved to maxpreps_data.csv")
