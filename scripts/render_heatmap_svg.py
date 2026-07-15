#!/usr/bin/env python3
import datetime, json, os, random

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, '..', 'data', 'contributions.json')
OUT_PATH = os.path.join(HERE, '..', 'contrib-heatmap.svg')

PALETTE = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353', '#69f0a0']
CELL, GAP = 12, 3
STEP = CELL + GAP
PAD, LEFT_LABEL_W, TOP_LABEL_H, TITLEBAR_H = 22, 30, 20, 30
BG, BG2 = '#0a0e14', '#0d1420'
FRAME, MUTED, TEXT = '#1f6feb', '#7d8590', '#e6edf3'
ACCENT, GREEN, GOLD = '#22d3ee', '#39d353', '#f2cc60'
SNAKE_STEP = 0.08
SNAKE_LEN = 5


def level_for(c):
    if c == 0: return 0
    if c <= 5: return 1
    if c <= 15: return 2
    if c <= 30: return 3
    if c <= 50: return 4
    return 5


def build_grid(days):
    first = datetime.date.fromisoformat(days[0]['date'])
    lead_pad = (first.weekday() + 1) % 7
    grid, col = [], [None] * lead_pad
    for d in days:
        date = datetime.date.fromisoformat(d['date'])
        wd = (date.weekday() + 1) % 7
        while len(col) < wd: col.append(None)
        col.append((d['date'], d['count'], level_for(d['count'])))
        if len(col) == 7: grid.append(col); col = []
    if col:
        while len(col) < 7: col.append(None)
        grid.append(col)
    return grid


def random_walk(n_cols, n_rows, seed):
    rng = random.Random(seed)
    total = n_cols * n_rows
    def neighbors(c, r):
        out = []
        if c > 0: out.append((c-1, r))
        if c < n_cols-1: out.append((c+1, r))
        if r > 0: out.append((c, r-1))
        if r < n_rows-1: out.append((c, r+1))
        return out
    for attempt in range(100):
        visited = set()
        start = (0, 0)
        path = [start]
        visited.add(start)
        while len(path) < total:
            cx, cy = path[-1]
            nbrs = [(c, r) for c, r in neighbors(cx, cy) if (c, r) not in visited]
            if not nbrs: break
            nbrs.sort(key=lambda p: len([(c,r) for c,r in neighbors(p[0],p[1]) if (c,r) not in visited]))
            if len(nbrs) > 1 and rng.random() < 0.3:
                pick = rng.choice(nbrs[:2])
            else:
                pick = nbrs[0]
            path.append(pick)
            visited.add(pick)
        if len(path) >= total * 0.95:
            path.append((0, 0))
            return path
    path = [(0, 0)]
    visited = {(0, 0)}
    for _ in range(total * 3):
        cx, cy = path[-1]
        nbrs = neighbors(cx, cy)
        fresh = [p for p in nbrs if p not in visited]
        if fresh: pos = rng.choice(fresh)
        else: pos = rng.choice(nbrs)
        path.append(pos)
        visited.add(pos)
        if len(visited) >= total: break
    path.append((0, 0))
    return path


