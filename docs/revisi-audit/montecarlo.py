#!/usr/bin/env python3
"""
Monte Carlo reproduction + SVG visuals for the Maya ChargeHub audit paper.
Pure stdlib (no numpy/matplotlib) so it runs in the restricted sandbox.

Model (audit paper, Table 1 + Eq 1-3):
  pi  = s*(T-c)*q + alpha*A - n          (monthly contribution / unit, IDR)
  CFt = 12*ubar_t*pi - F - k*du_t        (annual cash flow, year t; expansion from y2)
  NPV = -I0 + sum CFt/(1+r)^t
Reference path units (year-end): 100, 300, 1500, 1500, 3000
Average units in service:        50, 200, 900, 1500, 2250
"""
import random, math, statistics

SEED = 20261019
random.seed(SEED)
N = 10_000

# ---- reference inputs (Table 1) ; money in IDR ----
I0 = 2_169_300_000          # initial investment
F0 = 2_714_800_000          # fixed opex / year
k0 = 13_593_000             # capex per unit
T0, c0, q0 = 4000.0, 3000.0, 150.0
s = 0.70
A0 = 2_370_000              # advertising+data / unit / month
n0 = 361_000                # non-energy cost / unit / month
r0 = 0.10

YEAR_END = [100, 300, 1500, 1500, 3000]
def avg_units(path):
    prev = 0; out = []
    for u in path:
        out.append((prev + u) / 2.0); prev = u
    return out
def added(path):
    prev = 0; out = []
    for u in path:
        out.append(max(u - prev, 0)); prev = u
    return out

def npv(alpha, T, c, q, A, n, F, k, r, path):
    ubar = avg_units(path); du = added(path)
    pi = s*(T-c)*q + alpha*A - n          # per unit per month
    tot = -I0
    for t in range(1, 6):
        cf = 12*ubar[t-1]*pi - F - (k*du[t-1] if t >= 2 else 0)
        tot += cf / (1+r)**t
    return tot

def tri(lo, mode, hi):
    return random.triangular(lo, hi, mode)

# ---- reference NPV at full ads (sanity vs paper's 44.31 B) ----
ref_full = npv(1.0, T0, c0, q0, A0, n0, F0, k0, r0, YEAR_END)
ref_zero = npv(0.0, T0, c0, q0, A0, n0, F0, k0, r0, YEAR_END)
print(f"NPV alpha=1 : {ref_full/1e9:+.2f} B  (paper +44.31)")
print(f"NPV alpha=0 : {ref_zero/1e9:+.2f} B  (paper -49.79)")

# break-even alpha* via bisection
def npv_alpha(a): return npv(a, T0,c0,q0,A0,n0,F0,k0,r0,YEAR_END)
lo, hi = 0.0, 1.0
for _ in range(60):
    mid = (lo+hi)/2
    if npv_alpha(mid) < 0: lo = mid
    else: hi = mid
astar = (lo+hi)/2
print(f"break-even alpha* : {astar:.3f}  (paper ~0.53)")

# ---- Monte Carlo ----
npvs, alphas = [], []
inputs = {k_: [] for k_ in ["alpha","q","T","c","k","F","n","r","roll"]}
for _ in range(N):
    alpha = random.uniform(0, 1)
    q = tri(105, 150, 195)
    T = tri(2800, 4000, 5200)
    c = tri(2100, 3000, 3900)
    k = tri(9.515e6, 13.593e6, 17.671e6)
    F = tri(1.9004e9, 2.7148e9, 3.5292e9)
    n = tri(252_700, 361_000, 469_300)
    r = random.uniform(0.0575, 0.15)
    roll = random.uniform(0.7, 1.3)
    path = [u*roll for u in YEAR_END]
    val = npv(alpha, T, c, q, A0, n, F, k, r, path)
    npvs.append(val); alphas.append(alpha)
    inputs["alpha"].append(alpha); inputs["q"].append(q); inputs["T"].append(T)
    inputs["c"].append(c); inputs["k"].append(k); inputs["F"].append(F)
    inputs["n"].append(n); inputs["r"].append(r); inputs["roll"].append(roll)

