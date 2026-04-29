import pandas as pd
import json
import os
import math

ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT_DIR, 'data')
DRAFT_DATA_DIR = os.path.join(DATA_DIR, 'draft')
RECRUIT_DATA_DIR = os.path.join(DATA_DIR, 'recruits')

POSITIONS = {
    'qb': {'name': 'Quarterback', 'recruit_match': ['QB']},
    'rb': {'name': 'Running Back', 'recruit_match': ['RB']},
    'wr': {'name': 'Wide Receiver', 'recruit_match': ['WR']},
    'te': {'name': 'Tight End', 'recruit_match': ['TE']},
    'ol': {'name': 'Offensive Line', 'recruit_match': ['OT', 'OG', 'OL', 'C', 'G', 'T', 'LT', 'RT', 'LG', 'RG']},
    'safety': {'name': 'Safety', 'recruit_match': ['S', 'FS', 'SS', 'Safety']},
    'cb': {'name': 'Cornerback', 'recruit_match': ['CB']},
    'lb': {'name': 'Linebacker', 'recruit_match': ['LB', 'OLB', 'ILB']},
    'de': {'name': 'Defensive End', 'recruit_match': ['DE']},
    'dt': {'name': 'Defensive Tackle', 'recruit_match': ['DT']}
}

def load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    # Read the first few lines to determine header
    with open(path, 'r') as f:
        lines = [f.readline() for _ in range(5)]
    
    skip = 0
    if len(lines) > 0 and 'NFL DRAFT' in lines[0]:
        skip = 1
    
    try:
        # Load with mangled names to handle duplicates
        df = pd.read_csv(path, skiprows=skip)
        
        # Handle cases where the first col is Unnamed (e.g. QB/RB files)
        if 'Unnamed: 0' in df.columns:
            df = df.rename(columns={'Unnamed: 0': 'YEAR'})
            
        # Robustly handle duplicate columns for offense stats (Yds, TD, etc.)
        # RB stats: GP,Car,Yds,Avg,Y/G,Lng,100+,TD (Rushing) then GP,Rec,Yds,Avg,Y/G,Lng,TD (Receiving)
        # WR/TE stats: GP,Rec,Yds,Avg,Y/G,Lng,TD (Receiving) then GP,Car,Yds,Avg,Y/G,Lng,100+,TD (Rushing)
        
        new_cols = []
        counts = {}
        for col in df.columns:
            clean_col = col.split('.')[0] # Remove .1, .2 added by pandas
            if clean_col in ['Yds', 'TD', 'Avg', 'Y/G', 'Lng', 'GP', '100+']:
                counts[clean_col] = counts.get(clean_col, 0) + 1
                if counts[clean_col] == 1:
                    # Keep original for now, but we'll rename later based on position
                    new_cols.append(col)
                else:
                    new_cols.append(f"{clean_col}_{counts[clean_col]}")
            else:
                new_cols.append(col)
        df.columns = new_cols
        return df
    except:
        return pd.DataFrame()

