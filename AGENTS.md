# AGENTS.md - StockSelector Agent Guidelines

## Build & Run Commands

### Backend
```bash
pip install -r requirements.txt
python app.py           # Flask on http://localhost:5001
```

### Frontend
```bash
cd frontend && pnpm install
pnpm dev             # Vite on http://localhost:5173
pnpm build           # Build for production
```

### CLI Mode
```bash
python main.py --top 30 --min-score 60 --tech-weight 0.7 --fund-weight 0.3
```

## Key Architecture

| Item | Value |
|------|-------|
| Flask port | **5001** (not 5000 - see app.py:321) |
| Frontend path | `frontend/src/` (Vue3 + ElementPlus) |
| Static data | `frontend/public/assets/stocks.json` |
| Stock mapping | `_STOCK_MAPPING` in `data_fetcher.py:19` |
| Package manager | pnpm (uses pnpm-lock.yaml) |

## Data Flow
1. Frontend tries `/assets/stocks.json` (static JSON)
2. Falls back to `/api/cache` → `/api/select`

## Config (`config.json`)
- `top`: number of stocks to return
- `min_score`: minimum score threshold
- `tech_weight` / `fund_weight`: weight allocation
- `max_workers`: ThreadPoolExecutor workers (default: 16)

## Important Notes

1. **AkShare**: External APIs, network failures common - add `time.sleep(0.5)` between calls
2. **First run**: Full market scan takes 5-10 minutes
3. **Multithreading**: selector.py uses `ThreadPoolExecutor` with `max_workers` from config
4. **Cancellation**: Global `stop_flag` in selector.py:22
5. **Output path**: Must save to `frontend/public/assets/stocks.json`
6. **Auto-deploy**: app.py:72-145 runs `npm run build`, commits to main, triggers GitHub Actions (deploys to gh-pages)
7. **CI**: Uses pnpm (workflow file), but auto-build script uses npm

## Code Style (Python)
- snake_case naming
- Imports: stdlib → third-party → local
- Error handling: return empty DataFrame/None on failure
- Logging: print statements only (no logging module)

## What NOT to Do
- Do NOT change JSON output path
- Do NOT remove thread safety (selector.py is multithreaded)
