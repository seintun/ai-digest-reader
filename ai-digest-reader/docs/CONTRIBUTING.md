# Contributing

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- npm

### Getting Started

```bash
# Clone repository
git clone https://github.com/your-org/ai-digest-reader.git
cd ai-digest-reader

# Install frontend dependencies
npm install

# Install Python dependencies (for data generation)
cd ..
pip install requests
cd ai-digest-reader
```

### Development Workflow

```bash
# Start dev server
npm run dev

# Type check
npm run check

# Build production
npm run build
```

## Code Style

### Formatting
- **Prettier** for code formatting
- Run before committing:
  ```bash
  npm run format
  ```

### Linting
- **ESLint** for JavaScript/TypeScript
- Run checks:
  ```bash
  npm run lint  # if configured
  ```

### TypeScript
- Strict mode enabled
- No `any` types (unless existing code uses them)
- Use explicit types for function parameters and returns

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting (no code change) |
| `refactor` | Code restructure |
| `test` | Adding tests |
| `chore` | Maintenance |

### Examples

```bash
feat: add glance view mode
fix: correct story filtering logic
docs: update deployment guide
chore: update dependencies
```

## Pull Request Process

### Before Submitting

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feat/your-feature-name
   ```

3. **Make your changes**
   - Follow code style guidelines
   - Add types for new functions
   - Update relevant documentation

4. **Run checks**
   ```bash
   npm run check    # TypeScript
   npm run build    # Production build
   ```

5. **Commit** using conventional commits format

### Submitting PR

1. Push your branch
2. Open pull request on GitHub
3. Fill out PR template:
   ```markdown
   ## Summary
   Brief description of changes

   ## Testing
   How was this tested?

   ## Screenshots (if UI change)
   ```

### PR Requirements

- [ ] Code follows style guidelines
- [ ] TypeScript compiles without errors
- [ ] Build succeeds
- [ ] PR description is clear
- [ ] Commits follow conventional format

## Testing Approach

### Manual Testing

Test across:
- Different browsers (Chrome, Firefox, Safari)
- Mobile viewport (375px)
- Dark/light mode toggle
- All three view modes
- Source filtering

### PWA Testing

1. Install as app (Add to Home Screen)
2. Test offline mode (airplane mode)
3. Verify theme persistence

## Project Structure

```
ai-digest-reader/
├── docs/                    # Documentation
├── public/                  # Static assets
│   └── data/
│       └── digest.json      # Generated data
├── scripts/
│   └── generate_json.py    # Data generator
├── src/
│   ├── components/         # Astro components
│   ├── layouts/            # Page layouts
│   ├── lib/                # Utilities (state, digest)
│   ├── pages/              # Routes
│   ├── styles/             # Global CSS
│   └── types.ts            # TypeScript types
├── package.json
├── astro.config.mjs
├── tailwind.config.mjs
└── tsconfig.json
```

## Questions

Open an issue for:
- Bug reports
- Feature requests
- Documentation improvements