pos = sum(1 for v in npvs if v > 0) / N
med = statistics.median(npvs)
sv = sorted(npvs)
p5, p95 = sv[int(0.05*N)], sv[int(0.95*N)]
print(f"P(NPV>0)   : {pos*100:.0f}%  (paper ~38%)")
print(f"median NPV : {med/1e9:+.1f} B  (paper ~-7.3)")
print(f"5-95 pct   : {p5/1e9:+.1f} .. {p95/1e9:+.1f} B  (paper -35.9 .. +23.2)")

# Spearman rank correlation of each input vs NPV
def spearman(x, y):
    def ranks(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        rk = [0]*len(a)
        for pos_, idx in enumerate(order): rk[idx] = pos_
        return rk
    rx, ry = ranks(x), ranks(y)
    mx = sum(rx)/len(rx); my = sum(ry)/len(ry)
    num = sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    den = math.sqrt(sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))
    return num/den if den else 0
corr = {k_: spearman(inputs[k_], npvs) for k_ in inputs}
print("rank corr:", {k_: round(v,2) for k_,v in sorted(corr.items(), key=lambda kv:-abs(kv[1]))})

# ================= SVG helpers =================
W, H = 760, 460
PAD_L, PAD_R, PAD_T, PAD_B = 70, 24, 46, 54
PX, PY = W-PAD_L-PAD_R, H-PAD_T-PAD_B
NAVY, ORANGE, GREY, AXIS = "#1f4e79", "#c55a11", "#9aa0a6", "#444"

def frame(title, xlab, ylab):
    s_ = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
          f'viewBox="0 0 {W} {H}" font-family="Segoe UI,Helvetica,Arial,sans-serif">',
          f'<rect width="{W}" height="{H}" fill="white"/>',
          f'<text x="{W/2}" y="26" font-size="17" font-weight="700" text-anchor="middle" fill="#222">{title}</text>',
          f'<rect x="{PAD_L}" y="{PAD_T}" width="{PX}" height="{PY}" fill="none" stroke="{AXIS}" stroke-width="1"/>',
          f'<text x="{PAD_L+PX/2}" y="{H-14}" font-size="13" text-anchor="middle" fill="{AXIS}">{xlab}</text>',
          f'<text x="18" y="{PAD_T+PY/2}" font-size="13" text-anchor="middle" fill="{AXIS}" '
          f'transform="rotate(-90 18 {PAD_T+PY/2})">{ylab}</text>']
    return s_

def sx(v, lo, hi): return PAD_L + (v-lo)/(hi-lo)*PX
def sy(v, lo, hi): return PAD_T + PY - (v-lo)/(hi-lo)*PY

def write(name, parts):
    parts.append("</svg>")
    with open(name, "w") as f: f.write("\n".join(parts))
    print("wrote", name)

# ---------- 1) histogram of NPV ----------
def hist():
    lo, hi = min(npvs)/1e9, max(npvs)/1e9
    nb = 40; bw = (hi-lo)/nb
    counts = [0]*nb
    for v in npvs:
        b = min(int((v/1e9-lo)/bw), nb-1); counts[b]+=1
    cmax = max(counts)
    s_ = frame("Monte Carlo distribution of NPV (10,000 draws)",
               "NPV (IDR billion)", "Frequency")
    # zero line
    zx = sx(0, lo, hi)
    s_.append(f'<line x1="{zx:.1f}" y1="{PAD_T}" x2="{zx:.1f}" y2="{PAD_T+PY}" stroke="{ORANGE}" stroke-width="1.4" stroke-dasharray="5,4"/>')
    s_.append(f'<text x="{zx+4:.1f}" y="{PAD_T+14}" font-size="11" fill="{ORANGE}">NPV = 0</text>')
    for i,cnt in enumerate(counts):
        x0 = sx(lo+i*bw, lo, hi); x1 = sx(lo+(i+1)*bw, lo, hi)
        h = cnt/cmax*PY; y0 = PAD_T+PY-h
        col = NAVY if (lo+(i+0.5)*bw)>0 else GREY
        s_.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{max(x1-x0-0.6,0.6):.1f}" height="{h:.1f}" fill="{col}"/>')
    # x ticks
    for t in range(-60, 61, 20):
        if lo<=t<=hi:
            x=sx(t,lo,hi); s_.append(f'<line x1="{x:.1f}" y1="{PAD_T+PY}" x2="{x:.1f}" y2="{PAD_T+PY+5}" stroke="{AXIS}"/>')
            s_.append(f'<text x="{x:.1f}" y="{PAD_T+PY+20}" font-size="11" text-anchor="middle" fill="{AXIS}">{t}</text>')
    # median + stats box
    mx = sx(med/1e9, lo, hi)
    s_.append(f'<line x1="{mx:.1f}" y1="{PAD_T}" x2="{mx:.1f}" y2="{PAD_T+PY}" stroke="#222" stroke-width="1" stroke-dasharray="2,3"/>')
    box = [f"P(NPV&gt;0) = {pos*100:.0f}%", f"median = {med/1e9:+.1f} B",
           f"P5..P95 = {p5/1e9:+.0f}..{p95/1e9:+.0f} B"]
    for j,txt in enumerate(box):
        s_.append(f'<text x="{PAD_L+10}" y="{PAD_T+18+j*16}" font-size="12" fill="#222">{txt}</text>')
    write("mc_histogram.svg", s_)

