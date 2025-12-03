#!/usr/bin/env python3
"""
Grafana Dashboard Import/Export Script

Imports EJE dashboards to Grafana via API and exports existing dashboards.
"""

import json
import os
import requests
from pathlib import Path
from typing import Dict, List, Optional
import argparse


class GrafanaClient:
    """Client for Grafana API operations."""

    def __init__(self, url: str, api_key: str):
        """
        Initialize Grafana client.

        Args:
            url: Grafana URL (e.g., http://localhost:3000)
            api_key: Grafana API key or admin:admin
        """
        self.url = url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def import_dashboard(self, dashboard_path: Path) -> Dict:
        """
        Import dashboard from JSON file.

        Args:
            dashboard_path: Path to dashboard JSON file

        Returns:
            API response
        """
        with open(dashboard_path, 'r') as f:
            dashboard_data = json.load(f)

        payload = {
            'dashboard': dashboard_data,
            'overwrite': True,
            'message': f'Imported from {dashboard_path.name}'
        }

        response = requests.post(
            f'{self.url}/api/dashboards/db',
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def export_dashboard(self, uid: str, output_path: Path) -> None:
        """
        Export dashboard by UID to JSON file.

        Args:
            uid: Dashboard UID
            output_path: Path to save dashboard JSON
        """
        response = requests.get(
            f'{self.url}/api/dashboards/uid/{uid}',
            headers=self.headers
        )
        response.raise_for_status()

        dashboard_data = response.json()['dashboard']

        with open(output_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2)

        print(f'✓ Exported dashboard {uid} to {output_path}')

    def list_dashboards(self) -> List[Dict]:
        """
        List all dashboards.

        Returns:
            List of dashboard metadata
        """
        response = requests.get(
            f'{self.url}/api/search?type=dash-db',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()


def import_all_dashboards(client: GrafanaClient, dashboards_dir: Path) -> None:
    """
    Import all dashboards from directory.

    Args:
        client: Grafana client
        dashboards_dir: Directory containing dashboard JSON files
    """
    dashboard_files = list(dashboards_dir.glob('*.json'))

    if not dashboard_files:
        print(f'No dashboard files found in {dashboards_dir}')
        return

    print(f'\nImporting {len(dashboard_files)} dashboards...\n')

    for dashboard_file in dashboard_files:
        try:
            result = client.import_dashboard(dashboard_file)
            print(f'✓ Imported: {dashboard_file.name}')
            print(f'  URL: {result.get("url", "N/A")}')
            print(f'  UID: {result.get("uid", "N/A")}\n')
        except Exception as e:
            print(f'✗ Failed to import {dashboard_file.name}: {e}\n')


def export_all_dashboards(client: GrafanaClient, output_dir: Path) -> None:
    """
    Export all dashboards to directory.

    Args:
        client: Grafana client
        output_dir: Directory to save dashboard JSON files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    dashboards = client.list_dashboards()

    print(f'\nExporting {len(dashboards)} dashboards...\n')

    for dashboard in dashboards:
        uid = dashboard['uid']
        title = dashboard['title']
        filename = f"{uid}.json"
        output_path = output_dir / filename

        try:
            client.export_dashboard(uid, output_path)
        except Exception as e:
            print(f'✗ Failed to export {title}: {e}')


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Import/Export Grafana dashboards')
    parser.add_argument(
        'action',
        choices=['import', 'export'],
        help='Action to perform'
    )
    parser.add_argument(
        '--url',
        default=os.getenv('GRAFANA_URL', 'http://localhost:3000'),
        help='Grafana URL (default: http://localhost:3000)'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('GRAFANA_API_KEY', ''),
        help='Grafana API key (or use GRAFANA_API_KEY env var)'
    )
    parser.add_argument(
        '--dir',
        type=Path,
        default=Path(__file__).parent / 'dashboards',
        help='Directory containing dashboard files'
    )

    args = parser.parse_args()

    if not args.api_key:
        print('Error: API key required. Set GRAFANA_API_KEY or use --api-key')
        return 1

    client = GrafanaClient(args.url, args.api_key)

    if args.action == 'import':
        import_all_dashboards(client, args.dir)
    elif args.action == 'export':
        export_all_dashboards(client, args.dir)

    print('\nDone!')


if __name__ == '__main__':
    exit(main() or 0)
