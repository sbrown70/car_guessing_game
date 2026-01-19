# Car Guessing Game

A web app where you guess the year, make, and model of cars from closed auctions on Bring A Trailer.

## Quick Start

```bash
cd C:\claude_code\car-guess-game
python server.py
```
Then open **http://localhost:3000** in your browser.

---

## Features

- **Free Play Mode**: Guess random cars one at a time
- **Competition Mode**: 10 cars, unique make+models, cumulative scoring
- **Smart Year Scoring**: Partial points for close guesses
- **Mobile-Friendly**: Works great on phones

---

## Scoring System

| Category | Points | Notes |
|----------|--------|-------|
| Make | 10 | Exact match required |
| Year (exact) | 25 | Perfect match |
| Year (±1) | 15 | One year off |
| Year (±2) | 5 | Two years off |
| Year (±3+) | 0 | Three or more years off |
| Model | 50 | Flexible matching |
| Perfect Bonus | 25 | All three exact (year must be exact) |

**Max per car**: 110 points
**Max competition (10 cars)**: 1,100 points

---

## Running Locally

### Basic Start
```bash
cd C:\claude_code\car-guess-game
python server.py
```
Open: http://localhost:3000

### Play on Phone (Same WiFi)
```bash
python start.py
```
This shows your local IP. On your phone, open: `http://YOUR_IP:3000`

---

## Deploy to the Internet (Free)

### Step 1: Create GitHub Repository
1. Go to https://github.com/new
2. Name: `car-guess-game`
3. Keep public, don't add README
4. Click "Create repository"

### Step 2: Push Your Code
```bash
cd C:\claude_code\car-guess-game
git remote add origin https://github.com/YOUR_USERNAME/car-guess-game.git
git push -u origin master
```

### Step 3: Deploy on Render
1. Go to https://render.com (sign up with GitHub)
2. Click **New** → **Web Service**
3. Connect GitHub and select `car-guess-game`
4. Settings auto-detect from `render.yaml`
5. Click **Create Web Service**

In ~2 minutes you'll get a URL like:
`https://car-guess-game-xxxx.onrender.com`

**Note**: Free tier sleeps after 15 min inactivity (~30 sec wake time).

---

## Alternative: ngrok (Quick Testing)

If you just want to share temporarily:

1. Sign up at https://ngrok.com (free)
2. Install ngrok and add your auth token:
   ```bash
   ngrok config add-authtoken YOUR_TOKEN
   ```
3. Run:
   ```bash
   python start_public.py
   ```

This gives you a public URL that works while your computer is on.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Car count and last update time |
| `/api/random-car` | GET | Get a random car for free play |
| `/api/competition-cars` | GET | Get 10 unique cars for competition |
| `/api/check-answer` | POST | Submit guess and get results |
| `/api/refresh` | POST | Force refresh car cache |

### Check Answer Request
```json
{
  "carId": "bat-123456",
  "year": "1969",
  "make": "Chevrolet",
  "model": "Camaro"
}
```

### Check Answer Response
```json
{
  "yearCorrect": false,
  "yearDiff": 1,
  "yearPoints": 15,
  "makeCorrect": true,
  "modelCorrect": true,
  "score": 75,
  "correctAnswer": {
    "year": "1970",
    "make": "Chevrolet",
    "model": "Camaro Z/28"
  }
}
```

---

## File Structure

```
car-guess-game/
├── server.py           # Main Python server
├── start.py            # Easy launcher (shows IP)
├── start_public.py     # Launcher with ngrok tunnel
├── public/
│   └── index.html      # Frontend (single file)
├── render.yaml         # Render deployment config
├── Procfile            # Heroku/Railway config
├── requirements.txt    # Python dependencies (none!)
└── PROJECT_LOG.md      # This documentation
```

---

## Data Source

Currently scrapes **Bring A Trailer** (bringatrailer.com) for closed auction data.

**Cars And Bids** is blocked by their firewall - would need browser automation to add.

---

## Development Log

### Session 1 - 2026-01-19
- Built complete game with Free Play and Competition modes
- Implemented distance-based year scoring
- Added guess vs correct answer comparison display
- Set up for Render deployment

### Future Ideas
- [ ] Add Cars And Bids via Selenium/Playwright
- [ ] User accounts and leaderboards
- [ ] Difficulty levels (hide more info)
- [ ] Hints system
- [ ] Offline mode with cached cars

