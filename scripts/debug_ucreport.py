"""Read-only API configuration smoke test; does not change exports."""
from ucreport_api import APIError, COLUMNS, UCReportClient

if __name__ == '__main__':
    try:
        client = UCReportClient.from_config()
        row = next(client.rows(filters={'class_field': 2027}, cols=COLUMNS, limit=1), None)
        print('API connected; requested player fields returned.' if row else 'API connected; no visible 2027 players.')
    except APIError as exc:
        raise SystemExit(str(exc))
