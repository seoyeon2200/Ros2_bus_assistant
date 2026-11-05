#!/usr/bin/env python3
"""
bus_stop.sdf 월드를 기반으로 Nav2용 occupancy grid 지도 생성
- 해상도: 0.05 m/pixel
- 범위: x[-10, 10], y[-10, 10] → 400×400 pixels
- 0 = 점유(장애물), 254 = 자유 공간
"""
import struct
import os

RESOLUTION = 0.05
ORIGIN_X = -10.0
ORIGIN_Y = -10.0
WIDTH  = 400
HEIGHT = 400
FREE = 254
OCCUPIED = 0

grid = [[FREE] * WIDTH for _ in range(HEIGHT)]


def col(wx):
    return int((wx - ORIGIN_X) / RESOLUTION)

def row(wy):
    return HEIGHT - 1 - int((wy - ORIGIN_Y) / RESOLUTION)


def mark_box(x_min, x_max, y_min, y_max, pad=0.08):
    x_min -= pad; x_max += pad
    y_min -= pad; y_max += pad
    c0 = max(0, col(x_min))
    c1 = min(WIDTH  - 1, col(x_max))
    r0 = max(0, row(y_max))
    r1 = min(HEIGHT - 1, row(y_min))
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            grid[r][c] = OCCUPIED


def mark_cylinder(cx, cy, radius=0.15):
    cr = max(2, int(radius / RESOLUTION) + 1)
    cc = col(cx); rc = row(cy)
    for r in range(max(0, rc - cr), min(HEIGHT, rc + cr + 1)):
        for c in range(max(0, cc - cr), min(WIDTH, cc + cr + 1)):
            grid[r][c] = OCCUPIED


# ── 버스 (4.0 × 2.0 m 박스) — bus_stop.sdf 기준 ──────────────────
# 빨간 버스: center (5.0, -7.5), yaw=π → footprint x[3.0,7.0], y[-8.5,-6.5]
mark_box(3.0, 7.0, -8.5, -6.5)

# 파란 버스: center (5.0, -2.5), yaw=π → footprint x[3.0,7.0], y[-3.5,-1.5]
mark_box(3.0, 7.0, -3.5, -1.5)

# 초록 버스: center (5.0,  2.5), yaw=π → footprint x[3.0,7.0], y[ 1.5, 3.5]
mark_box(3.0, 7.0,  1.5,  3.5)

# 노란 버스: center (5.0,  7.5), yaw=π → footprint x[3.0,7.0], y[ 6.5, 8.5]
mark_box(3.0, 7.0,  6.5,  8.5)

# ── PGM 저장 (P5 binary) ─────────────────────────────────────────
out_dir = os.path.dirname(os.path.abspath(__file__))
pgm_path  = os.path.join(out_dir, 'bus_stop.pgm')
yaml_path = os.path.join(out_dir, 'bus_stop.yaml')

with open(pgm_path, 'wb') as f:
    header = f'P5\n{WIDTH} {HEIGHT}\n255\n'
    f.write(header.encode('ascii'))
    for r in range(HEIGHT):
        f.write(bytes(grid[r]))

# ── YAML 저장 ─────────────────────────────────────────────────────
with open(yaml_path, 'w') as f:
    f.write(f"""image: bus_stop.pgm
resolution: {RESOLUTION}
origin: [{ORIGIN_X}, {ORIGIN_Y}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
""")

print(f"[OK] 지도 생성 완료")
print(f"     PGM : {pgm_path}")
print(f"     YAML: {yaml_path}")
print(f"     크기: {WIDTH}x{HEIGHT} px  ({WIDTH*RESOLUTION:.0f}x{HEIGHT*RESOLUTION:.0f} m)")

