# Car Guessing Game - Project Log

## Project Overview
A web app where users guess the year, make, and model of cars from closed auctions on Cars And Bids and Bring A Trailer.

### Features
- **Free Play Mode**: Guess a single random car
- **Competition Mode**: 10 cars, no duplicate make+model, scoring system
  - Points: Make (lowest) < Year < Model (highest) + Bonus for all three

### Tech Stack
- Backend: Python (built-in http.server, no external dependencies!)
- Frontend: HTML/CSS/JavaScript (vanilla, single-page app)
- Data Sources: Bring A Trailer (working), Cars And Bids (blocked by their WAF)

---

## Development Log

### Session 1 - Initial Development
**Date**: 2026-01-19

#### Tasks Completed:
- [x] Project structure setup
- [x] Research data sources (BaT working, C&B blocked)
- [x] Backend API development (Python)
- [x] Frontend UI development (responsive, mobile-friendly)
- [x] Free Play mode implementation
- [x] Competition mode implementation
- [x] Local testing - WORKING!
- [x] Remote deployment options documented

#### Notes:
- Originally planned Node.js but switched to Python (no npm installed)
- Bring A Trailer scraping works perfectly (~20+ cars per refresh)
- Cars And Bids blocks requests (403/WAF) - would need browser automation
- Game is fully functional with BaT data alone

---

## How to Run

### Local Development
```bash
cd car-guess-game
python server.py
# Open http://localhost:3000 in your browser
```

### Access from Phone (Same Network)
1. Find your computer's local IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. Run the server: `python server.py`
3. On your phone, open: `http://YOUR_LOCAL_IP:3000`

### Remote Deployment Options

#### Option 1: ngrok (Recommended for quick testing)
```bash
# Install ngrok from https://ngrok.com
ngrok http 3000
# Use the provided URL to access from anywhere
```

#### Option 2: Deploy to Render.com (Free)
1. Create account at render.com
2. Create new Web Service
3. Connect to GitHub repo
4. Set start command: `python server.py`
5. Set environment: Python 3

#### Option 3: Deploy to Railway.app (Free)
1. Create account at railway.app
2. Connect GitHub repo
3. Deploy automatically

---

## Data Source Research

### Bring A Trailer (bringatrailer.com) - WORKING
- Auction data embedded in page as `auctionsCompletedInitialData`
- JSON format with title, thumbnail, bid info
- Titles follow pattern: "YEAR MAKE MODEL VARIANT"
- ~36 cars per page load

### Cars And Bids (carsandbids.com) - BLOCKED
- Site uses WAF/Cloudflare protection
- Returns minimal HTML without auction data
- Would need Selenium/Playwright for full scraping
- Future enhancement: could add browser automation

---

## Scoring System (Competition Mode)
- Make correct: 10 points
- Year correct: 25 points
- Model correct: 50 points
- All three correct bonus: 25 points
- Maximum per car: 110 points
- Maximum total (10 cars): 1,100 points

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get car count and last update time |
| `/api/random-car` | GET | Get a random car for free play |
| `/api/competition-cars` | GET | Get 10 unique cars for competition |
| `/api/check-answer` | POST | Submit and check a guess |
| `/api/refresh` | POST | Force refresh car cache |

---

## File Structure
```
car-guess-game/
├── PROJECT_LOG.md      # This file
├── server.py           # Python backend server
├── test_scrape.py      # Scraping debug script
└── public/
    └── index.html      # Frontend (single file)
```

---

## Future Updates
- [ ] Add Cars And Bids via browser automation
- [ ] Add user accounts and leaderboards
- [ ] Add difficulty levels (hide more info)
- [ ] Add hints system
- [ ] Mobile app version

