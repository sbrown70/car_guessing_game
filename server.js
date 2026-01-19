const express = require('express');
const cors = require('cors');
const axios = require('axios');
const cheerio = require('cheerio');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Cache for scraped car data
let carCache = {
  bringATrailer: [],
  carsAndBids: [],
  lastUpdated: null
};

// Common headers to mimic browser requests
const browserHeaders = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.5',
  'Connection': 'keep-alive',
};

// Parse year, make, model from title
function parseCarTitle(title) {
  // Common pattern: "YEAR MAKE MODEL VARIANT"
  // Examples: "1997 Porsche 911 Carrera 4S Coupe 6-Speed"
  //           "2020 Ford Mustang Shelby GT500"

  const cleaned = title.replace(/\s+/g, ' ').trim();
  const yearMatch = cleaned.match(/^(\d{4})\s+/);

  if (!yearMatch) return null;

  const year = yearMatch[1];
  const rest = cleaned.substring(yearMatch[0].length);

  // Known makes to help with parsing
  const knownMakes = [
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
  ];

  let make = null;
  let modelStart = 0;

  // Check for known makes (case-insensitive)
  for (const knownMake of knownMakes) {
    if (rest.toLowerCase().startsWith(knownMake.toLowerCase())) {
      make = knownMake;
      modelStart = knownMake.length;
      break;
    }
  }

  // If no known make found, use first word
  if (!make) {
    const firstSpace = rest.indexOf(' ');
    if (firstSpace > 0) {
      make = rest.substring(0, firstSpace);
      modelStart = firstSpace;
    } else {
      make = rest;
      modelStart = rest.length;
    }
  }

  // Get model - typically the next word(s) before variant descriptors
  let modelPart = rest.substring(modelStart).trim();

  // Remove common suffixes that aren't part of the model name
  const suffixPatterns = [
    /\s+\d+-Speed$/i,
    /\s+Manual$/i,
    /\s+Automatic$/i,
    /\s+Auto$/i,
    /\s+Coupe$/i,
    /\s+Sedan$/i,
    /\s+Convertible$/i,
    /\s+Wagon$/i,
    /\s+Hatchback$/i,
    /\s+SUV$/i,
    /\s+Roadster$/i,
    /\s+Cabriolet$/i,
    /\s+Targa$/i,
    /\s+Spyder$/i,
    /\s+Spider$/i,
  ];

  for (const pattern of suffixPatterns) {
    modelPart = modelPart.replace(pattern, '');
  }

  // Take first 2-3 words as model
  const modelWords = modelPart.split(' ').filter(w => w.length > 0);
  let model = modelWords.slice(0, 3).join(' ').trim();

  // Clean up model
  if (!model || model.length === 0) {
    model = modelWords[0] || 'Unknown';
  }

  return { year, make, model };
}

