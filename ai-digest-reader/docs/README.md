# AI Digest Reader

A mobile-first PWA news reader that aggregates AI-related content from Reddit and Hacker News into a clean, personalized digest.

## Features

- **Multi-source aggregation** - Combines posts from Reddit (r/ArtificialIntelligence, r/LocalLLaMA, r/ChatGPT, r/MachineLearning) and Hacker News
- **Three view modes** - Cards, list, and glance views for different browsing preferences
- **Source filtering** - Filter content by Reddit, Hacker News, or view all
- **Dark mode** - Automatic theme detection with manual toggle
- **Offline support** - PWA with service worker caching
- **Responsive design** - Mobile-first approach with desktop support

## Quick Start

### Frontend (Astro)

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend (Python Digest Generator)

```bash
cd ai-digest-reader

# Create virtual environment
python3 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install requests

# Generate digest JSON (stdout)
python scripts/generate_json.py

# Generate and save to file
python scripts/generate_json.py > public/data/digest.json
```

### Running with Sample Data

The project includes sample data at `public/data/digest.json`. After generating your own data, the JSON is printed to stdout - redirect it to the data file.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Astro 4, Tailwind CSS 3, Vanilla JavaScript |
| Backend | Python CLI (data generation) |
| Deployment | Vercel |
| Data | JSON (generated daily) |

## Screenshots

*Screenshots coming soon*

### Card View
![Card View Placeholder]

### List View
![List View Placeholder]

### Glance View
![Glance View Placeholder]
