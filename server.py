#!/usr/bin/env python3
"""
Car Guess Game - Backend Server
Serves car data from Bring A Trailer and Cars And Bids auctions
"""

import json
import re
import random
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import parse_qs, urlparse
from urllib.error import URLError, HTTPError
import threading
import time

# Try to import Playwright for browser automation
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available - using basic scraping (limited cars)")

PORT = int(os.environ.get('PORT', 3000))

# Cache for scraped car data
car_cache = {
    'bring_a_trailer': [],
    'cars_and_bids': [],
    'last_updated': None
}

# Browser headers
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Known car makes for parsing
KNOWN_MAKES = [
    'Acura', 'Alfa Romeo', 'Aston Martin', 'Audi', 'Bentley', 'BMW', 'Bugatti',
    'Buick', 'Cadillac', 'Chevrolet', 'Chevy', 'Chrysler', 'Citroën', 'Datsun',
    'De Tomaso', 'Dodge', 'Ferrari', 'Fiat', 'Ford', 'Genesis', 'GMC', 'Honda',
    'Hummer', 'Hyundai', 'Infiniti', 'Jaguar', 'Jeep', 'Kia', 'Lamborghini',
    'Land Rover', 'Lexus', 'Lincoln', 'Lotus', 'Maserati', 'Mazda', 'McLaren',
    'Mercedes-Benz', 'Mercedes', 'Mercury', 'Mini', 'Mitsubishi', 'Nissan',
    'Oldsmobile', 'Pagani', 'Peugeot', 'Plymouth', 'Pontiac', 'Porsche', 'Ram',
    'Renault', 'Rolls-Royce', 'Saab', 'Saturn', 'Scion', 'Subaru', 'Suzuki',
    'Tesla', 'Toyota', 'Triumph', 'Volkswagen', 'VW', 'Volvo', 'AMC',
    'American Motors', 'Austin-Healey', 'DeLorean', 'DeTomaso', 'Hudson',
    'International', 'Kaiser', 'Nash', 'Packard', 'Shelby', 'Studebaker',
    'Willys', 'MG', 'TVR', 'Lancia', 'Opel', 'Vauxhall', 'Seat', 'Skoda'
]

# Motorcycle-only makes (always filter these out)
MOTORCYCLE_MAKES = [
    'Harley-Davidson', 'Harley Davidson', 'Harley', 'Ducati', 'Kawasaki',
    'Yamaha', 'Suzuki', 'Indian', 'Moto Guzzi', 'Aprilia', 'KTM', 'MV Agusta',
    'Norton', 'BSA', 'Royal Enfield', 'Husqvarna', 'Benelli', 'Bimota',
    'Buell', 'Victory', 'Can-Am', 'Ural', 'Zero', 'Confederate', 'Arch'
]

# Keywords that indicate a motorcycle (in title)
MOTORCYCLE_KEYWORDS = ['motorcycle', 'motorbike', 'bike', 'scooter', 'moped']


def is_motorcycle(title, make=None):
    """Check if a listing is a motorcycle (should be filtered out)."""
    title_lower = title.lower()

    # Check for motorcycle keywords in title
    for keyword in MOTORCYCLE_KEYWORDS:
        if keyword in title_lower:
            return True

    # Check if make is a motorcycle-only brand
    if make:
        make_lower = make.lower()
        for moto_make in MOTORCYCLE_MAKES:
            if moto_make.lower() == make_lower or moto_make.lower() in make_lower:
                return True

    # Also check title for motorcycle makes
    for moto_make in MOTORCYCLE_MAKES:
        if moto_make.lower() in title_lower:
            return True

    return False