def build_html():
    base_path = ROOT_DIR
    draft_data_path = DRAFT_DATA_DIR
    recruit_data_path = RECRUIT_DATA_DIR
    ucreport_path = os.path.join(recruit_data_path, 'ucreport_data.csv')
    maxpreps_path = os.path.join(recruit_data_path, 'maxpreps_data.csv')
    
    # Load recruit data once
    all_recruits = pd.DataFrame()
    if os.path.exists(ucreport_path) and os.path.exists(maxpreps_path):
        uc_df = pd.read_csv(ucreport_path)
        mp_df = pd.read_csv(maxpreps_path)

        # Drop columns already present in ucreport to avoid _x/_y duplicates
        mp_dup = [c for c in ('query_name', 'source_recruit_id', 'board_position_group', 'board_category') if c in mp_df.columns]
        mp_df = mp_df.drop(columns=mp_dup)

        recruit_df = pd.merge(uc_df, mp_df, on='player_id', how='left')

        # Drop duplicate players (same player_id on multiple board positions)
        recruit_df = recruit_df.drop_duplicates(subset='player_id', keep='first')

        # Save joined CSV so it can be inspected outside the HTML build
        combined_path = os.path.join(recruit_data_path, 'combined_data.csv')
        recruit_df.to_csv(combined_path, index=False)

        recruit_df['NAME'] = recruit_df['first'].astype(str).str.strip() + ' ' + recruit_df['last'].astype(str).str.strip()
        recruit_df['SCHOOL'] = recruit_df['effective_school_name']
        recruit_df['TEAM'] = "High School Recruit"
        recruit_df['HT']   = recruit_df['height']
        recruit_df['WT']   = recruit_df['weight']
        recruit_df['WING'] = recruit_df['wingspan']
        recruit_df['40'] = recruit_df['forty']
        recruit_df['100M'] = recruit_df['track100m']
        recruit_df['VERT'] = recruit_df['vertical']
        recruit_df['BROAD'] = recruit_df['broad']
        recruit_df['SHUT'] = recruit_df['shuttle']
        recruit_df['SHOT'] = recruit_df['trackSP']
        recruit_df['LJ'] = recruit_df['trackLJ']

        def col(name):
            return recruit_df[name] if name in recruit_df.columns else None

        def coalesce(*names):
            result = pd.Series([None] * len(recruit_df), index=recruit_df.index)
            for name in names:
                if name in recruit_df.columns:
                    result = result.combine_first(recruit_df[name])
            return result

        # Passing
        recruit_df['GP']      = coalesce('maxpreps_gp', 'maxpreps_pass_gp', 'maxpreps_tackle_gp', 'maxpreps_rush_gp', 'maxpreps_rec_gp')
        recruit_df['C']       = col('maxpreps_c')
        recruit_df['Att']     = col('maxpreps_att')
        recruit_df['Yds']     = coalesce('maxpreps_pass_yds', 'maxpreps_rush_yds', 'maxpreps_rec_yds')
        recruit_df['C%']      = col('maxpreps_c_pct')
        recruit_df['Avg']     = coalesce('maxpreps_pass_avg', 'maxpreps_rush_avg', 'maxpreps_rec_avg')
        recruit_df['Y/G']     = coalesce('maxpreps_pass_y_g', 'maxpreps_rush_y_g', 'maxpreps_rec_y_g')
        recruit_df['C/G']     = col('maxpreps_c_g')
        recruit_df['TD']      = coalesce('maxpreps_pass_td', 'maxpreps_rush_td', 'maxpreps_rec_td')
        recruit_df['TD/G']    = col('maxpreps_td_g')
        recruit_df['Int']     = col('maxpreps_int')
        recruit_df['Lng']     = coalesce('maxpreps_pass_lng', 'maxpreps_rush_lng', 'maxpreps_rec_lng')
        recruit_df['QBR']     = col('maxpreps_qbr')
        # Rushing
        recruit_df['Car']     = col('maxpreps_car')
        recruit_df['100+']    = col('maxpreps_rush_100_plus')
        recruit_df['Rush_GP'] = col('maxpreps_rush_gp')
        recruit_df['Rush_Car']   = col('maxpreps_car')
        recruit_df['Rush_Yds']   = col('maxpreps_rush_yds')
        recruit_df['Rush_Avg']   = col('maxpreps_rush_avg')
        recruit_df['Rush_Y/G']   = col('maxpreps_rush_y_g')
        recruit_df['Rush_Lng']   = col('maxpreps_rush_lng')
        recruit_df['Rush_100+']  = col('maxpreps_rush_100_plus')
        recruit_df['Rush_TD']    = col('maxpreps_rush_td')
        # Receiving
        recruit_df['Rec']     = col('maxpreps_rec')
        recruit_df['Rec_GP']  = col('maxpreps_rec_gp')
        recruit_df['Rec_Rec'] = col('maxpreps_rec')
        recruit_df['Rec_Yds'] = col('maxpreps_rec_yds')
        recruit_df['Rec_Avg'] = col('maxpreps_rec_avg')
        recruit_df['Rec_Y/G'] = col('maxpreps_rec_y_g')
        recruit_df['Rec_Lng'] = col('maxpreps_rec_lng')
        recruit_df['Rec_TD']  = col('maxpreps_rec_td')
        # Defense
        recruit_df['SOLO']  = col('maxpreps_solo')
        recruit_df['ASST']  = col('maxpreps_asst')
        recruit_df['TKLS']  = col('maxpreps_total_tackles')
        recruit_df['T/G']   = col('maxpreps_t_g')
        recruit_df['TFL']   = col('maxpreps_tfl')
        recruit_df['INT']   = col('maxpreps_ints')
        recruit_df['PD']    = col('maxpreps_pd')
        recruit_df['SACKS'] = col('maxpreps_sacks')
        recruit_df['YDL']   = col('maxpreps_ydl')
        recruit_df['S/G']   = col('maxpreps_s_g')
        recruit_df['HURS']  = col('maxpreps_hurs')

        recruit_df['ROUND'] = None
        recruit_df['is_recruit'] = True
        all_recruits = recruit_df

    position_data = {}
    
    for pos_code, pos_info in POSITIONS.items():
        # OL has no combine/stats CSV — load from UCReport picks file instead
        if pos_code == 'ol':
            ol_path = os.path.join(draft_data_path, 'ol_ucreport_data.csv')
            if not os.path.exists(ol_path):
                continue
            ol_raw = pd.read_csv(ol_path)
            if ol_raw.empty:
                continue
            ol_raw['first'] = ol_raw['first'].astype(str).str.strip()
            ol_raw['last']  = ol_raw['last'].astype(str).str.strip()
            ol_raw['NAME']  = ol_raw['first'] + ' ' + ol_raw['last']
            ol_raw['YEAR']  = ol_raw['wiki_year']
            ol_raw['ROUND'] = pd.to_numeric(ol_raw['wiki_round'], errors='coerce')
            ol_raw['PICK #'] = pd.to_numeric(ol_raw['wiki_pick'], errors='coerce')
            ol_raw['TEAM']  = ol_raw['wiki_team']
            ol_raw['SCHOOL'] = ol_raw['effective_school_name'].fillna(ol_raw.get('wiki_college', ''))
            ol_raw['HT']    = pd.to_numeric(ol_raw['height'],   errors='coerce')
            ol_raw['WT']    = pd.to_numeric(ol_raw['weight'],   errors='coerce')
            ol_raw['40']    = pd.to_numeric(ol_raw['forty'],    errors='coerce')
            ol_raw['SHUT']  = pd.to_numeric(ol_raw['shuttle'],  errors='coerce')
            ol_raw['VERT']  = pd.to_numeric(ol_raw['vertical'], errors='coerce')
            ol_raw['BROAD'] = pd.to_numeric(ol_raw['broad'],    errors='coerce')
            ol_raw['WING']  = pd.to_numeric(ol_raw['wingspan'], errors='coerce')
            ol_raw['100M']  = pd.to_numeric(ol_raw['track100m'],errors='coerce')
            ol_raw['SHOT']  = pd.to_numeric(ol_raw['trackSP'],  errors='coerce')
            ol_raw['LJ']    = pd.to_numeric(ol_raw['trackLJ'],  errors='coerce')
            ol_raw['HJ']    = pd.to_numeric(ol_raw['highJump'], errors='coerce')
            ol_raw['is_recruit'] = False
            df = ol_raw[ol_raw['NAME'].str.strip().str.len() > 0].copy()

            if not all_recruits.empty:
                match_positions = pos_info['recruit_match']
                mask = (
                    all_recruits['position_projected'].isin(match_positions) |
                    all_recruits['position_played'].isin(match_positions)
                )
                pos_recruits = all_recruits[mask].copy()
                if not pos_recruits.empty:
                    df = pd.concat([df, pos_recruits], ignore_index=True)

            records = df.to_dict(orient='records')
            for row in records:
                for k, v in row.items():
                    if isinstance(v, float) and math.isnan(v):
                        row[k] = None
            position_data[pos_code] = {'name': pos_info['name'], 'players': records}
            continue

        combine_path = os.path.join(draft_data_path, f'{pos_code}_combine.csv')
        stats_path = os.path.join(draft_data_path, f'{pos_code}_stats.csv')

        combine_df = load_csv(combine_path)
        stats_df = load_csv(stats_path)

        if combine_df.empty:
            continue
            
        # Clean up average/summary rows (including rows where NAME is NaN)
        combine_df = combine_df[~combine_df['YEAR'].astype(str).str.contains('AVERAGE|Avg', case=False, na=False)]
        combine_df = combine_df[combine_df['NAME'].notna()]
        combine_df = combine_df[combine_df['NAME'].astype(str).str.strip().str.len() > 0]
        combine_df = combine_df[~combine_df['NAME'].astype(str).str.contains('AVERAGE|Avg', case=False, na=False)]
        combine_df['NAME'] = combine_df['NAME'].astype(str).str.strip()
        
        # YEAR column is only filled on the first row of each year-group; forward-fill so all rows
        # in a group carry the correct year before we filter to 2022-2025.
        combine_df['YEAR'] = combine_df['YEAR'].replace('', pd.NA).ffill()
        combine_df['YEAR_NUM'] = pd.to_numeric(combine_df['YEAR'], errors='coerce')
        combine_df = combine_df[(combine_df['YEAR_NUM'] >= 2022) & (combine_df['YEAR_NUM'] <= 2025)]
        combine_df = combine_df.drop(columns=['YEAR_NUM'])
        
        if not stats_df.empty:
            stats_df = stats_df[~stats_df['YEAR'].astype(str).str.contains('AVERAGE|Avg', case=False, na=False)]
            stats_df = stats_df[stats_df['NAME'].notna()]
            stats_df = stats_df[stats_df['NAME'].astype(str).str.strip().str.len() > 0]
            stats_df = stats_df[~stats_df['NAME'].astype(str).str.contains('AVERAGE|Avg', case=False, na=False)]
            stats_df['NAME'] = stats_df['NAME'].astype(str).str.strip()
            
            stats_df['YEAR'] = stats_df['YEAR'].replace('', pd.NA).ffill()
            stats_df['YEAR_NUM'] = pd.to_numeric(stats_df['YEAR'], errors='coerce')
            stats_df = stats_df[(stats_df['YEAR_NUM'] >= 2022) & (stats_df['YEAR_NUM'] <= 2025)]
            stats_df = stats_df.drop(columns=['YEAR_NUM'])
            
            # Specific renaming for position groups
            if pos_code == 'qb':
                # GP,C,Att,Yds,C%,Avg,Y/G,C/G,TD,TD/G,Int,Lng,QBR,GP,Car,Yds,Avg,Y/G,Lng,100+,TD
                # Second set is Rushing
                rename_map = {
                    'GP_2': 'Rush_GP', 'Car': 'Rush_Car', 'Yds_2': 'Rush_Yds', 
                    'Avg_2': 'Rush_Avg', 'Y/G_2': 'Rush_Y/G', 'Lng_2': 'Rush_Lng', 
                    '100+_2': 'Rush_100+', 'TD_2': 'Rush_TD'
                }
                stats_df = stats_df.rename(columns=rename_map)
            elif pos_code == 'rb':
                # GP,Car,Yds,Avg,Y/G,Lng,100+,TD,GP,Rec,Yds,Avg,Y/G,Lng,TD
                # First set is Rushing; second set is Receiving
                rename_map = {
                    'Car': 'Rush_Car', 'Yds': 'Rush_Yds', 'Avg': 'Rush_Avg',
                    'Y/G': 'Rush_Y/G', 'Lng': 'Rush_Lng', '100+': 'Rush_100+',
                    'TD': 'Rush_TD', 'GP_2': 'Rec_GP', 'Rec': 'Rec_Rec', 'Yds_2': 'Rec_Yds',
                    'Avg_2': 'Rec_Avg', 'Y/G_2': 'Rec_Y/G', 'Lng_2': 'Rec_Lng',
                    'TD_2': 'Rec_TD'
                }
                stats_df = stats_df.rename(columns=rename_map)
            elif pos_code in ['wr', 'te']:
                # GP,Rec,Yds,Avg,Y/G,Lng,TD,GP,Car,Yds,Avg,Y/G,Lng,100+,TD
                # First set is Receiving; second set is Rushing
                rename_map = {
                    'Rec': 'Rec_Rec', 'Yds': 'Rec_Yds', 'Avg': 'Rec_Avg',
                    'Y/G': 'Rec_Y/G', 'Lng': 'Rec_Lng', 'TD': 'Rec_TD',
                    'GP_2': 'Rush_GP', 'Car': 'Rush_Car', 'Yds_2': 'Rush_Yds',
                    'Avg_2': 'Rush_Avg', 'Y/G_2': 'Rush_Y/G', 'Lng_2': 'Rush_Lng',
                    '100+_2': 'Rush_100+', 'TD_2': 'Rush_TD'
                }
                stats_df = stats_df.rename(columns=rename_map)

            # Identify columns to merge from stats (everything except metadata)
            meta_cols = ['YEAR', 'PICK', 'ROUND', 'PICK #', 'PLAYER', 'TEAM', 'SCHOOL']
            stat_cols = [c for c in stats_df.columns if c not in meta_cols or c == 'NAME']
            stat_cols = list(set(stat_cols))
            
            # Left join: every combine player gets their stats attached.
            # Then pick up any players who appear ONLY in the stats file (right-only)
            # by doing a separate right-join and appending.
            df = pd.merge(combine_df, stats_df[stat_cols], on='NAME', how='left')
            
            # Find stats-only players (in stats but not combine) and append them
            stats_only = pd.merge(combine_df[['NAME']], stats_df[stat_cols], on='NAME', how='right', indicator=True)
            stats_only = stats_only[stats_only['_merge'] == 'right_only'].drop(columns=['_merge'])
            if not stats_only.empty:
                df = pd.concat([df, stats_only], ignore_index=True)
            
            # Resolve duplicate TEAM/SCHOOL columns if they exist from the merge
            if 'TEAM_y' in df.columns:
                df['TEAM'] = df['TEAM_x'].fillna(df['TEAM_y'])
                df = df.drop(columns=['TEAM_x', 'TEAM_y'])
            if 'SCHOOL_y' in df.columns:
                df['SCHOOL'] = df['SCHOOL_x'].fillna(df['SCHOOL_y'])
                df = df.drop(columns=['SCHOOL_x', 'SCHOOL_y'])
        else:
            df = combine_df
            
        df['is_recruit'] = False
        
        if not all_recruits.empty:
            match_positions = pos_info['recruit_match']
            mask = (
                all_recruits['position_projected'].isin(match_positions) |
                all_recruits['position_played'].isin(match_positions)
            )
            if pos_code == 'safety':
                mask = mask | all_recruits['position_projected'].isin(['ATH']) | all_recruits['position_played'].isin(['ATH'])
            pos_recruits = all_recruits[mask].copy()
            if not pos_recruits.empty:
                df = pd.concat([df, pos_recruits], ignore_index=True)

        num_cols = df.columns.difference(['NAME', 'SCHOOL', 'TEAM', 'is_recruit', 'YEAR', 'PLAYER', 'PICK', 'PICK #', 'maxpreps_url', 'college_level_projection', 'uc_score', 'last', 'first', 'effective_school_name', 'college_enrolled', 'school_city', 'state', 'county', 'position_played', 'position_projected', 'height', 'weight', 'wingspan', 'forty', 'shuttle', 'vertical', 'track60m', 'track100m', 'track200m', 'broad', 'trackLJ', 'highJump', 'trackSP', 'discus', 'updated', 'head_coach', 'player_head_shot', 'camp_event_videos', 'hudl_video_link', 'college_offers', 'commit', 'max_speed_video', 'query_name', 'player_id', 'class_field', 'source_recruit_id', 'source_contact_id', 'board', 'board_position_group', 'board_category', 'board_rank_type', 'board_rank_value'])
        
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        records = df.to_dict(orient='records')
        for row in records:
            for k, v in row.items():
                if isinstance(v, float) and math.isnan(v):
                    row[k] = None
        
        position_data[pos_code] = {
            'name': pos_info['name'],
            'players': records
        }

    json_data = json.dumps(position_data)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Draft Scouting Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #BF5700;
            --primary-dark: #9E4800;
            --bg-color: #F4F7F6;
            --card-bg: #FFFFFF;
            --text-dark: #2C3E50;
            --text-light: #7F8C8D;
            --border: #E2E8F0;
            --success: #2ECC71;
            --nfl-blue: #013369;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-dark);
            padding-bottom: 50px;
        }}
        
        .navbar {{
            background-color: var(--card-bg);
            padding: 15px 50px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .navbar h1 {{
            color: var(--primary);
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        
        .pos-selector-nav {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .pos-selector-nav label {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-light);
        }}
        #position-select {{
            padding: 8px 16px;
            font-size: 15px;
            font-weight: 700;
            border-radius: 8px;
            border: 2px solid var(--primary);
            background-color: white;
            color: var(--primary);
            cursor: pointer;
            outline: none;
            transition: all 0.2s;
        }}
        #position-select:hover {{
            background-color: var(--primary);
            color: white;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 50px;
        }}
        
        .metrics-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            transition: transform 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
        }}
        .metric-title {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-light);
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: 800;
            color: var(--text-dark);
        }}
        
        .panel {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
            margin-bottom: 30px;
        }}
        
        .controls-row {{
            display: flex;
            gap: 20px;
            align-items: flex-end;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
        }}
        
        .control-group {{
            display: flex;
            flex-direction: column;
        }}
        .control-group label {{
            font-size: 12px;
            font-weight: 800;
            color: var(--text-light);
            margin-bottom: 6px;
            text-transform: uppercase;
        }}
        select.control-select {{
            padding: 10px 15px;
            font-size: 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background-color: var(--bg-color);
            color: var(--text-dark);
            width: 200px;
            outline: none;
            font-weight: 600;
        }}
        
        .btn-clear {{
            padding: 10px 20px;
            background-color: #EDF2F7;
            border: none;
            border-radius: 8px;
            color: #4A5568;
            font-weight: 600;
            cursor: pointer;
            display: none;
        }}
        
        .hint-text {{
            font-size: 14px;
            color: #4A5568;
            background-color: #EDF2F7;
            padding: 12px 16px;
            border-radius: 8px;
            border-left: 4px solid var(--primary);
            width: 100%;
        }}
        
        #plot {{
            width: 100%;
            height: 550px;
        }}
        
        .cards-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }}
        .player-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s;
            position: relative;
        }}
        .player-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.1);
        }}
        .card-type-tag {{
            position: absolute;
            top: 0;
            right: 0;
            padding: 4px 12px;
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            border-bottom-left-radius: 10px;
        }}
        .tag-nfl {{ background: var(--nfl-blue); color: white; }}
        .tag-recruit {{ background: var(--success); color: white; }}
        
        .card-header {{
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .card-name {{ font-size: 18px; font-weight: 800; }}
        .card-school {{ font-size: 13px; color: var(--text-light); font-weight: 600; }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .m-label {{ font-size: 9px; font-weight: 800; color: var(--text-light); text-transform: uppercase; }}
        .m-val {{ font-size: 13px; font-weight: 700; }}
        
        .empty-state {{ padding: 60px; text-align: center; color: var(--text-light); grid-column: 1 / -1; }}

        .hover-tooltip {{
            position: fixed;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-left: 4px solid var(--success);
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            z-index: 9999;
            min-width: 200px;
            pointer-events: none;
            display: none;
        }}
        .hover-tooltip .ht-name {{ font-size: 15px; font-weight: 800; margin-bottom: 2px; }}
        .hover-tooltip .ht-school {{ font-size: 12px; color: var(--text-light); font-weight: 600; margin-bottom: 10px; }}
        .hover-tooltip .ht-stat {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; }}
        .hover-tooltip .ht-stat-label {{ font-size: 11px; font-weight: 700; color: var(--text-light); text-transform: uppercase; }}
        .hover-tooltip .ht-stat-val {{ font-size: 20px; font-weight: 800; color: var(--primary); }}
    </style>
</head>
<body>

    <div id="hover-tooltip" class="hover-tooltip">
        <div class="ht-name" id="ht-name"></div>
        <div class="ht-school" id="ht-school"></div>
        <div class="ht-stat">
            <span class="ht-stat-label" id="ht-label"></span>
            <span class="ht-stat-val" id="ht-val"></span>
        </div>
    </div>

    <div class="navbar">
        <h1>Scouting Dashboard</h1>
        <div class="pos-selector-nav">
            <label for="position-select">SELECT POSITION:</label>
            <select id="position-select"></select>
        </div>
    </div>
    
    <div class="container">
        <div class="metrics-container" id="top-metrics"></div>
        
        <div class="panel">
            <div class="controls-row">
                <div class="control-group">
                    <label>View Mode</label>
                    <select id="chart-type" class="control-select">
                        <option value="scatter">Scatter Plot</option>
                        <option value="histogram">Histogram</option>
                    </select>
                </div>
                <div class="control-group">
                    <label id="x-label">Metric A</label>
                    <select id="x-select" class="control-select"></select>
                </div>
                <div class="control-group" id="y-group">
                    <label>Metric B</label>
                    <select id="y-select" class="control-select"></select>
                </div>
                <div class="control-group" style="padding-bottom: 8px;">
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--text-dark); margin: 0; text-transform: none; font-size: 14px; font-weight: 600;">
                        <input type="checkbox" id="toggle-recruits" checked style="width: 18px; height: 18px; accent-color: var(--primary);">
                        Show Recruits
                    </label>
                </div>
                <div class="control-group" style="margin-left: auto; padding-bottom: 5px;">
                    <button id="clear-selection" class="btn-clear">Clear Filter</button>
                </div>
                <div class="hint-text">
                    <i id="dynamic-hint">Use the dropdowns to explore data. Filter by selecting regions on the chart.</i>
                </div>
            </div>
            <div id="plot"></div>
        </div>
        
        <div class="panel">
            <div class="cards-header">
                <h3 id="database-title" style="font-weight: 800;">Player Database</h3>
                <span id="player-count" style="color: var(--text-light); font-size: 14px; font-weight: 700;"></span>
            </div>
            <div id="player-cards-container" class="cards-grid"></div>
        </div>
    </div>

    <script>
        const posData = {json_data};
        // currentPos is set AFTER options are populated so it matches what the dropdown shows
        let currentPos = '';

        
        const metricDefs = {{
            // Physical / Combine
            'HT':     {{ label: 'Height',    unit: 'in',  decimals: 1, dtick: 1,    binSize: 1 }},
            'WT':     {{ label: 'Weight',    unit: 'lbs', decimals: 0, dtick: 10,   binSize: 10 }},
            '40':     {{ label: '40-Yard',   unit: 's',   decimals: 2, dtick: 0.10, binSize: 0.05 }},
            'VERT':   {{ label: 'Vertical',  unit: 'in',  decimals: 1, dtick: 2,    binSize: 1 }},
            'BROAD':  {{ label: 'Broad Jmp', unit: 'in',  decimals: 0, dtick: 6,    binSize: 3 }},
            'SHUT':   {{ label: 'Shuttle',   unit: 's',   decimals: 2, dtick: 0.10, binSize: 0.05 }},
            '3 CONE': {{ label: '3-Cone',    unit: 's',   decimals: 2, dtick: 0.10, binSize: 0.05 }},
            '100M':   {{ label: '100M',      unit: 's',   decimals: 2, dtick: 0.25, binSize: 0.10 }},
            '110HH':  {{ label: '110H',      unit: 's',   decimals: 2, dtick: 0.50, binSize: 0.25 }},
            '200M':   {{ label: '200M',      unit: 's',   decimals: 2, dtick: 0.50, binSize: 0.25 }},
            '300IH':  {{ label: '300H',      unit: 's',   decimals: 2, dtick: 1,    binSize: 0.50 }},
            '400M':   {{ label: '400M',      unit: 's',   decimals: 2, dtick: 1,    binSize: 0.50 }},
            '400R':   {{ label: '400R',      unit: 's',   decimals: 2, dtick: 1,    binSize: 0.50 }},
            'WING':   {{ label: 'Wingspan',  unit: 'in',  decimals: 1, dtick: 1,    binSize: 1 }},
            'HAND':   {{ label: 'Hand Size', unit: 'in',  decimals: 2, dtick: 0.5,  binSize: 0.25 }},
            'HJ':     {{ label: 'High Jump', unit: 'in',  decimals: 1, dtick: 2,    binSize: 1 }},
            'LJ':     {{ label: 'Long Jump', unit: 'in',  decimals: 1, dtick: 6,    binSize: 3 }},
            'TJ':     {{ label: 'Triple Jmp', unit: 'in', decimals: 1, dtick: 12,   binSize: 6 }},
            'SHOT':   {{ label: 'Shot Put',  unit: 'in',  decimals: 1, dtick: 12,   binSize: 6 }},
            'DISCUS': {{ label: 'Discus',    unit: 'in',  decimals: 1, dtick: 24,   binSize: 12 }},
            'JAVELIN':{{ label: 'Javelin',   unit: 'in',  decimals: 1, dtick: 24,   binSize: 12 }},
            // Passing (QB)
            'GP':    {{ label: 'Games',      unit: '', decimals: 0 }},
            'C':     {{ label: 'Completions', unit: '', decimals: 0 }},
            'Att':   {{ label: 'Attempts',   unit: '', decimals: 0 }},
            'Yds':   {{ label: 'Pass Yds',   unit: '', decimals: 0 }},
            'C%':    {{ label: 'Comp %',     unit: '', decimals: 1 }},
            'Avg':   {{ label: 'Yds/Comp',   unit: '', decimals: 1 }},
            'Y/G':   {{ label: 'Pass Y/G',   unit: '', decimals: 1 }},
            'C/G':   {{ label: 'Comp/G',     unit: '', decimals: 1 }},
            'TD':    {{ label: 'Pass TD',    unit: '', decimals: 0 }},
            'TD/G':  {{ label: 'TD/G',       unit: '', decimals: 2 }},
            'Int':   {{ label: 'Pass INT',   unit: '', decimals: 0 }},
            'Lng':   {{ label: 'Long Pass',  unit: '', decimals: 0 }},
            'QBR':   {{ label: 'QBR',        unit: '', decimals: 1 }},
            // Rushing
            'Rush_GP':   {{ label: 'Rush GP',    unit: '', decimals: 0 }},
            'Rush_Car':  {{ label: 'Carries',     unit: '', decimals: 0 }},
            'Rush_Yds':  {{ label: 'Rush Yds',    unit: '', decimals: 0 }},
            'Rush_Avg':  {{ label: 'Rush Avg',    unit: '', decimals: 1 }},
            'Rush_Y/G':  {{ label: 'Rush Y/G',    unit: '', decimals: 1 }},
            'Rush_Lng':  {{ label: 'Rush Long',   unit: '', decimals: 0 }},
            'Rush_TD':   {{ label: 'Rush TD',     unit: '', decimals: 0 }},
            'Rush_100+': {{ label: '100+ Yd Gms', unit: '', decimals: 0 }},
            'Car':       {{ label: 'Carries',     unit: '', decimals: 0 }},
            '100+':      {{ label: '100+ Yd Gms', unit: '', decimals: 0 }},
            // Receiving
            'Rec_GP':  {{ label: 'Rec GP',   unit: '', decimals: 0 }},
            'Rec_Rec': {{ label: 'Receptions', unit: '', decimals: 0 }},
            'Rec_Yds': {{ label: 'Rec Yds',  unit: '', decimals: 0 }},
            'Rec_Avg': {{ label: 'Rec Avg',  unit: '', decimals: 1 }},
            'Rec_Y/G': {{ label: 'Rec Y/G',  unit: '', decimals: 1 }},
            'Rec_Lng': {{ label: 'Rec Long', unit: '', decimals: 0 }},
            'Rec_TD':  {{ label: 'Rec TD',   unit: '', decimals: 0 }},
            // Defense — coverage (CB / Safety)
            'SOLO':  {{ label: 'Solo Tkl',   unit: '', decimals: 0 }},
            'ASST':  {{ label: 'Asst Tkl',   unit: '', decimals: 0 }},
            'TKLS':  {{ label: 'Total Tkl',  unit: '', decimals: 0 }},
            'T/G':   {{ label: 'Tkl/G',      unit: '', decimals: 1 }},
            'TFL':   {{ label: 'TFL',        unit: '', decimals: 1 }},
            'INT':   {{ label: 'INT',        unit: '', decimals: 0 }},
            'PD':    {{ label: 'Pass Def',   unit: '', decimals: 0 }},
            // Defense — pass rush (LB / DE / DT)
            'GP_2':  {{ label: 'Sack GP',    unit: '', decimals: 0 }},
            'SACKS': {{ label: 'Sacks',      unit: '', decimals: 1 }},
            'YDL':   {{ label: 'Yds Lost',   unit: '', decimals: 0 }},
            'S/G':   {{ label: 'Sacks/G',    unit: '', decimals: 2 }},
            'HURS':  {{ label: 'Hurries',    unit: '', decimals: 0 }},
        }};

        const positionMetrics = {{
            qb:     ['HT','WT','WING','HAND','40','SHUT','VERT','100M','110HH','200M','300IH','400M','HJ','LJ','TJ',
                     'GP','C','Att','Yds','C%','Avg','Y/G','C/G','TD','TD/G','Int','Lng','QBR',
                     'Rush_GP','Rush_Car','Rush_Yds','Rush_Avg','Rush_Y/G','Rush_Lng','100+','Rush_TD'],
            rb:     ['HT','WT','WING','HAND','40','SHUT','3 CONE','VERT','BROAD','100M','200M','400M','SHOT','HJ','LJ','TJ',
                     'GP','Rush_Car','Rush_Yds','Rush_Avg','Rush_Y/G','Rush_Lng','Rush_100+','Rush_TD',
                     'Rec_GP','Rec_Rec','Rec_Yds','Rec_Avg','Rec_Y/G','Rec_Lng','Rec_TD'],
            wr:     ['HT','WT','WING','HAND','40','SHUT','VERT','BROAD','100M','200M','400M','HJ','LJ','TJ',
                     'GP','Rec_Rec','Rec_Yds','Rec_Avg','Rec_Y/G','Rec_Lng','Rec_TD',
                     'Rush_GP','Rush_Car','Rush_Yds','Rush_Avg','Rush_Y/G','Rush_Lng','100+','Rush_TD'],
            te:     ['HT','WT','WING','HAND','40','SHUT','VERT','BROAD','100M','110HH','200M','300IH','400M','SHOT','DISCUS','HJ','LJ','TJ',
                     'GP','Rec_Rec','Rec_Yds','Rec_Avg','Rec_Y/G','Rec_Lng','Rec_TD',
                     'Rush_GP','Rush_Car','Rush_Yds','Rush_Avg','Rush_Y/G','Rush_Lng','100+','Rush_TD'],
            ol:     ['HT','WT','WING','40','SHUT','VERT','BROAD','100M','SHOT','HJ','LJ'],
            safety: ['HT','WT','WING','HAND','40','SHUT','3 CONE','VERT','BROAD','100M','110HH','200M','300IH','400M','400R','SHOT','DISCUS','JAVELIN','HJ','LJ','TJ',
                     'GP','SOLO','ASST','TKLS','T/G','TFL','INT','PD'],
            cb:     ['HT','WT','WING','HAND','40','SHUT','3 CONE','VERT','BROAD','100M','110HH','200M','300IH','400M','400R','SHOT','DISCUS','JAVELIN','HJ','LJ','TJ',
                     'GP','SOLO','ASST','TKLS','T/G','TFL','INT','PD'],
            lb:     ['HT','WT','WING','HAND','40','SHUT','3 CONE','VERT','BROAD','100M','110HH','200M','300IH','400M','400R','SHOT','DISCUS','JAVELIN','HJ','LJ','TJ',
                     'GP','SOLO','ASST','TKLS','T/G','TFL','GP_2','SACKS','YDL','S/G','HURS'],
            de:     ['HT','WT','WING','HAND','40','SHUT','3 CONE','VERT','BROAD','100M','110HH','200M','300IH','400M','400R','SHOT','DISCUS','JAVELIN','HJ','LJ','TJ',
                     'GP','SOLO','ASST','TKLS','T/G','TFL','GP_2','SACKS','YDL','S/G','HURS'],
            dt:     ['HT','WT','WING','HAND','40','SHUT','3 CONE','VERT','BROAD','100M','110HH','200M','300IH','400M','400R','SHOT','DISCUS','JAVELIN','HJ','LJ','TJ',
                     'GP','SOLO','ASST','TKLS','T/G','TFL','GP_2','SACKS','YDL','S/G','HURS'],
        }};

        function axisConfig(field) {{
            const def = metricDefs[field] || {{ label: field }};
            const axis = {{ title: def.label }};
            if (def.dtick) axis.dtick = def.dtick;
            if (def.unit === 's') axis.tickformat = '.2f';
            return axis;
        }}

        function histogramBins(field, values) {{
            const def = metricDefs[field];
            if (!def || !def.binSize || !values.length) return null;
            const min = Math.min(...values);
            const max = Math.max(...values);
            if (!isFinite(min) || !isFinite(max)) return null;
            const size = def.binSize;
            return {{
                start: Math.floor(min / size) * size,
                end: Math.ceil(max / size) * size + size,
                size
            }};
        }}

        const nflColors = {{
            'Arizona Cardinals': '#97233F', 'Atlanta Falcons': '#A71930', 'Baltimore Ravens': '#241773',
            'Buffalo Bills': '#00338D', 'Carolina Panthers': '#0085CA', 'Chicago Bears': '#0B162A',
            'Cincinnati Bengals': '#FB4F14', 'Cleveland Browns': '#311D00', 'Dallas Cowboys': '#041E42',
            'Denver Broncos': '#FB4F14', 'Detroit Lions': '#0076B6', 'Green Bay Packers': '#203731',
            'Houston Texans': '#03202F', 'Indianapolis Colts': '#002C5F', 'Jacksonville Jaguars': '#006778',
            'Kansas City Chiefs': '#E31837', 'Las Vegas Raiders': '#000000', 'Los Angeles Chargers': '#0080C6',
            'Los Angeles Rams': '#003594', 'Miami Dolphins': '#008E97', 'Minnesota Vikings': '#4F2683',
            'New England Patriots': '#002244', 'New Orleans Saints': '#D3BC8D', 'New York Giants': '#012352',
            'New York Jets': '#125740', 'Philadelphia Eagles': '#004C54', 'Pittsburgh Steelers': '#FFB612',
            'San Francisco 49ers': '#AA0000', 'Seattle Seahawks': '#002244', 'Tampa Bay Buccaneers': '#D50A0A',
            'Tennessee Titans': '#0C2340', 'Washington Commanders': '#5A1414'
        }};

        const posSelect = document.getElementById('position-select');
        const xSelect = document.getElementById('x-select');
        const ySelect = document.getElementById('y-select');
        const chartType = document.getElementById('chart-type');
        const toggleRecruits = document.getElementById('toggle-recruits');
        
        Object.keys(posData).forEach(code => {{
            const opt = document.createElement('option');
            opt.value = code;
            opt.text = posData[code].name.toUpperCase();
            posSelect.appendChild(opt);
        }});
        
        // Sync currentPos with whatever the dropdown shows on load
        currentPos = posSelect.value;

        function getActiveMetrics() {{
            const allowed = positionMetrics[currentPos] || Object.keys(metricDefs);
            return allowed.filter(k => metricDefs[k]);
        }}

        function getChartMetrics() {{
            const players = posData[currentPos].players;
            if (!players.length) return [];
            return getActiveMetrics().filter(k =>
                players.some(p => p[k] != null && !isNaN(p[k]))
            );
        }}

        function updateSelectors() {{
            const active = getChartMetrics();
            xSelect.innerHTML = '';
            ySelect.innerHTML = '';
            active.forEach(m => {{
                const label = metricDefs[m].label;
                xSelect.appendChild(new Option(label, m));
                ySelect.appendChild(new Option(label, m));
            }});
            
            if (active.includes('WT')) xSelect.value = 'WT';
            if (active.includes('40')) ySelect.value = '40';
        }}

        function formatVal(v, key) {{
            if (v === null || v === undefined || isNaN(v)) return "-";
            if (key === 'HT') {{
                const ft = Math.floor(v / 12);
                const inch = Math.round(v % 12);
                return `${{ft}}'${{inch}}"`;
            }}
            const def = metricDefs[key];
            return v.toFixed(def.decimals) + (def.unit ? ' ' + def.unit : '');
        }}

        function updateTopMetrics() {{
            const drafted = posData[currentPos].players.filter(p => !p.is_recruit);
            const container = document.getElementById('top-metrics');
            container.innerHTML = '';
            
            const active = getChartMetrics();
            const core = ['HT', 'WT', '40'];
            // Add a position specific high-level metric
            const specific = active.find(m => !['HT', 'WT', '40', 'GP', '100M', 'SHUT', 'VERT', 'BROAD'].includes(m));
            const display = core.filter(m => active.includes(m));
            if (specific) display.push(specific);

            display.forEach(m => {{
                const vals = drafted.map(p => p[m]).filter(v => v !== null && !isNaN(v));
                const avg = vals.length ? vals.reduce((a,b) => a+b, 0) / vals.length : 0;
                container.innerHTML += `
                    <div class="metric-card">
                        <div class="metric-title">AVG DRAFTED ${{metricDefs[m].label}}</div>
                        <div class="metric-value">${{formatVal(avg, m)}}</div>
                    </div>
                `;
            }});
        }}

        function renderCards(data) {{
            const container = document.getElementById('player-cards-container');
            container.innerHTML = '';
            document.getElementById('player-count').innerText = `${{data.length}} PLAYERS`;
            
            if (!data.length) {{
                container.innerHTML = '<div class="empty-state">No players match these filters.</div>';
                return;
            }}

            const activePosMetrics = getActiveMetrics();

            data.forEach(p => {{
                const card = document.createElement('div');
                card.className = 'player-card';
                const tagClass = p.is_recruit ? 'tag-recruit' : 'tag-nfl';
                const tagText = p.is_recruit ? 'Recruit' : 'Drafted';
                const draftInfo = p.is_recruit ? 'HS Prospect' : (p.ROUND ? `Round ${{p.ROUND}}` : 'UDFA');

                let metricsHtml = '';
                activePosMetrics.forEach(m => {{
                    const val = p[m];
                    const display = (val != null && !isNaN(val)) ? formatVal(val, m) : '-';
                    metricsHtml += `
                        <div class="metric-item">
                            <span class="m-label">${{metricDefs[m].label}}</span>
                            <span class="m-val">${{display}}</span>
                        </div>
                    `;
                }});

                card.innerHTML = `
                    <div class="card-type-tag ${{tagClass}}">${{tagText}}</div>
                    <div class="card-header">
                        <div class="card-name">${{p.NAME}}</div>
                        <div class="card-school">${{p.SCHOOL || '-'}} • ${{draftInfo}}</div>
                    </div>
                    <div class="metrics-grid">${{metricsHtml}}</div>
                `;
                container.appendChild(card);
            }});
        }}

        let traceDataMap = {{}};

        function drawPlot() {{
            const mode = chartType.value;
            const xField = xSelect.value;
            const yField = ySelect.value;
            const isHist = mode === 'histogram';
            
            document.getElementById('y-group').style.display = isHist ? 'none' : 'flex';
            
            const all = posData[currentPos].players;
            let players = toggleRecruits.checked ? all : all.filter(p => !p.is_recruit);
            
            traceDataMap = {{}};

            if (isHist) {{
                const valid = players.filter(p => p[xField] !== null && !isNaN(p[xField]));
                const drafted = valid.filter(p => !p.is_recruit);
                const recruits = valid.filter(p => p.is_recruit);
                const draftedX = drafted.map(p => p[xField]);
                const binSpec = histogramBins(xField, draftedX);
                
                const histTrace = {{
                    x: draftedX,
                    type: 'histogram',
                    name: 'Drafted',
                    marker: {{ color: '#CBD5E0' }},
                    opacity: 0.8
                }};
                if (binSpec) histTrace.xbins = binSpec;

                const traces = [histTrace];
                
                // Compute bin counts for drafted players — needed to stack recruits on bars
                const draftBinCounts = {{}};
                if (binSpec) {{
                    draftedX.forEach(v => {{
                        const bin = Math.floor((v - binSpec.start) / binSpec.size);
                        draftBinCounts[bin] = (draftBinCounts[bin] || 0) + 1;
                    }});
                }}
                const yMaxCount = Math.max(...Object.values(draftBinCounts), 1);

                if (recruits.length) {{
                    // Assign each recruit a bin index and slot so they stack on top of their bar
                    const rBuckets = {{}};
                    recruits.forEach(p => {{
                        const bin = binSpec
                            ? Math.floor((p[xField] - binSpec.start) / binSpec.size)
                            : Math.round(p[xField]);
                        rBuckets[bin] = (rBuckets[bin] || 0) + 1;
                        p._binIndex = bin;
                        p._jitterSlot = rBuckets[bin] - 1;
                    }});
                    traces.push({{
                        x: recruits.map(p => p[xField]),
                        y: recruits.map(p => 0.5 + p._jitterSlot * 0.8),
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Recruits',
                        hoverinfo: 'none',
                        selectedpoints: null,
                        selected: {{ marker: {{ opacity: 1 }} }},
                        unselected: {{ marker: {{ opacity: 1 }} }},
                        marker: {{ color: '#2ECC71', size: 12, symbol: 'diamond' }}
                    }});
                }}

                // Compute percentiles from drafted players only
                const draftedVals = drafted.map(p => p[xField]).sort((a, b) => a - b);

                function quantile(arr, q) {{
                    if (!arr.length) return 0;
                    const pos = (arr.length - 1) * q;
                    const base = Math.floor(pos);
                    const rest = pos - base;
                    return arr[base + 1] !== undefined ? arr[base] + rest * (arr[base + 1] - arr[base]) : arr[base];
                }}

                const isSpeed = metricDefs[xField] && metricDefs[xField].unit === 's';
                const p50  = quantile(draftedVals, 0.50);
                const pBot = isSpeed ? quantile(draftedVals, 0.90) : quantile(draftedVals, 0.10);
                const pTop = isSpeed ? quantile(draftedVals, 0.10) : quantile(draftedVals, 0.90);
                const dec  = (metricDefs[xField] && metricDefs[xField].decimals !== undefined) ? metricDefs[xField].decimals : 1;

                const yaxisCfg = {{ title: 'Frequency' }};
                if (binSpec) {{
                    const maxRecruitSlot = recruits.length ? Math.max(...recruits.map(p => p._jitterSlot)) : 0;
                    const maxRecruitY = recruits.length ? 0.5 + maxRecruitSlot * 0.8 : 0;
                    const yTop = Math.ceil(Math.max(yMaxCount, maxRecruitY)) + 1;
                    const yTickVals = Array.from({{length: yTop + 1}}, (_, i) => i);
                    Object.assign(yaxisCfg, {{ range: [0, yTop], tickmode: 'array', tickvals: yTickVals }});
                }}

                const layout = {{
                    title: `DISTRIBUTION OF ${{metricDefs[xField].label.toUpperCase()}}`,
                    xaxis: axisConfig(xField),
                    yaxis: yaxisCfg,
                    barmode: 'overlay',
                    dragmode: 'select',
                    margin: {{ t: 50 }},
                    plot_bgcolor: 'white',
                    shapes: [
                        {{ type: 'line', x0: p50,  x1: p50,  y0: 0, y1: 1, yref: 'paper', line: {{ color: '#4A5568', dash: 'dash', width: 2 }} }},
                        {{ type: 'line', x0: pBot, x1: pBot, y0: 0, y1: 1, yref: 'paper', line: {{ color: '#E53E3E', width: 2.5 }} }},
                        {{ type: 'line', x0: pTop, x1: pTop, y0: 0, y1: 1, yref: 'paper', line: {{ color: '#38A169', width: 2.5 }} }}
                    ],
                    annotations: [
                        {{
                            x: p50, y: 0.97, yref: 'paper', xanchor: 'center', yanchor: 'top',
                            text: `Median<br><b>${{p50.toFixed(dec)}}</b>`,
                            showarrow: false, font: {{ color: '#4A5568', size: 11 }},
                            bgcolor: 'rgba(255,255,255,0.8)', borderpad: 3
                        }},
                        {{
                            x: pBot, y: 0.84, yref: 'paper', xanchor: 'left', yanchor: 'top',
                            text: `Bottom 10%<br><b>${{pBot.toFixed(dec)}}</b>`,
                            showarrow: false, font: {{ color: '#E53E3E', size: 11 }},
                            bgcolor: 'rgba(255,255,255,0.8)', borderpad: 3
                        }},
                        {{
                            x: pTop, y: 0.84, yref: 'paper', xanchor: 'right', yanchor: 'top',
                            text: `Top 10%<br><b>${{pTop.toFixed(dec)}}</b>`,
                            showarrow: false, font: {{ color: '#38A169', size: 11 }},
                            bgcolor: 'rgba(255,255,255,0.8)', borderpad: 3
                        }}
                    ]
                }};
                
                if (isSpeed) layout.xaxis.autorange = 'reversed';

                
                Plotly.newPlot('plot', traces, layout, {{ displaylogo: false }});
                traceDataMap[0] = drafted;
                if (recruits.length) traceDataMap[1] = recruits;

                // Hover card for recruit points on the histogram
                const plotDivHist = document.getElementById('plot');
                const tooltip = document.getElementById('hover-tooltip');
                plotDivHist.on('plotly_hover', function(eventData) {{
                    const pt = eventData.points[0];
                    if (pt.curveNumber !== 1) {{ tooltip.style.display = 'none'; return; }}
                    const recruit = traceDataMap[1] && traceDataMap[1][pt.pointIndex];
                    if (!recruit) return;
                    const def = metricDefs[xField] || {{ label: xField }};
                    document.getElementById('ht-name').textContent = recruit.NAME;
                    document.getElementById('ht-school').textContent = recruit.SCHOOL || '-';
                    document.getElementById('ht-label').textContent = def.label;
                    document.getElementById('ht-val').textContent = formatVal(recruit[xField], xField);
                    const ev = eventData.event;
                    const tx = ev.clientX + 18;
                    const ty = Math.max(10, ev.clientY - 90);
                    tooltip.style.left = tx + 'px';
                    tooltip.style.top  = ty + 'px';
                    tooltip.style.display = 'block';
                }});
                plotDivHist.on('plotly_unhover', function() {{
                    tooltip.style.display = 'none';
                }});

                // Show ALL players for the position by default in the list
                renderCards(all);
            }} else {{
                const valid = players.filter(p => 
                    p[xField] !== null && !isNaN(p[xField]) && 
                    p[yField] !== null && !isNaN(p[yField])
                );
                
                const trace = {{
                    x: valid.map(p => p[xField]),
                    y: valid.map(p => p[yField]),
                    text: valid.map(p => p.NAME),
                    mode: 'markers',
                    type: 'scatter',
                    marker: {{
                        size: valid.map(p => {{
                            if (p.is_recruit) return 14;
                            const pick = p['PICK #'];
                            if (!pick || isNaN(pick)) return 8;   // UDFA
                            // Linear scale: pick 1 = 28px, pick 252 = 8px
                            return Math.max(8, Math.round(28 - (pick - 1) * (20 / 251)));
                        }}),
                        color: valid.map(p => p.is_recruit ? '#2ECC71' : (nflColors[p.TEAM] || '#BF5700')),
                        line: {{ width: 1, color: 'white' }}
                    }},
                    selected: {{ marker: {{ opacity: 1 }} }},
                    unselected: {{ marker: {{ opacity: 0.2 }} }}
                }};

                const layout = {{
                    title: `${{metricDefs[yField].label.toUpperCase()}} VS ${{metricDefs[xField].label.toUpperCase()}}`,
                    xaxis: axisConfig(xField),
                    yaxis: axisConfig(yField),
                    dragmode: 'select',
                    margin: {{ t: 60 }},
                    hovermode: 'closest',
                    plot_bgcolor: 'white'
                }};

                if (metricDefs[xField] && metricDefs[xField].unit === 's') {{
                    layout.xaxis.autorange = 'reversed';
                }}
                if (metricDefs[yField] && metricDefs[yField].unit === 's') {{
                    layout.yaxis.autorange = 'reversed';
                }}

                Plotly.newPlot('plot', [trace], layout, {{ displaylogo: false }});
                traceDataMap[0] = valid;
                
                // Show ALL players for the position by default in the list
                renderCards(all);
            }}

            const plotDiv = document.getElementById('plot');

            // Track current selection ranges for redraw
            let histSelections = [];
            let histBinSpec = null;

            function getHistBinSpec() {{
                if (histBinSpec) return histBinSpec;
                const rendered = plotDiv._fullData && plotDiv._fullData[0];
                const xbins = rendered && rendered.xbins;
                if (!xbins || !xbins.size) return null;
                histBinSpec = {{
                    start: Number(xbins.start),
                    end: Number(xbins.end),
                    size: Number(xbins.size)
                }};
                return histBinSpec;
            }}

            function redrawHistWithSelection() {{
                const xField = xSelect.value;
                const all = posData[currentPos].players;
                let players = toggleRecruits.checked ? all : all.filter(p => !p.is_recruit);
                const valid = players.filter(p => p[xField] !== null && !isNaN(p[xField]));
                const drafted = valid.filter(p => !p.is_recruit);
                const recruits = valid.filter(p => p.is_recruit);
                const binSpec = getHistBinSpec();

                if (!binSpec) return;

                const binCount = Math.max(1, Math.ceil((binSpec.end - binSpec.start) / binSpec.size));
                const counts = Array(binCount).fill(0);
                drafted.forEach(p => {{
                    const value = p[xField];
                    let binIndex = Math.floor((value - binSpec.start) / binSpec.size);
                    if (value === binSpec.end) binIndex = binCount - 1;
                    if (binIndex >= 0 && binIndex < binCount) counts[binIndex] += 1;
                }});

                const centers = counts.map((_, i) => binSpec.start + (i + 0.5) * binSpec.size);
                const barColors = counts.map((_, i) => {{
                    const xMin = binSpec.start + i * binSpec.size;
                    const xMax = xMin + binSpec.size;
                    return histSelections.some(selection => xMin < selection.xMax && xMax > selection.xMin)
                        ? '#BF5700' : '#E2E8F0';
                }});
                const barBorders = barColors.map(color => color === '#BF5700' ? '#9E4800' : '#CBD5E0');

                const traces = [{{
                    x: centers,
                    y: counts,
                    width: binSpec.size,
                    type: 'bar',
                    name: 'Drafted',
                    marker: {{
                        color: barColors,
                        line: {{ color: barBorders, width: 1.5 }}
                    }},
                    opacity: 0.9
                }}];

                if (recruits.length) {{
                    // Reuse _binIndex/_jitterSlot from initial draw; stack on bars using current counts
                    traces.push({{
                        x: recruits.map(p => p[xField]),
                        y: recruits.map(p => 0.5 + (p._jitterSlot || 0) * 0.8),
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Recruits',
                        hoverinfo: 'none',
                        selectedpoints: null,
                        selected: {{ marker: {{ opacity: 1 }} }},
                        unselected: {{ marker: {{ opacity: 1 }} }},
                        marker: {{ color: '#2ECC71', size: 12, symbol: 'diamond' }}
                    }});
                }}

                const yMax2 = Math.max(...counts, 1);
                const maxRecruitSlot2 = recruits.length ? Math.max(...recruits.map(p => p._jitterSlot || 0)) : 0;
                const maxRecruitY2 = recruits.length ? 0.5 + maxRecruitSlot2 * 0.8 : 0;
                const yTop2 = Math.ceil(Math.max(yMax2, maxRecruitY2)) + 1;
                const yTickVals2 = Array.from({{length: yTop2 + 1}}, (_, i) => i);
                const nextLayout = {{
                    ...plotDiv.layout,
                    xaxis: {{ ...plotDiv.layout.xaxis }},
                    yaxis: {{ ...plotDiv.layout.yaxis, range: [0, yTop2], tickmode: 'array', tickvals: yTickVals2, autorange: false }}
                }};
                if (plotDiv._fullLayout && plotDiv._fullLayout.xaxis && plotDiv._fullLayout.xaxis.range) {{
                    nextLayout.xaxis.range = [...plotDiv._fullLayout.xaxis.range];
                    nextLayout.xaxis.autorange = false;
                }}

                Plotly.react('plot', traces, nextLayout, {{ displaylogo: false }});
            }}

            function normalizeHistRange(xMin, xMax) {{
                const lo = Math.min(xMin, xMax);
                const hi = Math.max(xMin, xMax);
                return {{ xMin: lo, xMax: hi }};
            }}

            function rangesMatch(a, b) {{
                const tolerance = 1e-9;
                return Math.abs(a.xMin - b.xMin) < tolerance && Math.abs(a.xMax - b.xMax) < tolerance;
            }}

            function updateHistFilter() {{
                const xField = xSelect.value;
                const all = posData[currentPos].players;
                const showRec = toggleRecruits.checked;
                const activePlayers = showRec ? all : all.filter(p => !p.is_recruit);
                if (!histSelections.length) {{
                    renderCards(all);
                    document.getElementById('clear-selection').style.display = 'none';
                    redrawHistWithSelection();
                    return;
                }}
                const filtered = activePlayers.filter(p => {{
                    const v = p[xField];
                    return v !== null && !isNaN(v) && histSelections.some(selection => v >= selection.xMin && v <= selection.xMax);
                }});
                renderCards(filtered);
                document.getElementById('clear-selection').style.display = histSelections.length ? 'block' : 'none';
                redrawHistWithSelection();
            }}

            function setHistFilter(xMin, xMax) {{
                histSelections = [normalizeHistRange(xMin, xMax)];
                updateHistFilter();
            }}

            function toggleHistFilter(xMin, xMax) {{
                const nextRange = normalizeHistRange(xMin, xMax);
                const existingIndex = histSelections.findIndex(selection => rangesMatch(selection, nextRange));
                if (existingIndex >= 0) {{
                    histSelections.splice(existingIndex, 1);
                }} else {{
                    histSelections.push(nextRange);
                }}
                updateHistFilter();
            }}

            // Click a single bar to filter
            plotDiv.on('plotly_click', function(eventData) {{
                if (chartType.value !== 'histogram') return;
                if (!eventData || !eventData.points.length) return;
                const pt = eventData.points[0];
                // Use the rendered bin edges for player filtering
                const binSpec = getHistBinSpec();
                const size = binSpec && binSpec.size;
                let xMin, xMax;
                if (size) {{
                    const binIndex = pt.data.type === 'bar'
                        ? pt.pointNumber
                        : Math.floor((pt.x - binSpec.start) / size);
                    xMin = binSpec.start + binIndex * size;
                    xMax = xMin + size;
                }} else {{
                    xMin = pt.x - 0.5;
                    xMax = pt.x + 0.5;
                }}
                toggleHistFilter(xMin, xMax);
            }});

            // Drag-select a range on the histogram
            plotDiv.on('plotly_selected', function(eventData) {{
                if (!eventData) return;
                
                const mode = chartType.value;
                const xField = xSelect.value;
                const all = posData[currentPos].players;
                const showRec = toggleRecruits.checked;
                const activePlayers = showRec ? all : all.filter(p => !p.is_recruit);
                
                if (mode === 'histogram') {{
                    const range = eventData.range;
                    if (!range || !range.x) return;
                    const [xMin, xMax] = range.x;
                    setHistFilter(xMin, xMax);
                }} else {{
                    // Scatter: filter by selected point indices
                    const filtered = [];
                    eventData.points.forEach(pt => {{
                        if (traceDataMap[pt.curveNumber]) {{
                            filtered.push(traceDataMap[pt.curveNumber][pt.pointIndex]);
                        }}
                    }});
                    renderCards(filtered);
                }}
                document.getElementById('clear-selection').style.display = 'block';
            }});
        }}

        function init() {{
            updateSelectors();
            updateTopMetrics();
            drawPlot();
        }}

        posSelect.onchange = () => {{
            currentPos = posSelect.value;
            init();
        }};
        
        xSelect.onchange = drawPlot;
        ySelect.onchange = drawPlot;
        chartType.onchange = drawPlot;
        toggleRecruits.onchange = drawPlot;
        
        document.getElementById('clear-selection').onclick = () => {{
            Plotly.restyle('plot', 'selectedpoints', null);
            document.getElementById('clear-selection').style.display = 'none';
            drawPlot();
        }};

        init();
    </script>
</body>
</html>
"""
    with open(os.path.join(base_path, 'index.html'), 'w') as f:
        f.write(html_template)

if __name__ == '__main__':
    build_html()