# ---------- 2) NPV vs alpha scatter ----------
def scatter():
    lo, hi = -60, 60
    s_ = frame("NPV versus advertising realization share (alpha)",
               "Advertising realization share  alpha", "NPV (IDR billion)")
    zy = sy(0, lo, hi)
    s_.append(f'<line x1="{PAD_L}" y1="{zy:.1f}" x2="{PAD_L+PX}" y2="{zy:.1f}" stroke="{AXIS}" stroke-width="1"/>')
    ax = sx(astar, 0, 1)
    s_.append(f'<line x1="{ax:.1f}" y1="{PAD_T}" x2="{ax:.1f}" y2="{PAD_T+PY}" stroke="{ORANGE}" stroke-width="1.4" stroke-dasharray="5,4"/>')
    s_.append(f'<text x="{ax+4:.1f}" y="{PAD_T+14}" font-size="11" fill="{ORANGE}">alpha* = {astar:.2f}</text>')
    step = max(1, N//2500)
    for i in range(0, N, step):
        a = alphas[i]; v = npvs[i]/1e9
        if v<lo or v>hi: continue
        col = NAVY if v>0 else GREY
        s_.append(f'<circle cx="{sx(a,0,1):.1f}" cy="{sy(v,lo,hi):.1f}" r="1.3" fill="{col}" fill-opacity="0.45"/>')
    for t in (0,0.25,0.5,0.75,1.0):
        x=sx(t,0,1); s_.append(f'<line x1="{x:.1f}" y1="{PAD_T+PY}" x2="{x:.1f}" y2="{PAD_T+PY+5}" stroke="{AXIS}"/>')
        s_.append(f'<text x="{x:.1f}" y="{PAD_T+PY+20}" font-size="11" text-anchor="middle" fill="{AXIS}">{t:g}</text>')
    for t in range(-60,61,20):
        y=sy(t,lo,hi); s_.append(f'<line x1="{PAD_L-5}" y1="{y:.1f}" x2="{PAD_L}" y2="{y:.1f}" stroke="{AXIS}"/>')
        s_.append(f'<text x="{PAD_L-9}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="{AXIS}">{t}</text>')
    write("mc_npv_vs_alpha.svg", s_)

# ---------- 3) tornado (rank corr) ----------
def tornado():
    labels = {"alpha":"Advertising realization","roll":"Unit rollout","r":"Discount rate",
              "k":"Capital cost / unit","T":"Retail tariff","n":"Non-energy cost / unit",
              "c":"Electricity cost","F":"Fixed operating cost","q":"Energy sold / unit"}
    items = sorted(((labels[k_], corr[k_]) for k_ in labels), key=lambda kv: abs(kv[1]))
    s_ = frame("Monte Carlo driver ranking (Spearman rank correlation with NPV)",
               "Rank correlation with NPV", "")
    cx = sx(0, -1, 1)
    s_.append(f'<line x1="{cx:.1f}" y1="{PAD_T}" x2="{cx:.1f}" y2="{PAD_T+PY}" stroke="{AXIS}"/>')
    bh = PY/len(items)*0.6
    for i,(lab,val) in enumerate(items):
        yc = PAD_T + PY - (i+0.5)*(PY/len(items))
        x1 = sx(val,-1,1)
        col = NAVY if val>=0 else ORANGE
        xa, wdt = (cx, x1-cx) if val>=0 else (x1, cx-x1)
        s_.append(f'<rect x="{xa:.1f}" y="{yc-bh/2:.1f}" width="{abs(wdt):.1f}" height="{bh:.1f}" fill="{col}"/>')
        s_.append(f'<text x="{PAD_L-6}" y="{yc+4:.1f}" font-size="11" text-anchor="end" fill="#222">{lab}</text>')
        tx = x1 + (6 if val>=0 else -6)
        anc = "start" if val>=0 else "end"
        s_.append(f'<text x="{tx:.1f}" y="{yc+4:.1f}" font-size="11" text-anchor="{anc}" fill="#222">{val:.2f}</text>')
    for t in (-1,-0.5,0,0.5,1):
        x=sx(t,-1,1); s_.append(f'<line x1="{x:.1f}" y1="{PAD_T+PY}" x2="{x:.1f}" y2="{PAD_T+PY+5}" stroke="{AXIS}"/>')
        s_.append(f'<text x="{x:.1f}" y="{PAD_T+PY+20}" font-size="11" text-anchor="middle" fill="{AXIS}">{t:g}</text>')
    write("mc_tornado.svg", s_)

# ---------- 4) P(NPV>0) conditional on alpha ----------
def conditional():
    nb=10; buck=[[0,0] for _ in range(nb)]
    for a,v in zip(alphas,npvs):
        b=min(int(a*nb),nb-1); buck[b][0]+=1; buck[b][1]+= (1 if v>0 else 0)
    s_ = frame("Probability of positive NPV conditional on alpha",
               "Advertising realization share  alpha (bin)", "P(NPV > 0)")
    bw = PX/nb
    for i,(tot,p) in enumerate(buck):
        frac = p/tot if tot else 0
        x0 = PAD_L + i*bw; h = frac*PY
        col = NAVY if (i+0.5)/nb>=astar else GREY
        s_.append(f'<rect x="{x0+3:.1f}" y="{PAD_T+PY-h:.1f}" width="{bw-6:.1f}" height="{h:.1f}" fill="{col}"/>')
        s_.append(f'<text x="{x0+bw/2:.1f}" y="{PAD_T+PY-h-5:.1f}" font-size="10" text-anchor="middle" fill="#222">{frac*100:.0f}%</text>')
    ax = sx(astar,0,1)
    s_.append(f'<line x1="{ax:.1f}" y1="{PAD_T}" x2="{ax:.1f}" y2="{PAD_T+PY}" stroke="{ORANGE}" stroke-width="1.4" stroke-dasharray="5,4"/>')
    s_.append(f'<text x="{ax+4:.1f}" y="{PAD_T+14}" font-size="11" fill="{ORANGE}">break-even alpha* = {astar:.2f}</text>')
    for t in (0,0.25,0.5,0.75,1.0):
        x=sx(t,0,1); s_.append(f'<text x="{x:.1f}" y="{PAD_T+PY+20}" font-size="11" text-anchor="middle" fill="{AXIS}">{t:g}</text>')
    for t in (0,0.25,0.5,0.75,1.0):
        y=sy(t,0,1); s_.append(f'<text x="{PAD_L-9}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="{AXIS}">{t:g}</text>')
    write("mc_conditional.svg", s_)

hist(); scatter(); tornado(); conditional()
print("DONE")


# ---- self-check: deterministic spine must match the paper's published figures ----
# (ponytail: only the deterministic anchors are asserted; the MC spread uses
#  reconstructed distribution params and is NOT checked against 38%/-7.3B here.)
def _selfcheck():
    assert abs(ref_full/1e9 - 44.31) < 0.05, ref_full
    assert abs(ref_zero/1e9 + 49.79) < 0.05, ref_zero
    assert abs(astar - 0.53) < 0.01, astar
    assert corr["alpha"] > 0.90 and all(abs(v) < 0.2 for k_, v in corr.items() if k_ != "alpha")
    print("selfcheck OK")

if __name__ == "__main__":
    _selfcheck()
