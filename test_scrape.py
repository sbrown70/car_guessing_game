#!/usr/bin/env python3
"""Test scraping for debugging."""

import json
import re
from urllib.request import urlopen, Request

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def test_bat():
    print("Testing Bring A Trailer...")
    try:
        req = Request('https://bringatrailer.com/auctions/results/', headers=BROWSER_HEADERS)
        with urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')

        print(f"Got response: {len(html)} bytes")

        # Try different patterns to find the data
        patterns = [
            r'auctionsCompletedInitialData\s*=\s*(\{[\s\S]*?\});',
            r'"items"\s*:\s*(\[[\s\S]*?\])',
            r'<script[^>]*type="application/json"[^>]*>([\s\S]*?)</script>',
        ]

        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, html)
            print(f"Pattern {i+1}: Found {len(matches)} matches")
            if matches:
                sample = matches[0][:200] if matches[0] else "empty"
                print(f"  Sample: {sample}...")

        # Look for any JSON with items
        if 'auctionsCompletedInitialData' in html:
            print("Found 'auctionsCompletedInitialData' string in page!")
            # Get surrounding context
            idx = html.find('auctionsCompletedInitialData')
            print(f"Context: {html[idx:idx+300]}...")
        else:
            print("No 'auctionsCompletedInitialData' found")

        # Check if it's a client-side rendered page
        if '__NEXT_DATA__' in html:
            print("Found __NEXT_DATA__ - it's a Next.js page")
            next_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html)
            if next_match:
                try:
                    data = json.loads(next_match.group(1))
                    props = data.get('props', {}).get('pageProps', {})
                    print(f"PageProps keys: {props.keys()}")
                except:
                    print("Could not parse NEXT_DATA")

    except Exception as e:
        print(f"Error: {e}")


def test_cab():
    print("\n\nTesting Cars And Bids...")
    try:
        headers = {
            **BROWSER_HEADERS,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://carsandbids.com/',
        }
        req = Request('https://carsandbids.com/past-auctions/', headers=headers)

        with urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')

        print(f"Got response: {len(html)} bytes")

        # Check for various data patterns
        if '__NEXT_DATA__' in html:
            print("Found __NEXT_DATA__")
            next_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html)
            if next_match:
                try:
                    data = json.loads(next_match.group(1))
                    props = data.get('props', {}).get('pageProps', {})
                    print(f"PageProps keys: {list(props.keys())}")

                    # Look for auction data
                    for key, value in props.items():
                        if isinstance(value, list) and len(value) > 0:
                            print(f"  {key}: list with {len(value)} items")
                            if isinstance(value[0], dict):
                                print(f"    First item keys: {list(value[0].keys())[:10]}")
                        elif isinstance(value, dict):
                            print(f"  {key}: dict with keys {list(value.keys())[:5]}")
                except Exception as e:
                    print(f"Error parsing NEXT_DATA: {e}")
        else:
            print("No __NEXT_DATA__ found")

        # Look for other JSON patterns
        json_patterns = [
            r'"auctions"\s*:\s*\[',
            r'"pastAuctions"\s*:\s*\[',
            r'"results"\s*:\s*\[',
        ]
        for pattern in json_patterns:
            if re.search(pattern, html):
                print(f"Found pattern: {pattern}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    test_bat()
    test_cab()