def parse_car_title(title):
    """Parse year, make, model from a car title."""
    cleaned = ' '.join(title.split())
    year_match = re.match(r'^(\d{4})\s+', cleaned)

    if not year_match:
        return None

    year = year_match.group(1)
    rest = cleaned[len(year_match.group(0)):]

    # Find make
    make = None
    model_start = 0

    for known_make in KNOWN_MAKES:
        if rest.lower().startswith(known_make.lower()):
            make = known_make
            model_start = len(known_make)
            break

    if not make:
        first_space = rest.find(' ')
        if first_space > 0:
            make = rest[:first_space]
            model_start = first_space
        else:
            make = rest
            model_start = len(rest)

    # Get model
    model_part = rest[model_start:].strip()

    # Remove common suffixes
    suffix_patterns = [
        r'\s+\d+-Speed$',
        r'\s+Manual$',
        r'\s+Automatic$',
        r'\s+Auto$',
        r'\s+Coupe$',
        r'\s+Sedan$',
        r'\s+Convertible$',
        r'\s+Wagon$',
        r'\s+Hatchback$',
        r'\s+SUV$',
        r'\s+Roadster$',
        r'\s+Cabriolet$',
        r'\s+Targa$',
        r'\s+Spyder$',
        r'\s+Spider$',
    ]

    for pattern in suffix_patterns:
        model_part = re.sub(pattern, '', model_part, flags=re.IGNORECASE)

    # Take first 2-3 words as model
    model_words = [w for w in model_part.split() if w]
    model = ' '.join(model_words[:3]).strip()

    if not model:
        model = model_words[0] if model_words else 'Unknown'

    return {'year': year, 'make': make, 'model': model}


def extract_bat_data_from_html(html):
    """Extract car data from BaT HTML page."""
    marker = 'auctionsCompletedInitialData = '
    start_idx = html.find(marker)

    if start_idx == -1:
        return []

    json_start = start_idx + len(marker)
    brace_count = 0
    json_end = json_start

    for i, char in enumerate(html[json_start:]):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = json_start + i + 1
                break

    try:
        data = json.loads(html[json_start:json_end])
        return data.get('items', [])
    except json.JSONDecodeError:
        return []


def scrape_bring_a_trailer(max_cars=500):
    """Scrape car data from Bring A Trailer using multiple URL variations.

    Args:
        max_cars: Maximum number of cars to collect

    Note: BaT's embedded data is limited, but we try multiple URLs to maximize variety.
    """
    try:
        print('Scraping Bring A Trailer...')
        all_cars = []
        seen_ids = set()

        # URLs to try - different filters/pages to maximize unique cars
        urls_to_try = [
            'https://bringatrailer.com/auctions/results/',
            'https://bringatrailer.com/auctions/results/?page=2',
            'https://bringatrailer.com/auctions/results/?page=3',
            'https://bringatrailer.com/auctions/results/?era=1980s',
            'https://bringatrailer.com/auctions/results/?era=1990s',
            'https://bringatrailer.com/auctions/results/?era=2000s',
            'https://bringatrailer.com/auctions/results/?era=2010s',
            'https://bringatrailer.com/auctions/results/?era=1970s',
            'https://bringatrailer.com/auctions/results/?era=1960s',
            'https://bringatrailer.com/auctions/results/?origin=american',
            'https://bringatrailer.com/auctions/results/?origin=japanese',
            'https://bringatrailer.com/auctions/results/?origin=german',
            'https://bringatrailer.com/auctions/results/?origin=british',
            'https://bringatrailer.com/auctions/results/?origin=italian',
        ]

        for url in urls_to_try:
            if len(all_cars) >= max_cars:
                break

            try:
                req = Request(url, headers=BROWSER_HEADERS)
                with urlopen(req, timeout=30) as response:
                    html = response.read().decode('utf-8')

                listings = extract_bat_data_from_html(html)

                # Parse and dedupe
                new_count = 0
                for item in listings:
                    bat_id = item.get('id', '')
                    if bat_id and bat_id not in seen_ids:
                        seen_ids.add(bat_id)
                        car = parse_bat_listing_item(item)
                        if car:
                            all_cars.append(car)
                            new_count += 1

                if new_count > 0:
                    print(f'  {url.split("?")[-1] if "?" in url else "base"}: +{new_count} new (total: {len(all_cars)})')

                time.sleep(0.2)

            except Exception as e:
                print(f'  Error fetching {url}: {e}')

        print(f'Found {len(all_cars)} unique cars from Bring A Trailer')
        return all_cars

    except Exception as e:
        print(f'Error scraping BaT: {e}')
        return []


