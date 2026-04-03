# MiniBench Sprint 1 — UI/UX Overhaul

## Problem
Current MiniBench frontend is functional but looks like AI-generated slop. Generic dark theme, no personality, no visual hierarchy, standard Recharts defaults. It needs to feel like a product people bookmark, not a school project.

## What Exists
- React + Vite + Tailwind + Recharts + Lucide icons
- 5 pages: Dashboard, Leaderboard, Compare, Hardware, Submit
- FastAPI backend at :3070 with full REST API
- 10 hardware specs, 8 benchmarks, 7 models in seed data
- GitHub: RaapTechllc/minibench, deployed on DVM at :3071

## Sprint 1 Scope: Dashboard + Leaderboard Polish
Focus on the two most-viewed pages. Do NOT touch backend/API.

### Dashboard Requirements
1. **Hero stat strip** — Replace generic StatCards with a purposeful top section. Show the #1 system name + t/s prominently. Show total submissions, unique systems, best HEI. Use color to create hierarchy (primary metric cyan, secondary gray).
2. **Efficiency Frontier chart** — Keep scatter plot but: add hover crosshairs, size dots by RAM, add a visible Pareto line (not invisible shape hack), label the #1 and #2 points directly on the chart.
3. **Bandwidth vs Throughput chart** — Add a trend line (linear regression). Show R² value. This proves the thesis ("memory bandwidth is king").
4. **Recent submissions table** — Add alternating row shading. Add a "View" link per row. Truncate long model names. Show relative time ("2h ago" not raw dates).
5. **Remove generic subtitle** — "Crowdsourced LLM benchmarks for Mini PCs. Memory bandwidth is king." is boring. Replace with something that hooks: show the actual top stat inline.

### Leaderboard Requirements
1. **Medal treatment for top 3** — Gold/Silver/Bronze visual indicators (not just numbers).
2. **HEI column emphasis** — HEI is the key metric. Make it the visual anchor of each row.
3. **Sticky header** — Table header should stick on scroll.
4. **System badges** — Color-coded system type badges (Apple=blue, AMD=red, Intel=blue, NVIDIA=green, ARM=purple).
5. **Sparkline or bar** — Inline t/s bar visualization in each row for quick visual comparison.

### Global Requirements
1. **No purple gradients, no glass morphism, no generic hero sections.**
2. **Utility-first design** — Every pixel serves a purpose. Data density over decoration.
3. **Mobile responsive** — Tables must work on mobile (horizontal scroll OK, but header visible).
4. **Keep existing nav** — Don't change App.tsx nav structure.
5. **Performance** — No new dependencies over 50KB. Recharts is already heavy enough.

## Tech Stack
- React 18 + TypeScript
- Tailwind CSS (v4, @import "tailwindcss" style)
- Recharts for charts
- Lucide for icons
- No new UI libraries (no Shadcn, no MUI, no Radix)

## Files to Modify
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Leaderboard.tsx`
- `frontend/src/components/StatCard.tsx` (or replace)
- `frontend/src/components/BandwidthBadge.tsx` (keep)
- New components OK if small and purposeful

## Files NOT to Touch
- `backend/` — nothing
- `frontend/src/App.tsx` — nav stays as-is
- `frontend/src/api.ts` — no API changes
- `docker-compose.yml` — no infra changes

## Anti-Slop Checklist
- [ ] No emoji in headings
- [ ] No "Welcome to..." or "Your one-stop..."
- [ ] No decorative gradients that don't encode data
- [ ] No cards with only 1 piece of information
- [ ] No placeholder images or illustrations
- [ ] Every chart axis is labeled and has units
- [ ] Colors encode meaning (system type, performance tier), not decoration
- [ ] Table rows are scannable in <2 seconds