// Scrape Bring A Trailer
async function scrapeBringATrailer() {
  try {
    console.log('Scraping Bring A Trailer...');
    const response = await axios.get('https://bringatrailer.com/auctions/results/', {
      headers: browserHeaders,
      timeout: 30000
    });

    const html = response.data;

    // Extract the auctionsCompletedInitialData from the script
    const dataMatch = html.match(/auctionsCompletedInitialData\s*=\s*(\{[\s\S]*?\});?\s*(?:var|const|let|<\/script>)/);

    if (!dataMatch) {
      console.log('Could not find BaT data in page');
      return [];
    }

    let jsonStr = dataMatch[1];
    // Clean up the JSON string
    jsonStr = jsonStr.replace(/,\s*\}/, '}').replace(/,\s*\]/, ']');

    const data = JSON.parse(jsonStr);
    const listings = data.items || [];

    const cars = [];
    for (const item of listings) {
      const title = item.title || '';
      const parsed = parseCarTitle(title);

      if (parsed && item.thumbnail_url) {
        cars.push({
          id: `bat-${item.id || Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          source: 'Bring A Trailer',
          title: title,
          year: parsed.year,
          make: parsed.make,
          model: parsed.model,
          imageUrl: item.thumbnail_url.replace(/\?resize=\d+%2C\d+/, '?resize=800%2C600'),
          auctionUrl: item.url || ''
        });
      }
    }

    console.log(`Found ${cars.length} cars from Bring A Trailer`);
    return cars;
  } catch (error) {
    console.error('Error scraping BaT:', error.message);
    return [];
  }
}

// Scrape Cars And Bids
async function scrapeCarsAndBids() {
  try {
    console.log('Scraping Cars And Bids...');
    const response = await axios.get('https://carsandbids.com/past-auctions/', {
      headers: {
        ...browserHeaders,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://carsandbids.com/',
      },
      timeout: 30000
    });

    const $ = cheerio.load(response.data);
    const cars = [];

    // Find auction items - they usually have a specific structure
    $('.auction-item, .past-auction, [class*="auction"]').each((i, elem) => {
      const $item = $(elem);

      // Try to find title
      let title = $item.find('h3, h2, .title, .auction-title, [class*="title"]').first().text().trim();
      if (!title) {
        title = $item.find('a').first().text().trim();
      }

      // Try to find image
      let imageUrl = $item.find('img').first().attr('src') ||
                     $item.find('img').first().attr('data-src') ||
                     $item.find('[style*="background-image"]').first().css('background-image');

      if (imageUrl && imageUrl.includes('url(')) {
        imageUrl = imageUrl.replace(/url\(['"]?/, '').replace(/['"]?\)/, '');
      }

      const parsed = parseCarTitle(title);

      if (parsed && imageUrl) {
        cars.push({
          id: `cab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          source: 'Cars And Bids',
          title: title,
          year: parsed.year,
          make: parsed.make,
          model: parsed.model,
          imageUrl: imageUrl,
          auctionUrl: $item.find('a').first().attr('href') || ''
        });
      }
    });

    // Alternative: try to find JSON data in script tags
    if (cars.length === 0) {
      $('script').each((i, elem) => {
        const scriptContent = $(elem).html() || '';
        if (scriptContent.includes('auctions') || scriptContent.includes('listings')) {
          // Try to extract auction data from inline scripts
          const jsonMatches = scriptContent.match(/\[\s*\{[^[\]]*"title"[^[\]]*\}\s*\]/g);
          if (jsonMatches) {
            for (const match of jsonMatches) {
              try {
                const items = JSON.parse(match);
                for (const item of items) {
                  if (item.title && item.image) {
                    const parsed = parseCarTitle(item.title);
                    if (parsed) {
                      cars.push({
                        id: `cab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                        source: 'Cars And Bids',
                        title: item.title,
                        year: parsed.year,
                        make: parsed.make,
                        model: parsed.model,
                        imageUrl: item.image,
                        auctionUrl: item.url || ''
                      });
                    }
                  }
                }
              } catch (e) {
                // Continue trying
              }
            }
          }
        }
      });
    }

    console.log(`Found ${cars.length} cars from Cars And Bids`);
    return cars;
  } catch (error) {
    console.error('Error scraping C&B:', error.message);
    return [];
  }
}

// Refresh car cache
async function refreshCache() {
  console.log('Refreshing car cache...');

  const [batCars, cabCars] = await Promise.all([
    scrapeBringATrailer(),
    scrapeCarsAndBids()
  ]);

  carCache.bringATrailer = batCars;
  carCache.carsAndBids = cabCars;
  carCache.lastUpdated = new Date();

  console.log(`Cache refreshed: ${batCars.length} BaT, ${cabCars.length} C&B cars`);
}

// Get all cars from cache
function getAllCars() {
  return [...carCache.bringATrailer, ...carCache.carsAndBids];
}

// Get random car
function getRandomCar() {
  const allCars = getAllCars();
  if (allCars.length === 0) return null;
  return allCars[Math.floor(Math.random() * allCars.length)];
}

// Get unique cars for competition (no duplicate make+model)
function getCompetitionCars(count = 10) {
  const allCars = getAllCars();
  if (allCars.length < count) return allCars;

  const selected = [];
  const usedMakeModels = new Set();
  const shuffled = [...allCars].sort(() => Math.random() - 0.5);

  for (const car of shuffled) {
    const key = `${car.make.toLowerCase()}-${car.model.toLowerCase()}`;
    if (!usedMakeModels.has(key)) {
      usedMakeModels.add(key);
      selected.push(car);
      if (selected.length >= count) break;
    }
  }

  return selected;
}

// API Routes

// Get a random car for free play
app.get('/api/random-car', (req, res) => {
  const car = getRandomCar();
  if (!car) {
    return res.status(503).json({ error: 'No cars available. Please try again later.' });
  }

  // Return car data without revealing answers
  res.json({
    id: car.id,
    imageUrl: car.imageUrl,
    source: car.source
  });
});

// Get cars for competition mode
app.get('/api/competition-cars', (req, res) => {
  const cars = getCompetitionCars(10);
  if (cars.length < 10) {
    return res.status(503).json({ error: 'Not enough cars available. Please try again later.' });
  }

  // Return cars without revealing answers
  res.json(cars.map(car => ({
    id: car.id,
    imageUrl: car.imageUrl,
    source: car.source
  })));
});

// Submit answer and check
app.post('/api/check-answer', (req, res) => {
  const { carId, year, make, model } = req.body;

  const allCars = getAllCars();
  const car = allCars.find(c => c.id === carId);

  if (!car) {
    return res.status(404).json({ error: 'Car not found' });
  }

  // Normalize strings for comparison
  const normalize = (str) => str.toLowerCase().trim().replace(/[-\s]+/g, ' ');

  const yearCorrect = year.toString() === car.year.toString();
  const makeCorrect = normalize(make) === normalize(car.make);

  // More flexible model matching
  const userModel = normalize(model);
  const correctModel = normalize(car.model);
  const modelCorrect = userModel === correctModel ||
                       correctModel.includes(userModel) ||
                       userModel.includes(correctModel);

  // Calculate score
  let score = 0;
  if (makeCorrect) score += 10;
  if (yearCorrect) score += 25;
  if (modelCorrect) score += 50;
  if (makeCorrect && yearCorrect && modelCorrect) score += 25; // Bonus

  res.json({
    yearCorrect,
    makeCorrect,
    modelCorrect,
    score,
    correctAnswer: {
      year: car.year,
      make: car.make,
      model: car.model,
      title: car.title,
      auctionUrl: car.auctionUrl
    }
  });
});

// Get cache status
app.get('/api/status', (req, res) => {
  res.json({
    bringATrailerCount: carCache.bringATrailer.length,
    carsAndBidsCount: carCache.carsAndBids.length,
    totalCars: getAllCars().length,
    lastUpdated: carCache.lastUpdated
  });
});

// Refresh cache manually
app.post('/api/refresh', async (req, res) => {
  await refreshCache();
  res.json({
    success: true,
    totalCars: getAllCars().length,
    lastUpdated: carCache.lastUpdated
  });
});

// Serve the main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, async () => {
  console.log(`Car Guess Game server running on http://localhost:${PORT}`);

  // Initial cache refresh
  await refreshCache();

  // Refresh cache every 30 minutes
  setInterval(refreshCache, 30 * 60 * 1000);
});