def parse_bat_listing_item(item):
    """Parse a single BaT listing item into a car object."""
    title = item.get('title', '')
    parsed = parse_car_title(title)

    if not parsed or not item.get('thumbnail_url'):
        return None

    # Filter out motorcycles
    if is_motorcycle(title, parsed.get('make')):
        return None

    image_url = re.sub(r'\?resize=\d+%2C\d+', '?resize=800%2C600', item['thumbnail_url'])
    bat_id = item.get('id', '') or str(hash(title))[:8]

    return {
        'id': f"bat-{bat_id}",
        'source': 'Bring A Trailer',
        'title': title,
        'year': parsed['year'],
        'make': parsed['make'],
        'model': parsed['model'],
        'imageUrl': image_url,
        'auctionUrl': item.get('url', '')
    }


def scrape_bat_with_playwright(target_cars=500):
    """Scrape BaT using Playwright browser automation for more cars.

    Args:
        target_cars: Target number of cars to collect
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, falling back to basic scraping")
        return scrape_bring_a_trailer()

    print(f'Scraping Bring A Trailer with Playwright (target: {target_cars} cars)...')
    all_cars = []
    seen_ids = set()

    def extract_listings_from_dom(page):
        """Extract listing data directly from DOM elements."""
        return page.evaluate('''() => {
            const items = [];
            const links = document.querySelectorAll('a[href*="/listing/"]');
            const seen = new Set();

            links.forEach(link => {
                const href = link.href;
                if (seen.has(href)) return;
                seen.add(href);

                // Get title from h3 or title class
                const titleEl = link.querySelector('h3, .title, [class*="title"]');
                let title = titleEl?.textContent?.trim() || '';

                // If no title element, try the link text itself
                if (!title) {
                    title = link.textContent?.trim() || '';
                }

                // Get image
                const img = link.querySelector('img') || link.parentElement?.querySelector('img');
                const imgUrl = img?.src || img?.dataset?.src || '';

                // Get ID from URL
                const match = href.match(/listing\\/([^/]+)/);
                const id = match ? match[1] : '';

                // Only include if title starts with a year
                if (title && title.match(/^\\d{4}/) && imgUrl && id) {
                    items.push({
                        title: title,
                        thumbnail_url: imgUrl,
                        id: id,
                        url: href
                    });
                }
            });

            return items;
        }''')

    try:
        with sync_playwright() as p:
            # Launch headless browser
            print('  Launching browser...')
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            # Go to results page
            print('  Loading BaT auction results page...')
            page.goto('https://bringatrailer.com/auctions/results/', timeout=60000)
            page.wait_for_load_state('networkidle', timeout=30000)

            # Click "Show More" button repeatedly to load more cars
            max_clicks = 20  # Each click loads ~20 more cars

            for click_num in range(max_clicks):
                # Extract current listings from DOM
                listings_data = extract_listings_from_dom(page)

                # Parse new listings
                new_count = 0
                for item in listings_data:
                    bat_id = str(item.get('id', ''))
                    if bat_id and bat_id not in seen_ids:
                        seen_ids.add(bat_id)
                        car = parse_bat_listing_item(item)
                        if car:
                            all_cars.append(car)
                            new_count += 1

                print(f'  After click {click_num}: {len(all_cars)} total cars (+{new_count} new)')

                if len(all_cars) >= target_cars:
                    print(f'  Reached target of {target_cars} cars!')
                    break

                # Try to click "Show More" button
                try:
                    show_more = page.locator('button:has-text("Show More")').first
                    if show_more.is_visible():
                        show_more.click()
                        time.sleep(1.5)  # Wait for new content to load
                        page.wait_for_load_state('networkidle', timeout=10000)
                    else:
                        print('  No more "Show More" button visible')
                        break
                except Exception as e:
                    print(f'  Could not click Show More: {e}')
                    break

            browser.close()

    except Exception as e:
        print(f'Playwright error: {e}')
        print('Falling back to basic scraping...')
        return scrape_bring_a_trailer()

    print(f'Found {len(all_cars)} total cars from Bring A Trailer (Playwright)')
    return all_cars


def scrape_cars_and_bids():
    """Scrape car data from Cars And Bids API."""
    try:
        print('Scraping Cars And Bids...')

        # Try their GraphQL/API endpoint
        api_headers = {
            **BROWSER_HEADERS,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://carsandbids.com',
            'Referer': 'https://carsandbids.com/past-auctions/',
        }

        # Try the search API
        api_url = 'https://carsandbids.com/api/auctions?status=ended&limit=50'
        req = Request(api_url, headers=api_headers)

        cars = []
        try:
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))

            auctions = data if isinstance(data, list) else data.get('auctions', []) or data.get('items', []) or data.get('data', [])

            for item in auctions:
                title = item.get('title', '') or item.get('name', '') or ''
                parsed = parse_car_title(title)

                # Get image URL
                image = ''
                if item.get('primaryPhotoUrl'):
                    image = item['primaryPhotoUrl']
                elif item.get('image'):
                    image = item['image']
                elif item.get('photos') and len(item['photos']) > 0:
                    image = item['photos'][0].get('url', '')
                elif item.get('imageUrl'):
                    image = item['imageUrl']

                if parsed and image:
                    slug = item.get('slug', '') or item.get('id', '')
                    cars.append({
                        'id': f"cab-{slug}",
                        'source': 'Cars And Bids',
                        'title': title,
                        'year': parsed['year'],
                        'make': parsed['make'],
                        'model': parsed['model'],
                        'imageUrl': image,
                        'auctionUrl': f"https://carsandbids.com/auctions/{slug}"
                    })
        except Exception as e:
            print(f'API request failed: {e}')

        # If API fails, try HTML scraping as fallback
        if not cars:
            try:
                html_headers = {
                    **BROWSER_HEADERS,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                req = Request('https://carsandbids.com/past-auctions/', headers=html_headers)
                with urlopen(req, timeout=30) as response:
                    html = response.read().decode('utf-8')

                # Look for JSON data in script tags
                script_pattern = re.compile(r'<script[^>]*>([\s\S]*?)</script>')
                for match in script_pattern.finditer(html):
                    script = match.group(1)
                    if '"auctions"' in script or '"title"' in script:
                        # Try to find JSON arrays
                        try:
                            array_match = re.search(r'\[[\s\S]*?"title"\s*:\s*"[^"]+[\s\S]*?\]', script)
                            if array_match:
                                items = json.loads(array_match.group(0))
                                for item in items:
                                    title = item.get('title', '')
                                    image = item.get('image', '') or item.get('primaryPhotoUrl', '')
                                    parsed = parse_car_title(title)
                                    if parsed and image:
                                        cars.append({
                                            'id': f"cab-{hash(title) % 100000}",
                                            'source': 'Cars And Bids',
                                            'title': title,
                                            'year': parsed['year'],
                                            'make': parsed['make'],
                                            'model': parsed['model'],
                                            'imageUrl': image,
                                            'auctionUrl': ''
                                        })
                        except:
                            pass
            except Exception as e:
                print(f'HTML scraping failed: {e}')

        print(f'Found {len(cars)} cars from Cars And Bids')
        return cars

    except Exception as e:
        print(f'Error scraping C&B: {e}')
        return []


def refresh_cache():
    """Refresh the car cache."""
    print('Refreshing car cache...')
    global car_cache

    # Load cars from BaT using Playwright for more results
    if PLAYWRIGHT_AVAILABLE:
        bat_cars = scrape_bat_with_playwright(target_cars=1000)
    else:
        bat_cars = scrape_bring_a_trailer(max_cars=1000)
    cab_cars = scrape_cars_and_bids()

    car_cache['bring_a_trailer'] = bat_cars
    car_cache['cars_and_bids'] = cab_cars
    car_cache['last_updated'] = datetime.now().isoformat()

    print(f'Cache refreshed: {len(bat_cars)} BaT, {len(cab_cars)} C&B cars')


def get_all_cars():
    """Get all cars from cache."""
    return car_cache['bring_a_trailer'] + car_cache['cars_and_bids']


def get_random_car():
    """Get a random car."""
    all_cars = get_all_cars()
    if not all_cars:
        return None
    return random.choice(all_cars)


def get_competition_cars(count=10):
    """Get unique cars for competition (no duplicate make+model)."""
    all_cars = get_all_cars()
    if len(all_cars) < count:
        return all_cars

    selected = []
    used_make_models = set()
    shuffled = all_cars.copy()
    random.shuffle(shuffled)

    for car in shuffled:
        key = f"{car['make'].lower()}-{car['model'].lower()}"
        if key not in used_make_models:
            used_make_models.add(key)
            selected.append(car)
            if len(selected) >= count:
                break

    return selected


def normalize_string(s):
    """Normalize string for comparison - removes punctuation for fuzzy matching.

    Examples:
        'F-250' -> 'f250'
        'GT-R' -> 'gtr'
        '911 Turbo S' -> '911turbos'
    """
    # Remove all non-alphanumeric characters and lowercase
    return re.sub(r'[^a-z0-9]', '', s.lower())


def fuzzy_match(user_input, correct_answer):
    """Check if user input matches correct answer with fuzzy tolerance.

    Handles:
    - Case insensitivity
    - Punctuation differences (F-250 vs f250)
    - Partial matches (both directions)
    """
    user_norm = normalize_string(user_input)
    correct_norm = normalize_string(correct_answer)

    # Exact match after normalization
    if user_norm == correct_norm:
        return True

    # Partial match (one contains the other)
    if correct_norm in user_norm or user_norm in correct_norm:
        return True

    return False


class GameHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for the game."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), 'public'), **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/random-car':
            car = get_random_car()
            if not car:
                self.send_json({'error': 'No cars available. Please try again later.'}, 503)
            else:
                self.send_json({
                    'id': car['id'],
                    'imageUrl': car['imageUrl'],
                    'source': car['source']
                })

        elif path == '/api/competition-cars':
            cars = get_competition_cars(10)
            if len(cars) < 10:
                self.send_json({'error': 'Not enough cars available. Please try again later.'}, 503)
            else:
                self.send_json([{
                    'id': c['id'],
                    'imageUrl': c['imageUrl'],
                    'source': c['source']
                } for c in cars])

        elif path == '/api/status':
            self.send_json({
                'bringATrailerCount': len(car_cache['bring_a_trailer']),
                'carsAndBidsCount': len(car_cache['cars_and_bids']),
                'totalCars': len(get_all_cars()),
                'lastUpdated': car_cache['last_updated']
            })

        else:
            # Serve static files
            if path == '/':
                self.path = '/index.html'
            super().do_GET()

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/check-answer':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            car_id = data.get('carId')
            year = data.get('year', '')
            make = data.get('make', '')
            model = data.get('model', '')

            all_cars = get_all_cars()
            car = next((c for c in all_cars if c['id'] == car_id), None)

            if not car:
                self.send_json({'error': 'Car not found'}, 404)
                return

            # Calculate year difference and points (exponential decay)
            try:
                year_diff = abs(int(year) - int(car['year']))
            except (ValueError, TypeError):
                year_diff = 99  # Invalid year input

            year_exact = year_diff == 0
            # Exponential decay: exact=25, ±1=15, ±2=5, ±3+=0
            year_points_map = {0: 25, 1: 15, 2: 5}
            year_points = year_points_map.get(year_diff, 0)

            make_correct = fuzzy_match(make, car['make'])
            model_correct = fuzzy_match(model, car['model'])

            # Calculate score
            score = 0
            if make_correct:
                score += 10
            score += year_points  # 0-25 based on distance
            if model_correct:
                score += 50
            # Bonus only for perfect answers (year must be exact)
            if make_correct and year_exact and model_correct:
                score += 25

            self.send_json({
                'yearCorrect': year_exact,  # True only if exact match
                'yearDiff': year_diff,
                'yearPoints': year_points,
                'makeCorrect': make_correct,
                'modelCorrect': model_correct,
                'score': score,
                'correctAnswer': {
                    'year': car['year'],
                    'make': car['make'],
                    'model': car['model'],
                    'title': car['title'],
                    'auctionUrl': car['auctionUrl']
                }
            })

        elif path == '/api/refresh':
            refresh_cache()
            self.send_json({
                'success': True,
                'totalCars': len(get_all_cars()),
                'lastUpdated': car_cache['last_updated']
            })

        else:
            self.send_error(404)

    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log format."""
        if args and isinstance(args[0], str) and '/api/' in args[0]:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def cache_refresh_thread():
    """Background thread to refresh cache periodically."""
    while True:
        time.sleep(30 * 60)  # 30 minutes
        refresh_cache()


if __name__ == '__main__':
    print('=' * 50)
    print('Car Guess Game Server')
    print('=' * 50)

    # Initial cache refresh
    refresh_cache()

    # Start background refresh thread
    thread = threading.Thread(target=cache_refresh_thread, daemon=True)
    thread.start()

    # Start server
    server = HTTPServer(('0.0.0.0', PORT), GameHandler)
    print(f'\nServer running at http://localhost:{PORT}')
    print('Press Ctrl+C to stop\n')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        server.shutdown()
