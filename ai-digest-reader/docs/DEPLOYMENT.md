# Deployment

## Vercel Deployment

### Prerequisites
- Vercel account
- GitHub repository connected to Vercel

### Steps

1. **Connect repository**
   ```bash
   # Install Vercel CLI
   npm install -g vercel

   # Login
   vercel login

   # Deploy
   vercel
   ```

2. **Configure project**
   - Framework Preset: Astro
   - Build Command: `npm run build`
   - Output Directory: `dist`

3. **Deploy**
   ```bash
   vercel --prod
   ```

### Manual Deployment

```bash
# Build locally
npm run build

# Deploy dist folder
vercel deploy dist/
```

## GitHub Actions (Auto-Regeneration)

### Workflow Setup

Create `.github/workflows/generate-digest.yml`:

```yaml
name: Generate Digest

on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM UTC
  workflow_dispatch:       # Manual trigger

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install requests
          python scripts/generate_json.py public/data/digest.json
      
      - name: Commit and push
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add public/data/digest.json
          git diff --staged --quiet || git commit -m "chore: update digest $(date -u +%Y-%m-%d)"
          git push
```

### Triggering Rebuilds

The workflow runs automatically at 8 AM UTC daily. To manually trigger:

1. Go to Actions tab in GitHub
2. Select "Generate Digest"
3. Click "Run workflow"

## Environment Variables

No environment variables required for basic deployment.

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VERCEL_GIT_COMMIT_REF` | Git branch (auto-set) | - |

## Build Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run check` | TypeScript validation |

## Troubleshooting

### Build Fails

```bash
# Clear cache and rebuild
rm -rf node_modules
npm install
npm run build
```

### JSON Not Updating

1. Check `public/data/` directory exists
2. Verify `digest.json` is valid JSON
3. Ensure file is committed to Git
4. Check Vercel deployment logs

### Type Errors

```bash
# Run type checking
npm run check
```

### PWA Not Working

1. Clear browser cache
2. Check service worker registration in DevTools
3. Verify site is served over HTTPS

## Data Generation (Local)

```bash
# From project root (parent directory)
cd ..
python -c "from ai-digest-reader.scripts.generate_json import generate_json; generate_json('ai-digest-reader/public/data/digest.json')"
```
