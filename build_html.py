import pandas as pd
import json
import os
import math

POSITIONS = {
    'qb': {'name': 'Quarterback', 'recruit_match': ['QB']},
    'rb': {'name': 'Running Back', 'recruit_match': ['RB']},
    'wr': {'name': 'Wide Receiver', 'recruit_match': ['WR']},
    'te': {'name': 'Tight End', 'recruit_match': ['TE']},
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
    base_path = os.path.dirname(__file__)
    ucreport_path = os.path.join(base_path, 'ucreport_data.csv')
    maxpreps_path = os.path.join(base_path, 'maxpreps_data.csv')
    
    # Load recruit data once
    all_recruits = pd.DataFrame()
    if os.path.exists(ucreport_path) and os.path.exists(maxpreps_path):
        uc_df = pd.read_csv(ucreport_path)
        mp_df = pd.read_csv(maxpreps_path)
        recruit_df = pd.merge(uc_df, mp_df, on='player_id', how='left')
        
        recruit_df['NAME'] = recruit_df['first'].astype(str).str.strip() + ' ' + recruit_df['last'].astype(str).str.strip()
        recruit_df['SCHOOL'] = recruit_df['effective_school_name']
        recruit_df['TEAM'] = "High School Recruit"
        recruit_df['HT'] = recruit_df['height']
        recruit_df['WT'] = recruit_df['weight']
        recruit_df['40'] = recruit_df['forty']
        recruit_df['100M'] = recruit_df['track100m']
        recruit_df['VERT'] = recruit_df['vertical']
        recruit_df['BROAD'] = recruit_df['broad']
        recruit_df['SHUT'] = recruit_df['shuttle']
        recruit_df['SHOT'] = recruit_df['trackSP']
        recruit_df['LJ'] = recruit_df['trackLJ']
        recruit_df['GP'] = recruit_df['maxpreps_gp']
        recruit_df['SOLO'] = recruit_df['maxpreps_solo']
        recruit_df['ASST'] = recruit_df['maxpreps_asst']
        recruit_df['TKLS'] = recruit_df['maxpreps_total_tackles']
        recruit_df['T/G'] = recruit_df['maxpreps_t_g']
        recruit_df['TFL'] = recruit_df['maxpreps_tfl']
        recruit_df['INT'] = recruit_df['maxpreps_ints']
        recruit_df['PD'] = recruit_df['maxpreps_pd']
        recruit_df['ROUND'] = None
        recruit_df['is_recruit'] = True
        all_recruits = recruit_df

    position_data = {}
    
    for pos_code, pos_info in POSITIONS.items():
        combine_path = os.path.join(base_path, f'{pos_code}_combine.csv')
        stats_path = os.path.join(base_path, f'{pos_code}_stats.csv')
        
        combine_df = load_csv(combine_path)
        stats_df = load_csv(stats_path)
        
        if combine_df.empty:
            continue
            
        # Clean up average/summary rows
        combine_df = combine_df[~combine_df['YEAR'].astype(str).str.contains('AVERAGE|Avg', case=False, na=False)]
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
                # Second set is Receiving
                rename_map = {
                    'GP_2': 'Rec_GP', 'Rec': 'Rec_Rec', 'Yds_2': 'Rec_Yds',
                    'Avg_2': 'Rec_Avg', 'Y/G_2': 'Rec_Y/G', 'Lng_2': 'Rec_Lng',
                    'TD_2': 'Rec_TD'
                }
                stats_df = stats_df.rename(columns=rename_map)
            elif pos_code in ['wr', 'te']:
                # GP,Rec,Yds,Avg,Y/G,Lng,TD,GP,Car,Yds,Avg,Y/G,Lng,100+,TD
                # Second set is Rushing
                rename_map = {
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
        
        if pos_code == 'safety' and not all_recruits.empty:
            pos_recruits = all_recruits[
                all_recruits['position_projected'].isin(pos_info['recruit_match']) | 
                all_recruits['position_played'].isin(pos_info['recruit_match']) |
                all_recruits['position_projected'].isin(['ATH']) |
                all_recruits['position_played'].isin(['ATH'])
            ].copy()
            if not pos_recruits.empty:
                df = pd.concat([df, pos_recruits], ignore_index=True)

        num_cols = df.columns.difference(['NAME', 'SCHOOL', 'TEAM', 'is_recruit', 'YEAR', 'PLAYER', 'PICK', 'PICK #', 'maxpreps_url', 'college_level_projection', 'uc_score', 'last', 'first', 'effective_school_name', 'college_enrolled', 'school_city', 'state', 'county', 'position_played', 'position_projected', 'height', 'weight', 'wingspan', 'forty', 'shuttle', 'vertical', 'track60m', 'track100m', 'track200m', 'broad', 'trackLJ', 'highJump', 'trackSP', 'discus', 'updated', 'head_coach', 'player_head_shot', 'camp_event_videos', 'hudl_video_link', 'college_offers', 'commit', 'max_speed_video', 'query_name', 'player_id', 'class_field'])
        
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
    </style>
</head>
<body>

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
            'HT': {{ label: 'Height', unit: 'in', decimals: 1 }},
            'WT': {{ label: 'Weight', unit: 'lbs', decimals: 0 }},
            '40': {{ label: '40-Yard', unit: 's', decimals: 2 }},
            '100M': {{ label: '100M', unit: 's', decimals: 2 }},
            'VERT': {{ label: 'Vertical', unit: 'in', decimals: 1 }},
            'BROAD': {{ label: 'Broad', unit: 'in', decimals: 0 }},
            'SHUT': {{ label: 'Shuttle', unit: 's', decimals: 2 }},
            // Defensive
            'GP': {{ label: 'Games', unit: '', decimals: 0 }},
            'SOLO': {{ label: 'Solo Tkl', unit: '', decimals: 0 }},
            'TKLS': {{ label: 'Total Tkl', unit: '', decimals: 0 }},
            'TFL': {{ label: 'TFL', unit: '', decimals: 1 }},
            'INT': {{ label: 'INT', unit: '', decimals: 0 }},
            'PD': {{ label: 'Pass Def', unit: '', decimals: 0 }},
            'T/G': {{ label: 'Tkl/G', unit: '', decimals: 1 }},
            'SACKS': {{ label: 'Sacks', unit: '', decimals: 1 }},
            'HURS': {{ label: 'Hurries', unit: '', decimals: 0 }},
            // Passing
            'C': {{ label: 'Completions', unit: '', decimals: 0 }},
            'Att': {{ label: 'Attempts', unit: '', decimals: 0 }},
            'Yds': {{ label: 'Pass Yds', unit: '', decimals: 0 }},
            'C%': {{ label: 'Comp %', unit: '', decimals: 1 }},
            'TD': {{ label: 'Pass TD', unit: '', decimals: 0 }},
            'Int': {{ label: 'Pass INT', unit: '', decimals: 0 }},
            'QBR': {{ label: 'QBR', unit: '', decimals: 1 }},
            // Rushing (Common / Pos Specific)
            'Car': {{ label: 'Carries', unit: '', decimals: 0 }},
            'Rush_Car': {{ label: 'Rush Carries', unit: '', decimals: 0 }},
            'Rush_Yds': {{ label: 'Rush Yds', unit: '', decimals: 0 }},
            'Rush_TD': {{ label: 'Rush TD', unit: '', decimals: 0 }},
            // Receiving
            'Rec': {{ label: 'Rec', unit: '', decimals: 0 }},
            'Rec_Rec': {{ label: 'Rec', unit: '', decimals: 0 }},
            'Rec_Yds': {{ label: 'Rec Yds', unit: '', decimals: 0 }},
            'Rec_TD': {{ label: 'Rec TD', unit: '', decimals: 0 }},
            'Avg': {{ label: 'Avg', unit: '', decimals: 1 }}
        }};

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
            const players = posData[currentPos].players;
            const metrics = [];
            if (!players.length) return [];
            
            // Check which metrics actually have data for this position
            Object.keys(metricDefs).forEach(k => {{
                const hasData = players.some(p => p[k] !== null && !isNaN(p[k]));
                if (hasData) metrics.push(k);
            }});
            return metrics;
        }}

        function updateSelectors() {{
            const active = getActiveMetrics();
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
            
            const active = getActiveMetrics();
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

                // Only show metrics that this specific position (and player if possible) has
                let metricsHtml = '';
                activePosMetrics.slice(0, 15).forEach(m => {{
                    const val = p[m];
                    if (val !== null && !isNaN(val)) {{
                        metricsHtml += `
                            <div class="metric-item">
                                <span class="m-label">${{metricDefs[m].label}}</span>
                                <span class="m-val">${{formatVal(val, m)}}</span>
                            </div>
                        `;
                    }}
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
                
                const traces = [{{
                    x: drafted.map(p => p[xField]),
                    type: 'histogram',
                    name: 'Drafted',
                    marker: {{ color: '#CBD5E0' }},
                    opacity: 0.8
                }}];
                
                if (recruits.length) {{
                    traces.push({{
                        x: recruits.map(p => p[xField]),
                        y: recruits.map(() => 0),
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Recruits',
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

                const layout = {{
                    title: `DISTRIBUTION OF ${{metricDefs[xField].label.toUpperCase()}}`,
                    xaxis: {{ title: metricDefs[xField].label }},
                    yaxis: {{ title: 'Frequency' }},
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
                    xaxis: {{ title: metricDefs[xField].label }},
                    yaxis: {{ title: metricDefs[yField].label }},
                    dragmode: 'select',
                    margin: {{ t: 60 }},
                    hovermode: 'closest',
                    plot_bgcolor: 'white'
                }};

                Plotly.newPlot('plot', [trace], layout, {{ displaylogo: false }});
                traceDataMap[0] = valid;
                
                // Show ALL players for the position by default in the list
                renderCards(all);
            }}

            const plotDiv = document.getElementById('plot');
            plotDiv.on('plotly_selected', function(eventData) {{
                if (!eventData) return;
                
                const mode = chartType.value;
                const xField = xSelect.value;
                const all = posData[currentPos].players;
                const showRec = toggleRecruits.checked;
                const activePlayers = showRec ? all : all.filter(p => !p.is_recruit);
                
                if (mode === 'histogram') {{
                    // For histograms, filter by the dragged x-range, ignoring y.
                    // This means touching any part of a bar selects ALL players in that range.
                    const range = eventData.range;
                    if (!range || !range.x) return;
                    const [xMin, xMax] = range.x;
                    const filtered = activePlayers.filter(p => {{
                        const v = p[xField];
                        return v !== null && !isNaN(v) && v >= xMin && v <= xMax;
                    }});
                    renderCards(filtered);
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
