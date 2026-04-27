import pandas as pd
import json
import os
import math

def build_html():
    base_path = os.path.dirname(__file__)
    combine_path = os.path.join(base_path, 'safety_combine.csv')
    stats_path = os.path.join(base_path, 'safety_stats.csv')
    ucreport_path = os.path.join(base_path, 'ucreport_data.csv')
    maxpreps_path = os.path.join(base_path, 'maxpreps_data.csv')
    
    # Load data
    combine_df = pd.read_csv(combine_path, skiprows=1)
    stats_df = pd.read_csv(stats_path, skiprows=1)
    
    # Clean up column names and rows (drop average rows)
    combine_df = combine_df[~combine_df['YEAR'].astype(str).str.contains('AVERAGE', na=False)]
    stats_df = stats_df[~stats_df['YEAR'].astype(str).str.contains('AVERAGE', na=False)]
    
    combine_df['NAME'] = combine_df['NAME'].astype(str).str.strip()
    stats_df['NAME'] = stats_df['NAME'].astype(str).str.strip()
    
    drafted_df = pd.merge(combine_df, stats_df[['NAME', 'GP', 'SOLO', 'ASST', 'TKLS', 'T/G', 'TFL', 'INT', 'PD']], on='NAME', how='left')
    drafted_df['is_recruit'] = False
    
    # Load recruit data
    if os.path.exists(ucreport_path) and os.path.exists(maxpreps_path):
        uc_df = pd.read_csv(ucreport_path)
        mp_df = pd.read_csv(maxpreps_path)
        recruit_df = pd.merge(uc_df, mp_df, on='player_id', how='left')
        
        # Map recruit columns to match drafted columns
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
        
        # Combine them
        df = pd.concat([drafted_df, recruit_df], ignore_index=True)
    else:
        df = drafted_df
        
    # Convert numerical columns
    num_cols = ['ROUND', 'HT', 'WT', '40', '100M', 'VERT', 'BROAD', 'SHUT', 'SHOT', 'LJ', 'TKLS', 'INT', 'TFL', 'PD', 'T/G', 'GP', 'SOLO', 'ASST']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    records = df[['NAME', 'SCHOOL', 'TEAM', 'is_recruit'] + num_cols].to_dict(orient='records')
    
    for row in records:
        for k, v in row.items():
            if isinstance(v, float) and math.isnan(v):
                row[k] = None
                
    json_data = json.dumps(records)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drafted Safeties Benchmark</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --primary: #BF5700;
            --bg-color: #F4F7F6;
            --card-bg: #FFFFFF;
            --text-dark: #2C3E50;
            --text-light: #7F8C8D;
            --border: #E2E8F0;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-dark);
            padding-bottom: 50px;
        }}
        
        /* Navbar */
        .navbar {{
            background-color: var(--card-bg);
            padding: 20px 50px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }}
        .navbar h1 {{
            color: var(--primary);
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 50px;
        }}
        
        /* Metrics */
        .metrics-container {{
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            flex: 1;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }}
        .metric-title {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-light);
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: 700;
            color: var(--text-dark);
        }}
        
        /* Dashboard Layout */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .panel {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }}
        
        .controls-row {{
            display: flex;
            gap: 20px;
            align-items: flex-end;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }}
        
        .control-group {{
            display: flex;
            flex-direction: column;
        }}
        .control-group label {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 8px;
        }}
        select {{
            padding: 10px 15px;
            font-size: 15px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background-color: var(--bg-color);
            color: var(--text-dark);
            width: 250px;
            outline: none;
            transition: border-color 0.2s;
        }}
        select:focus {{
            border-color: var(--primary);
        }}
        
        .hint-text {{
            font-size: 16px;
            font-weight: 500;
            color: #4A5568;
            margin-left: auto;
            display: flex;
            align-items: center;
            background-color: #EDF2F7;
            padding: 10px 15px;
            border-radius: 8px;
            border-left: 4px solid var(--primary);
        }}
        
        #plot {{
            width: 100%;
            height: 500px;
        }}
        
        /* Cards Grid */
        .cards-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .cards-header h3 {{
            font-size: 18px;
            color: var(--text-dark);
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .player-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            flex-direction: column;
        }}
        .player-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.05);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }}
        .card-name {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 4px;
        }}
        .card-school {{
            font-size: 13px;
            color: var(--text-light);
        }}
        .round-badge {{
            background-color: #F8F9FA;
            color: var(--primary);
            border: 1px solid var(--primary);
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px 10px;
        }}
        .metric-item {{
            display: flex;
            flex-direction: column;
        }}
        .m-label {{
            font-size: 10px;
            text-transform: uppercase;
            color: var(--text-light);
            margin-bottom: 2px;
            font-weight: 600;
        }}
        .m-val {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-dark);
        }}
        .empty-state {{
            padding: 40px;
            text-align: center;
            color: var(--text-light);
            grid-column: 1 / -1;
        }}
    </style>
