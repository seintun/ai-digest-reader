# Troubleshooting

Common issues and solutions for the AI News Digest Aggregator.

## Claude CLI Issues

### Claude CLI Not Found

**Error:**
```
Error: Claude CLI not found. Please install it first.
```

**Solution:**
```bash
# macOS
brew install anthropic/anthropic/claude

# or via npm
npm install -g @anthropic-ai/claude

# Verify installation
claude --version
```

For other platforms, see [Anthropic Claude Code Setup](https://docs.anthropic.com/en/docs/claude-code/setup).

---

### Authentication Issues

**Error:**
```
Error: Claude CLI authentication failed. Please run `claude auth` first.
```

**Solution:**
```bash
# Authenticate with Anthropic
claude auth

# Follow the prompts to complete authentication
```

If you don't have an Anthropic account:
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Generate an API key
3. Run `claude auth` and enter your API key

---

### API Rate Limits

**Error:**
```
Error: Rate limit exceeded. Please wait and retry.
```

**Solution:**
1. **Wait** - Rate limits typically reset within a minute
2. **Retry with exponential backoff** - The script automatically retries
3. **Use `--no-ai`** to skip AI summaries temporarily:
   ```bash
   python digest.py --no-ai
   ```

**Preventive measures:**
- Generate digests during off-peak hours
- Cache responses locally
- Use `--no-ai` for CI/CD pipelines

**Note:** If `analyzer.py` fails (Claude not installed), the script will continue without AI summary and print a warning.

---

## Summary Generation Failures

### Empty or Missing Summary

**Symptoms:**
- `summary` field is `null` or missing from digest.json
- Summary tabs show "No summary available"

**Possible causes:**
1. Claude CLI not installed or not authenticated
2. API request timed out
3. No stories were fetched (empty digest)

**Solutions:**
```bash
# 1. Verify Claude CLI is working
claude --version
claude auth

# 2. Run with verbose output
python digest.py --no-ai

# 3. Check if stories were fetched
python digest.py --no-ai

# 4. Generate with AI (if Claude CLI installed)
python digest.py
```

---

### Summary Quality Issues

**Symptoms:**
- Summary is too generic or unhelpful
- Missing relevant stories
- Incorrect categorization

**Solution:**
1. Ensure sufficient stories are fetched:
   ```bash
   python digest.py --limit 20
   ```
2. Wait for a day with more activity
3. Check that stories have meaningful titles and scores

---

## Data Fetching Issues

### Reddit API Errors

**Error:**
```
Error: Failed to fetch Reddit posts: 429 Too Many Requests
```

**Solution:**
```bash
# Wait and retry
sleep 60
python digest.py

# Or reduce the number of posts
python digest.py --limit 5
```

Reddit's free API has strict rate limits. The script includes automatic retry with backoff.

---

### Hacker News API Errors

**Error:**
```
Error: Failed to fetch HN stories: Connection timeout
```

**Solution:**
```bash
# Check your internet connection
ping news.ycombinator.com

# Retry
python digest.py
```

HN's Firebase API is generally reliable. Timeouts are usually network-related.

---

### No Stories Found

**Symptoms:**
- Empty arrays in `r` or `h` fields
- "No stories found" warning

**Possible causes:**
1. Network connectivity issues
2. API rate limits
3. Subreddit restrictions
4. Time of day (very early morning = fewer posts)

**Solutions:**
```bash
# Check network
curl https://www.reddit.com/r/ArtificialIntelligence.json

# Try different subreddits
python digest.py --subreddits ChatGPT MachineLearning

# Run during peak hours (typically 9 AM - 11 PM local time)
```

---

## Frontend Issues

### Digest Not Loading

**Symptoms:**
- "Failed to load digest" error
- Blank page

**Solutions:**
1. **Check API endpoint:**
   ```bash
   # Local development
   npm run dev
   
   # Check /api/digest in browser dev tools
   ```

2. **Verify digest.json exists:**
   ```bash
   ls -la ai-digest-reader/public/data/digest.json
   ```

3. **Clear localStorage:**
   - Open browser DevTools
   - Go to Application > Local Storage
   - Clear `digest-data`

---

### Old Data Displayed

**Symptoms:**
- Yesterday's digest shown instead of today's

**Solutions:**
1. **Clear cache and reload:**
   - Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   - Or: DevTools > Network > Disable Cache

2. **Regenerate digest:**
   ```bash
   python digest.py --output-dir ai-digest-reader/public/data/
   ```

3. **Clear localStorage** as described above

---

### Summary Tabs Not Showing

**Symptoms:**
- Summary section missing or empty
- "No summary" message displayed

**Solutions:**
1. **Regenerate with AI:**
   ```bash
   python scripts/generator.py  # Without --no-ai
   ```

2. **Check digest.json version:**
   - Open browser DevTools
   - Check `data.v` is `2`
   - Check `data.summary` exists

3. **Force refresh** after updating digest.json

---

## Deployment Issues

### Vercel Build Fails

**Error:**
```
Error: Build failed. See build log for details.
```

**Solutions:**
1. **Check Node.js version:**
   ```bash
   node --version  # Should be 24.x
   ```

2. **Reinstall dependencies:**
   ```bash
   cd ai-digest-reader
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **Check vercel.json:**
   ```bash
   cat vercel.json
   ```

---

### CORS Errors

**Error:**
```
Access to fetch at 'https://your-domain.vercel.app' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solution:**
The Vercel deployment should include CORS headers. If not:
1. Check the API endpoint includes CORS headers
2. Ensure you're deploying to Vercel, not running locally for production

---

## Getting Help

If you encounter an issue not listed here:

1. Check the [GitHub Issues](https://github.com/your-repo/dailydigest/issues)
2. Run with verbose logging:
   ```bash
   python scripts/generator.py --verbose 2>&1 | tee debug.log
   ```
3. Include the debug log when reporting issues