def render(data):
    days = data['days']
    grid = build_grid(days)
    n_cols, n_rows = len(grid), 7
    art_w, art_h = n_cols * STEP, n_rows * STEP
    month_labels, seen_months = [], set()
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None: continue
            date = datetime.date.fromisoformat(cell[0])
            key = (date.year, date.month)
            if key not in seen_months and date.day <= 7:
                seen_months.add(key)
                month_labels.append((ci, date.strftime('%b')))
            break
    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + 88 + PAD
    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W
    snake_path = random_walk(n_cols, n_rows, data['range']['end'])
    total_steps = len(snake_path)
    total_time = total_steps * SNAKE_STEP
    first_visit = {}
    for si, (ci, ri) in enumerate(snake_path):
        if (ci, ri) not in first_visit:
            first_visit[(ci, ri)] = si * SNAKE_STEP
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
        f'<defs><linearGradient id="hbg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
        f'<rect width="{canvas_w}" height="{canvas_h}" rx="12" fill="url(#hbg)"/>',
        f'<rect x=".5" y=".5" width="{canvas_w-1}" height="{canvas_h-1}" rx="12" fill="none" stroke="{FRAME}" stroke-opacity=".55"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-opacity=".35"/>',
    ]
    for i, dc in enumerate(['#ff5f56','#ffbd2e','#27c93f']):
        parts.append(f'<circle cx="{PAD+i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dc}"/>')
    parts.append(f'<text x="{canvas_w/2}" y="{TITLEBAR_H/2+4}" fill="{MUTED}" font-size="12" text-anchor="middle">gabriel@github: ~/contributions --graph</text>')
    for ci, label in month_labels:
        parts.append(f'<text x="{grid_left+ci*STEP}" y="{TITLEBAR_H+14}" fill="{MUTED}" font-size="10">{label}</text>')
    for wi, wn in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:
        parts.append(f'<text x="{PAD}" y="{grid_top+wi*STEP+CELL*.78:.1f}" fill="{MUTED}" font-size="9">{wn}</text>')
    RESTORE_PAUSE = 1.0
    loop_time = total_time + RESTORE_PAUSE
    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        for ri, cell in enumerate(column):
            if cell is None: continue
            ds, cnt, lvl = cell
            gy = grid_top + ri * STEP
            pl = 's' if cnt != 1 else ''
            eaten = ''
            t = first_visit.get((ci, ri))
            if lvl > 0 and t is not None:
                ke = max(0.0001, t / loop_time)
                kb = (total_time + RESTORE_PAUSE * 0.6) / loop_time
                eaten = f'<animate attributeName="fill" values="{PALETTE[lvl]};{PALETTE[0]};{PALETTE[0]};{PALETTE[lvl]}" keyTimes="0;{ke:.4f};{kb:.4f};1" calcMode="discrete" dur="{loop_time:.2f}s" repeatCount="indefinite"/>'
            parts.append(f'<rect x="{gx}" y="{gy}" width="{CELL}" height="{CELL}" rx="2.5" fill="{PALETTE[lvl]}"><title>{ds}: {cnt} contribution{pl}</title>{eaten}</rect>')
    def values_for(offset):
        pts = []
        for si in range(total_steps):
            idx = max(0, si - offset)
            c2, r2 = snake_path[idx]
            pts.append(f'{grid_left+c2*STEP+CELL/2:.1f},{grid_top+r2*STEP+CELL/2:.1f}')
        c2, r2 = snake_path[0]
        pts.append(f'{grid_left+c2*STEP+CELL/2:.1f},{grid_top+r2*STEP+CELL/2:.1f}')
        return ';'.join(pts)
    kts = [i*SNAKE_STEP/loop_time for i in range(total_steps)] + [1.0]
    key_times = ';'.join(f'{k:.5f}' for k in kts)
    snake_cols = ['#39d353','#2eaa47','#22803a','#186a2f','#125425']
    for seg in range(SNAKE_LEN, -1, -1):
        vals = values_for(seg)
        if seg == 0: col, r = '#e6ffec', CELL/2+1
        else:
            col = snake_cols[min(seg-1, len(snake_cols)-1)]
            r = max(2.5, CELL/2-(seg-1)*0.9)
        parts.append(f'<rect x="{-r:.1f}" y="{-r:.1f}" width="{2*r:.1f}" height="{2*r:.1f}" rx="{r*.5:.1f}" fill="{col}"><animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{key_times}" dur="{loop_time:.2f}s" calcMode="linear" repeatCount="indefinite"/></rect>')
    leg_y = grid_top + art_h + 6
    leg_x = canvas_w - PAD - (len(PALETTE)*(CELL-1)+70)
    parts.append(f'<text x="{leg_x}" y="{leg_y+CELL*.8:.1f}" fill="{MUTED}" font-size="10" text-anchor="end">Less</text>')
    lx = leg_x + 8
    for lvl, color in enumerate(PALETTE):
        parts.append(f'<rect x="{lx}" y="{leg_y}" width="{CELL-1}" height="{CELL-1}" rx="2.2" fill="{color}"/>')
        lx += CELL
    parts.append(f'<text x="{lx+4}" y="{leg_y+CELL*.8:.1f}" fill="{MUTED}" font-size="10">More</text>')
    sep_y = leg_y + CELL + 14
    parts.append(f'<line x1="0" y1="{sep_y}" x2="{canvas_w}" y2="{sep_y}" stroke="{FRAME}" stroke-opacity=".25"/>')
    cs = data['current_streak']['length']
    ls = data['longest_streak']['length']
    tc = data['total_contributions']
    best = data['best_day']
    rng = data['range']
    ly = sep_y + 24
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{GREEN}"><tspan font-weight="700">{tc:,}</tspan><tspan fill="{MUTED}"> contributions in the last year</tspan></text>')
    parts.append(f'<text x="{canvas_w-PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">{rng["start"]} to {rng["end"]}</text>')
    ly += 24
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{MUTED}">current streak <tspan fill="{ACCENT}" font-weight="700">{cs} days</tspan><tspan fill="{MUTED}">   |   longest </tspan><tspan fill="{ACCENT}" font-weight="700">{ls} days</tspan></text>')
    parts.append(f'<text x="{canvas_w-PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">best day <tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> on {best["date"]}</text>')
    parts.append('</svg>')
    return ''.join(parts)


if __name__ == '__main__':
    data = json.load(open(IN_PATH))
    svg = render(data)
    with open(OUT_PATH, 'w') as f: f.write(svg)
    print(f'wrote {OUT_PATH} ({len(svg)} bytes)')
