import re
from html.parser import HTMLParser


class TableRowParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current_row = []
        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = []

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.current_cell is not None:
            value = " ".join("".join(self.current_cell).split())
            self.current_row.append(value)
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None


def parse_arm_length(report_html):
    parser = TableRowParser()
    parser.feed(report_html)
    arm_values = []
    for row in parser.rows:
        if len(row) >= 2 and row[0].strip().lower() == "arm":
            value = row[1].strip()
            if re.search(r"\d", value):
                arm_values.append(value)
    return arm_values[-1] if arm_values else ""


def fetch_arm_length(session, player_id):
    if not player_id:
        return ""
    url = f"https://ucreport.us/dashboard/setReportGen/{player_id}"
    response = session.get(
        url,
        headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "referer": "https://ucreport.us/dashboard/",
        },
        timeout=20,
        allow_redirects=True,
    )
    if response.status_code != 200:
        return ""
    return parse_arm_length(response.text)