</head>
<body>

    <div class="navbar">
        <h1>Safety Recruiting Dashboard</h1>
    </div>
    
    <div class="container">
        <!-- Top Metrics -->
        <div class="metrics-container">
            <div class="metric-card">
                <div class="metric-title">Avg HS Height</div>
                <div class="metric-value" id="m-height">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Avg HS Weight</div>
                <div class="metric-value" id="m-weight">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Avg HS 40-Yard</div>
                <div class="metric-value" id="m-forty">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Avg HS Tackles (Sr)</div>
                <div class="metric-value" id="m-tkls">-</div>
            </div>
        </div>
        
        <!-- Plot Panel -->
        <div class="panel">
            <div class="controls-row" style="flex-wrap: wrap;">
                <div style="display: flex; gap: 20px; width: 100%; align-items: flex-end;">
                    <div class="control-group">
                        <label>Chart Type</label>
                        <select id="chart-type" style="width: 150px; font-weight: 600; color: var(--primary);">
                            <option value="scatter">Scatter Plot</option>
                            <option value="histogram">Histogram</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label id="x-label" for="x-select">X-Axis Metric</label>
                        <select id="x-select"></select>
                    </div>
                    <div class="control-group" id="y-group">
                        <label for="y-select">Y-Axis Metric</label>
                        <select id="y-select"></select>
                    </div>
                    <div class="control-group" style="justify-content: flex-end; padding-bottom: 8px; margin-left: 10px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; margin: 0; color: var(--text-dark);">
                            <input type="checkbox" id="toggle-recruits" checked style="width: 18px; height: 18px; accent-color: var(--primary);">
                            Show High School Recruits
                        </label>
                    </div>
                    <div class="control-group" style="justify-content: flex-end; padding-bottom: 8px; margin-left: auto;">
                        <button id="clear-selection" class="btn-clear">Clear Selection</button>
                    </div>
                </div>
                <div class="hint-text" style="width: 100%; margin-top: 15px;">
                    <i id="dynamic-hint">Choose "Histogram" to view the distribution of a single metric. Click or drag on the plot to select players.</i>
                </div>
            </div>
            <div id="plot"></div>
        </div>
        
        <!-- Cards Panel -->
        <div class="panel">
            <div class="cards-header">
                <h3>Player Database</h3>
                <span id="player-count" style="color: var(--text-light); font-size: 14px;"></span>
            </div>
            <div id="player-cards-container" class="cards-grid">
                <!-- Populated by JS -->
            </div>
        </div>
    </div>

    <script>
        const players = {json_data};
        
        const metricConfig = {{
            'HT': {{ label: 'Height (inches)', decimals: 1, type: 'size' }},
            'WT': {{ label: 'Weight (lbs)', decimals: 0, type: 'size' }},
            '40': {{ label: '40-Yard Dash (s)', decimals: 2, type: 'speed' }},
            '100M': {{ label: '100M Dash (s)', decimals: 2, type: 'speed' }},
            'VERT': {{ label: 'Vertical Jump (in)', decimals: 1, type: 'size' }},
            'BROAD': {{ label: 'Broad Jump (in)', decimals: 0, type: 'size' }},
            'SHUT': {{ label: 'Short Shuttle (s)', decimals: 2, type: 'speed' }},
            'LJ': {{ label: 'Long Jump (ft/in)', decimals: 2, type: 'size' }},
            'SHOT': {{ label: 'Shot Put', decimals: 1, type: 'size' }},
            'GP': {{ label: 'Games Played', decimals: 0, type: 'size' }},
            'SOLO': {{ label: 'Solo Tackles', decimals: 0, type: 'size' }},
            'ASST': {{ label: 'Assisted Tackles', decimals: 0, type: 'size' }},
            'TKLS': {{ label: 'Tackles', decimals: 0, type: 'size' }},
            'T/G': {{ label: 'Tackles Per Game', decimals: 1, type: 'size' }},
            'TFL': {{ label: 'Tackles For Loss', decimals: 0, type: 'size' }},
            'INT': {{ label: 'Interceptions', decimals: 0, type: 'size' }},
            'PD': {{ label: 'Pass Deflections', decimals: 0, type: 'size' }}
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
        
        // Populate Dropdowns
        const chartTypeSelect = document.getElementById('chart-type');
        const xSelect = document.getElementById('x-select');
        const ySelect = document.getElementById('y-select');
        const yGroup = document.getElementById('y-group');
        const xLabel = document.getElementById('x-label');
        const dynamicHint = document.getElementById('dynamic-hint');
        
        for (const [key, val] of Object.entries(metricConfig)) {{
            const opt1 = document.createElement('option');
            opt1.value = key;
            opt1.text = val.label;
            xSelect.appendChild(opt1);
            
            const opt2 = document.createElement('option');
            opt2.value = key;
            opt2.text = val.label;
            ySelect.appendChild(opt2);
        }}
        
        // Set Defaults
        xSelect.value = 'WT';
        ySelect.value = '40';
        
        // Formatter helpers
        function formatHeight(h) {{
            if (!h) return "-";
            const ft = Math.floor(h / 12);
            const inch = Math.round(h % 12);
            return `${{ft}}'${{inch}}"`;
        }}
        
        function formatNum(n, decimals) {{
            return n !== null && n !== undefined ? n.toFixed(decimals) : "-";
        }}
        
        // Calculate Top Metrics
        function calcMean(field) {{
            const vals = players.map(p => p[field]).filter(v => v !== null && !isNaN(v));
            if (vals.length === 0) return 0;
            return vals.reduce((a, b) => a + b, 0) / vals.length;
        }}
        
        document.getElementById('m-height').innerText = formatHeight(calcMean('HT'));
        document.getElementById('m-weight').innerText = calcMean('WT').toFixed(0) + ' lbs';
        document.getElementById('m-forty').innerText = calcMean('40').toFixed(2) + ' s';
        document.getElementById('m-tkls').innerText = calcMean('TKLS').toFixed(0);
        
        // Cards Rendering
        function renderCards(data) {{
            const container = document.getElementById('player-cards-container');
            container.innerHTML = '';
            document.getElementById('player-count').innerText = `${{data.length}} players found`;
            
            if (data.length === 0) {{
                container.innerHTML = `<div class="empty-state">No players found in this range. Try clearing your selection.</div>`;
                return;
            }}
            
            data.forEach(p => {{
                const card = document.createElement('div');
                card.className = 'player-card';
                
                const roundText = p.ROUND ? `Round ${{p.ROUND}}` : 'UDFA';
                
                card.innerHTML = `
                    <div class="card-header">
                        <div>
                            <div class="card-name">${{p.NAME}}</div>
                            <div class="card-school">${{p.SCHOOL || '-'}}</div>
                        </div>
                        <div class="round-badge">${{roundText}}</div>
                    </div>
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <span class="m-label">Height</span>
                            <span class="m-val">${{formatHeight(p.HT)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Weight</span>
                            <span class="m-val">${{formatNum(p.WT, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">40-Yard</span>
                            <span class="m-val">${{formatNum(p['40'], 2)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">100M</span>
                            <span class="m-val">${{formatNum(p['100M'], 2)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Vertical</span>
                            <span class="m-val">${{formatNum(p.VERT, 1)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Broad</span>
                            <span class="m-val">${{formatNum(p.BROAD, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Shuttle</span>
                            <span class="m-val">${{formatNum(p.SHUT, 2)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Long Jump</span>
                            <span class="m-val">${{formatNum(p.LJ, 2)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Shot Put</span>
                            <span class="m-val">${{formatNum(p.SHOT, 1)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">GP</span>
                            <span class="m-val">${{formatNum(p.GP, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Solo Tkl</span>
                            <span class="m-val">${{formatNum(p.SOLO, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Asst Tkl</span>
                            <span class="m-val">${{formatNum(p.ASST, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Tackles</span>
                            <span class="m-val">${{formatNum(p.TKLS, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Tkls/G</span>
                            <span class="m-val">${{formatNum(p['T/G'], 1)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">TFL</span>
                            <span class="m-val">${{formatNum(p.TFL, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">INTs</span>
                            <span class="m-val">${{formatNum(p.INT, 0)}}</span>
                        </div>
                        <div class="metric-item">
                            <span class="m-label">Pass Def</span>
                            <span class="m-val">${{formatNum(p.PD, 0)}}</span>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            }});
        }}
        
        let currentValidData = [];
        let traceDataMap = {};
        let selectedIndicesByTrace = {};
        
        function clearSelection() {
            Object.keys(selectedIndicesByTrace).forEach(k => selectedIndicesByTrace[k].clear());
            const plotDiv = document.getElementById('plot');
            if (plotDiv && plotDiv.data) {
                Plotly.restyle('plot', 'selectedpoints', null);
            }
            document.getElementById('clear-selection').style.display = 'none';
            renderCards(currentValidData);
        }
        
        function applySelectionToPlot() {
            let hasSelection = false;
            Object.keys(selectedIndicesByTrace).forEach(k => {
                if (selectedIndicesByTrace[k].size > 0) hasSelection = true;
            });
            
            if (!hasSelection) {
                clearSelection();
                return;
            }
            
            const plotDiv = document.getElementById('plot');
            if (!plotDiv || !plotDiv.data) return;
            
            let selectedArr = [];
            for(let i=0; i<plotDiv.data.length; i++) {
                if (selectedIndicesByTrace[i] && selectedIndicesByTrace[i].size > 0) {
                    selectedArr.push(Array.from(selectedIndicesByTrace[i]));
                } else {
                    selectedArr.push([]);
                }
            }
            
            Plotly.restyle('plot', {'selectedpoints': selectedArr});
            
            let filtered = [];
            Object.keys(selectedIndicesByTrace).forEach(traceIdx => {
                if (selectedIndicesByTrace[traceIdx].size > 0 && traceDataMap[traceIdx]) {
                    selectedIndicesByTrace[traceIdx].forEach(idx => {
                        if (traceDataMap[traceIdx][idx]) {
                            filtered.push(traceDataMap[traceIdx][idx]);
                        }
                    });
                }
            });
            
            document.getElementById('clear-selection').style.display = 'block';
            renderCards(filtered);
        }
        
        function drawPlot() {{
            const chartType = chartTypeSelect.value;
            const isHistogram = (chartType === 'histogram');
            
            if (isHistogram) {{
                yGroup.style.display = 'none';
                xLabel.innerText = 'Metric';
                dynamicHint.innerText = 'Click or drag on the bars to select players. Hold Shift to select multiple bars. Double-click the background to clear.';
            }} else {{
                yGroup.style.display = 'flex';
                xLabel.innerText = 'X-Axis Metric';
                dynamicHint.innerText = 'Click or drag on the plot to select players. Larger dots indicate earlier draft rounds. Double-click the background to clear.';
            }}
            
            const xField = xSelect.value;
            const yField = isHistogram ? xField : ySelect.value;
            
            const showRecruits = document.getElementById('toggle-recruits').checked;
            let activePlayers = players;
            if (!showRecruits) {
                activePlayers = players.filter(p => !p.is_recruit);
            }
            
            // Clear prior state
            traceDataMap = {};
            selectedIndicesByTrace = {};
            
            if (isHistogram) {
                // HISTOGRAM MODE
                currentValidData = activePlayers.filter(p => p[xField] !== null && !isNaN(p[xField]));
                
                // Separate drafted vs recruits
                const draftedPlayers = currentValidData.filter(p => !p.is_recruit);
                const recruitPlayers = currentValidData.filter(p => p.is_recruit);
                
                const vals = draftedPlayers.map(p => p[xField]);
                vals.sort((a,b) => a - b);
                
                if (vals.length === 0) {
                    Plotly.purge('plot');
                    return;
                }
                
                function quantile(arr, q) {
                    const pos = (arr.length - 1) * q;
                    const base = Math.floor(pos);
                    const rest = pos - base;
                    if (arr[base + 1] !== undefined) return arr[base] + rest * (arr[base + 1] - arr[base]);
                    return arr[base];
                }
                
                const p50 = quantile(vals, 0.50);
                let p10, p90;
                
                if (metricConfig[xField].type === 'speed') {
                    p10 = quantile(vals, 0.90); // Slower is bottom 10%
                    p90 = quantile(vals, 0.10); // Faster is top 10%
                } else {
                    p10 = quantile(vals, 0.10);
                    p90 = quantile(vals, 0.90);
                }
                
                const dec = metricConfig[xField].decimals;
                const traces = [{
                    x: draftedPlayers.map(p => p[xField]),
                    type: 'histogram',
                    marker: { color: '#A9A9A9' },
                    opacity: 0.8,
                    name: 'Drafted',
                    hoverinfo: 'x+y',
                    selected: { marker: { opacity: 0.8 } },
                    unselected: { marker: { opacity: 0.3 } }
                }];
                
                if (recruitPlayers.length > 0) {
                    traces.push({
                        x: recruitPlayers.map(p => p[xField]),
                        y: recruitPlayers.map(() => 0), // Base of the histogram
                        text: recruitPlayers.map(p => p.NAME + " (HS Recruit)"),
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Recruits',
                        marker: {
                            color: '#2ECC71',
                            size: 10,
                            line: {color: 'white', width: 1},
                            symbol: 'diamond'
                        },
                        hoverinfo: 'x+text',
                        cliponaxis: false,
                        selected: { marker: { opacity: 1 } },
                        unselected: { marker: { opacity: 0.3 } }
                    });
                }
                
                const layout = {
                    title: `Distribution of ${metricConfig[xField].label}`,
                    xaxis: { title: metricConfig[xField].label, nticks: 20 },
                    yaxis: { title: 'Number of Players' },
                    dragmode: 'select',
                    hovermode: 'closest',
                    clickmode: 'event',
                    showlegend: false,
                    shapes: [
                        {type: 'line', x0: p50, x1: p50, y0: 0, y1: 1, yref: 'paper', line: {color: '#333', dash: 'dash', width: 2}},
                        {type: 'line', x0: p10, x1: p10, y0: 0, y1: 1, yref: 'paper', line: {color: '#E74C3C', width: 3}},
                        {type: 'line', x0: p90, x1: p90, y0: 0, y1: 1, yref: 'paper', line: {color: '#2ECC71', width: 3}}
                    ],
                    annotations: [
                        {x: p50, y: 1.05, yref: 'paper', text: `Avg: ${p50.toFixed(dec)}`, showarrow: false, font: {color: '#333'}},
                        {x: p10, y: 1.1, yref: 'paper', text: `Bottom 10%: ${p10.toFixed(dec)}`, showarrow: false, font: {color: '#E74C3C'}},
                        {x: p90, y: 1.1, yref: 'paper', text: `Top 10%: ${p90.toFixed(dec)}`, showarrow: false, font: {color: '#2ECC71'}}
                    ],
                    margin: { t: 80 },
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white',
                    barmode: 'overlay'
                };
                
                if (metricConfig[xField].type === 'speed') layout.xaxis.autorange = 'reversed';
                
                traceDataMap[0] = draftedPlayers;
                selectedIndicesByTrace[0] = new Set();
                if (recruitPlayers.length > 0) {
                    traceDataMap[1] = recruitPlayers;
                    selectedIndicesByTrace[1] = new Set();
                }
                
                const config = {
                    displayModeBar: 'hover',
                    displaylogo: false,
                    modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines']
                };
                Plotly.newPlot('plot', traces, layout, config);
                
            } else {
                // SCATTER PLOT MODE
                currentValidData = activePlayers.filter(p => 
                    p[xField] !== null && !isNaN(p[xField]) && 
                    p[yField] !== null && !isNaN(p[yField])
                );
                
                if (currentValidData.length === 0) {
                    Plotly.purge('plot');
                    return;
                }
                
                const trace = {
                    x: currentValidData.map(p => p[xField]),
                    y: currentValidData.map(p => p[yField]),
                    text: currentValidData.map(p => {
                        if (p.is_recruit) return p.NAME + " (HS Recruit)";
                        return p.NAME + (p.ROUND ? ` (Round ${p.ROUND})` : '');
                    }),
                    mode: 'markers',
                    type: 'scatter',
                    marker: { 
                        size: currentValidData.map(p => {
                            if (p.is_recruit) return 14;
                            if (!p.ROUND || isNaN(p.ROUND)) return 10;
                            return Math.max(7, 25 - (p.ROUND - 1) * 3);
                        }), 
                        color: currentValidData.map(p => {
                            if (p.is_recruit) return '#2ECC71'; // Bright green for recruits
                            if (p.TEAM && nflColors[p.TEAM.trim()]) return nflColors[p.TEAM.trim()];
                            return '#BF5700';
                        }), 
                        opacity: 0.8, 
                        line: {width: 1, color: 'white'}
                    },
                    selected: { marker: { opacity: 1 } },
                    unselected: { marker: { opacity: 0.2 } }
                };
                
                const layout = {
                    title: `${metricConfig[yField].label} vs ${metricConfig[xField].label}`,
                    xaxis: { title: metricConfig[xField].label, nticks: 20 },
                    yaxis: { title: metricConfig[yField].label },
                    dragmode: 'select',
                    hovermode: 'closest',
                    clickmode: 'event',
                    plot_bgcolor: 'white',
                    paper_bgcolor: 'white',
                    margin: { t: 60 }
                };
                
                if (metricConfig[xField].type === 'speed') layout.xaxis.autorange = 'reversed';
                if (metricConfig[yField].type === 'speed') layout.yaxis.autorange = 'reversed';
                
                traceDataMap[0] = currentValidData;
                selectedIndicesByTrace[0] = new Set();
                
                const config = {
                    displayModeBar: 'hover',
                    displaylogo: false,
                    modeBarButtonsToRemove: ['zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines']
                };
                Plotly.newPlot('plot', [trace], layout, config);
            }
            
            // Re-bind Custom Selection Events
            const plotEl = document.getElementById('plot');
            plotEl.removeAllListeners('plotly_selected');
            plotEl.removeAllListeners('plotly_click');
            plotEl.removeAllListeners('plotly_deselect');
            
            plotEl.on('plotly_click', function(eventData) {
                if (eventData === undefined) return;
                let changed = false;
                eventData.points.forEach(pt => {
                    const curve = pt.curveNumber;
                    if (!selectedIndicesByTrace[curve]) selectedIndicesByTrace[curve] = new Set();
                    
                    let indices = pt.pointNumbers || [pt.pointIndex];
                    indices.forEach(idx => {
                        if (selectedIndicesByTrace[curve].has(idx)) {
                            selectedIndicesByTrace[curve].delete(idx);
                        } else {
                            selectedIndicesByTrace[curve].add(idx);
                        }
                        changed = true;
                    });
                });
                if (changed) applySelectionToPlot();
            });
            
            plotEl.on('plotly_selected', function(eventData) {
                if (eventData === undefined) {
                    clearSelection();
                    return;
                }
                Object.keys(selectedIndicesByTrace).forEach(k => selectedIndicesByTrace[k].clear());
                
                eventData.points.forEach(pt => {
                    const curve = pt.curveNumber;
                    if (!selectedIndicesByTrace[curve]) selectedIndicesByTrace[curve] = new Set();
                    
                    let indices = pt.pointNumbers || [pt.pointIndex];
                    indices.forEach(idx => selectedIndicesByTrace[curve].add(idx));
                });
                applySelectionToPlot();
            });
            
            plotEl.on('plotly_deselect', clearSelection);
            
            // Initial table render for valid data
            renderCards(currentValidData);
        }
        
        // Listeners
        chartTypeSelect.addEventListener('change', drawPlot);
        xSelect.addEventListener('change', drawPlot);
        ySelect.addEventListener('change', drawPlot);
        document.getElementById('toggle-recruits').addEventListener('change', drawPlot);
        document.getElementById('clear-selection').addEventListener('click', clearSelection);
        
        // Initial Plot
        drawPlot();

    </script>
</body>
</html>"""
    
    html_path = os.path.join(base_path, 'index.html')
    with open(html_path, 'w') as f:
        f.write(html_template)
    
    print(f"Successfully built index.html")

if __name__ == "__main__":
    build_html()
