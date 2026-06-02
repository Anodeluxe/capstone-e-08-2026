# Design

> Auto-generated and maintained by frontend-god-mode.
> Source of truth for typography, color, motion, layout, and component tokens.
> Read this BEFORE touching the UI in any subsequent session.

## Aesthetic direction

Precision Industrial — water monitoring control panel; deep slate palette with a single cyan-teal accent, monospace data readouts, engineer-trusted hierarchy. Clean without being cold.

## Dials

- DESIGN_VARIANCE: 4 / 10
- MOTION_INTENSITY: 2 / 10
- VISUAL_DENSITY: 5 / 10

## Type stack

- Display + Body: Geist (weights 400–700, variable `--font-sans`)
- Mono: Geist Mono (variable `--font-mono`) — **mandatory on all data values** (pH, scores, timestamps, tabular numbers)
- Loaded via: `next/font/google` in `app/layout.tsx`
- `tabular-nums` + `font-mono` on every metric value

Banned in this project: Inter (regular), Roboto, Arial, system-ui, any serif on dashboards.

## Color tokens (OKLCH)

```css
/* Light */
--background: oklch(0.98 0.006 220);   /* cool off-white, slate tint */
--foreground: oklch(0.13 0.012 220);   /* near-black, matched tint */
--card:       oklch(1.00 0.004 220);
--muted:      oklch(0.94 0.008 220);
--muted-foreground: oklch(0.52 0.012 220);
--border:     oklch(0.91 0.008 220);
--primary:    oklch(0.52 0.16 195);    /* cyan-teal accent */

/* Dark */
--background: oklch(0.13 0.010 220);
--foreground: oklch(0.97 0.005 220);
--card:       oklch(0.17 0.010 220);
--border:     oklch(0.24 0.010 220);
--primary:    oklch(0.72 0.16 195);    /* brighter cyan in dark */
```

**One accent rule**: `--primary` (cyan-teal) is the only accent. No purple, no blue gradients.

Banned: pure `#000`/`#FFF`, purple-to-blue gradients, gray family (use Slate/Zinc only and stay consistent).

## Chart / sensor colors

These map semantically to sensor parameters — do not rearrange:

| Sensor      | Color (light)       | Hex         |
|-------------|---------------------|-------------|
| pH          | cyan `chart-1`      | `#0891b2`   |
| Turbiditas  | amber `chart-3`     | `#d97706`   |
| TDS         | emerald `chart-2`   | `#059669`   |
| Suhu        | rose `chart-4`      | `#f43f5e`   |
| Level Air   | indigo `chart-5`    | `#6366f1`   |
| Trend/Score | cyan                | `#0891b2`   |

## Status colors

- Success / open / good: `text-emerald-600 dark:text-emerald-400`
- Warning / threshold: `text-amber-600 dark:text-amber-400`
- Danger / anomaly / closed: `text-rose-600 dark:text-rose-400`
- Never use raw `text-green-*`, `text-red-*`, or `text-yellow-*`

## Shadows

Tinted toward bg hue (220°). No pure-black drops:

```
0 4px 20px -8px oklch(0.4 0.1 220 / 0.12)   /* score cards */
0 2px 12px -4px oklch(0.4 0.1 220 / 0.08)   /* tables, charts, metric cards */
```

## Layout

- Container: `max-w-7xl mx-auto px-4`
- Page header pattern: `h1 text-xl font-semibold tracking-tight` + `p text-sm text-muted-foreground`
- Section labels: `text-xs font-medium text-muted-foreground uppercase tracking-widest mb-3`
- Tables: `bg-card`, header `bg-muted/50`, rows `hover:bg-muted/40`, borders `border-border/60`
- Cards: `rounded-xl border border-border bg-card` + tinted shadow
- No `h-screen` anywhere — use `min-h-[100dvh]`

## Navigation

- Wordmark: `Toren<span class="text-primary">.</span>` with Waves icon
- Active link: `bg-primary/10 text-primary font-medium`
- Inactive: `text-muted-foreground hover:text-foreground hover:bg-secondary`
- Status dot: emerald (connected) / amber pulse (connecting) / rose (disconnected)
- `sticky top-0 z-40 bg-background/90 backdrop-blur-md border-b border-border/60`

## Component inventory

shadcn: Button, Dialog
recharts: LineChart (SensorChart), AreaChart (TrendChart)
lucide-react: nav icons — Waves, Gauge, Activity, Droplets, TrendingUp, X
Custom: SensorScoreCard (SVG arc), SystemStatus (flat status row), AlertBanner

## Project-specific bans

- No `bg-white dark:bg-zinc-900` — use `bg-card`
- No `text-zinc-500` — use `text-muted-foreground`
- No `text-zinc-*` hardcoded — use semantic tokens
- No `text-green-*` / `text-red-*` / `text-yellow-*` for status — use emerald/rose/amber
- No emojis (lucide icons only)
- No `shadow-sm` with pure black — use tinted shadow above

## Last updated

2026-06-02 — initial design system: slate+cyan tokens, Geist Mono, nav redesign, full semantic token sweep across all 12 components/pages
