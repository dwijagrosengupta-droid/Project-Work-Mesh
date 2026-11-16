import csv
import math
import os
import re
import subprocess
import time

import matplotlib
matplotlib.use("Agg")  # save to files; remove this line to show windows and fuk me hard anish i love u
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


#dekh khanki aita toder laptop r location on rakhbi

#and pycharm ke run as adminsitartior korbi first time

#and secondly tora  "netsh wlan show interfaces" ata cmd prompt a run kre tode  wifi dekhte pabi
WIDTH, HEIGHT = 100.0, 60.0          # survey area in metres ar ata just tor bhab tor jaikhane ashish bhab or modhey theke 100*60 grid r nodehy hbe
RSSI_MIN, RSSI_MAX = -100.0, -20.0   # dekh amar icchai data nilam
CELL = 10.0
WEAK_THRESHOLD = -70.0
CSV_FILE = "survey.csv" #ata toder baal r csv file e store hobe
class SurveyPoint:

    def __init__(self, x, y, reading=None, label=""): #ai gulo survey point !
        self.x = self._to_float(x, "x")
        self.y = self._to_float(y, "y")
        if not (0 <= self.x <= WIDTH and 0 <= self.y <= HEIGHT):
            raise ValueError(f"({self.x}, {self.y}) is outside the survey area") #this is my service area bara
        self.reading = self._parse_reading(reading)
        self.label = str(label).strip()

    @staticmethod
    def _to_float(value, name): #dekh ara man jodi bhab mane tor 63*100 tar modehy theke pabe
        try:
            v = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} is missing or not a number: {value!r}")
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"{name} is not finite") #ai dekh value gulos
        return v

    @staticmethod
    def _parse_reading(value): #parse mane holo bhab i magibe kor 1+2 so 1 ke nebe then + ke nebe then 2 then
        if value is None or str(value).strip() == "":
            return float("nan") #ata toder garbage value
        try:
            r = float(value)
        except ValueError:
            raise ValueError(f"reading is not a number: {value!r}") #aint a number !
        if math.isnan(r):
            return r
        if not (RSSI_MIN <= r <= RSSI_MAX):
            raise ValueError(f"reading {r} dBm outside [{RSSI_MIN}, {RSSI_MAX}]") # prct r tor bhab dbm strangtg debe
        return r

    @property
    def has_reading(self): #it has the summary for the valye !
        return not math.isnan(self.reading) #ata constructor

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y) #manhaattan diff ata mane y=abs(y1-y2)+(x2-x1);

    def to_row(self): #tor row gulo te jabe !
        r = "" if not self.has_reading else self.reading
        return [self.label, self.x, self.y, r]

    def __repr__(self):
        return f"SurveyPoint({self.label!r}, x={self.x}, y={self.y}, reading={self.reading})" #baal r survey point nothing else


def save_points(points, path=CSV_FILE): #tor dekh Path ta akta value oi tor csv file r
    with open(path, "w", newline="") as f: #file haneling korechis to 2nd sem 2 then u know
        w = csv.writer(f)
        w.writerow(["label", "x", "y", "rssi_dbm"])
        w.writerows(p.to_row() for p in points)


def load_points(path=CSV_FILE): #load mane bhab matlab oi scatter functio  r moto kichu ta
    points, rejected = [], []
    with open(path, newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            try:
                points.append(SurveyPoint(row.get("x"), row.get("y"),
                                          row.get("rssi_dbm"), row.get("label", "")))
            except ValueError as e:
                rejected.append((line_no, str(e)))
    return points, rejected

def make_sample_data(n=150, seed=42, path=CSV_FILE): #ai function ta toder kaj r nam as ai gulo sample data ! toder ata bujte hobe na
    rng = np.random.default_rng(seed)
    aps = np.array([[20.0, 30.0], [75.0, 20.0]])
    xy = rng.uniform([0, 0], [WIDTH, HEIGHT], size=(n, 2))
    d = np.linalg.norm(xy[:, None, :] - aps[None, :, :], axis=2).min(axis=1)
    rssi = -35 - 25 * np.log10(np.maximum(d, 1.0)) + rng.normal(0, 3, n)
    rssi[(xy[:, 0] > 80) & (xy[:, 1] > 40)] -= 15          # dead corner
    rssi = np.clip(rssi, -95, -30)

    pts = [SurveyPoint(x, y, round(r, 1), f"P{i:03d}")
           for i, ((x, y), r) in enumerate(zip(xy, rssi))]
    for i in rng.choice(n, 8, replace=False):
        pts[i].reading = float("nan")
    save_points(pts, path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(["BAD1", 250, 10, -60])
        w.writerow(["BAD2", 30, 20, -5])
        w.writerow(["BAD3", "", 20, -60])
        w.writerow(["BAD4", 30, 20, "abc"])

def to_arrays(points): #cobvert jirchi np.array as np is fast bbay
    xy = np.array([[p.x, p.y] for p in points])
    rssi = np.array([p.reading for p in points])
    return xy, rssi


def grid_summary(xy, rssi): #grid r joonno i love anish visualzition copy ne akta n*n grid bana then kpr sala
    nx, ny = int(np.ceil(WIDTH / CELL)), int(np.ceil(HEIGHT / CELL))
    ok = ~np.isnan(rssi)
    ix = np.minimum((xy[ok, 0] // CELL).astype(int), nx - 1) #ami remobe korchi nx-1 or dx-1
    iy = np.minimum((xy[ok, 1] // CELL).astype(int), ny - 1)
    total = np.zeros((ny, nx))
    count = np.zeros((ny, nx), dtype=int)
    np.add.at(total, (iy, ix), rssi[ok])
    np.add.at(count, (iy, ix), 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(count > 0, total / count, np.nan)
    return mean, count


def distance_matrix(xy): #ditsnace of matidx

    diff = xy[:, None, :] - xy[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=-1))


 #nearest neightbour bhab min (distance (neighr1,neighbor 2))
def nearest_neighbour_distance(xy):
    d = distance_matrix(xy)
    np.fill_diagonal(d, np.inf)
    return d.min(axis=1)
def build_dataframe(points):
    df = pd.DataFrame([{"label": p.label, "x": p.x, "y": p.y,
                        "rssi_dbm": p.reading} for p in points])
    df["col"] = np.minimum((df.x // CELL).astype(int), int(WIDTH // CELL) - 1)
    df["row"] = np.minimum((df.y // CELL).astype(int), int(HEIGHT // CELL) - 1)
    df["cell"] = "C" + df["col"].astype(str) + "R" + df["row"].astype(str)
    df["weak"] = df.rssi_dbm < WEAK_THRESHOLD       # NaN -> False (unknown)
    return df


def compare_locations(df):
    overall = df.rssi_dbm.mean()
    cells = (df.groupby("cell")
             .agg(samples=("rssi_dbm", "count"),     # valid readings only or else akta boro text
                  visits=("label", "size"),
                  mean_dbm=("rssi_dbm", "mean"),
                  worst_dbm=("rssi_dbm", "min"),
                  pct_weak=("weak", "mean"))
             .assign(vs_overall=lambda t: t.mean_dbm - overall)
             .sort_values("mean_dbm"))
    cells["pct_weak"] = (cells.pct_weak * 100).round(0)
    # a cell is a weak ZONE if its mean is below threshold, and has >=2 samples kgulo ke nebe bara
    cells["weak_zone"] = (cells.mean_dbm < WEAK_THRESHOLD) & (cells.samples >= 2)
    return cells.round(1)
def make_plots(df, mean_grid, prefix="survey"):
    valid = df.dropna(subset=["rssi_dbm"])
    weak = valid[valid.weak]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    sc = ax.scatter(valid.x, valid.y, c=valid.rssi_dbm, cmap="RdYlGn",
                    vmin=-90, vmax=-40, s=55, edgecolor="k", linewidth=0.3)
    ax.scatter(weak.x, weak.y, s=150, facecolors="none", edgecolors="red",
               linewidth=1.2, label=f"weak (< {WEAK_THRESHOLD:.0f} dBm)")
    nomr = df[df.rssi_dbm.isna()]
    ax.scatter(nomr.x, nomr.y, marker="x", c="grey", label="no reading")
    for k in range(1, int(WIDTH // CELL)):
        ax.axvline(k * CELL, color="lightgrey", lw=0.5, zorder=0)
    for k in range(1, int(HEIGHT // CELL)):
        ax.axhline(k * CELL, color="lightgrey", lw=0.5, zorder=0)
    ax.set(xlim=(0, WIDTH), ylim=(0, HEIGHT), xlabel="x (m)", ylabel="y (m)",
           title="Signal strength survey map", aspect="equal")
    fig.colorbar(sc, label="RSSI (dBm)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{prefix}_map.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(valid.rssi_dbm, bins=15, color="steelblue", edgecolor="white")
    ax.axvline(WEAK_THRESHOLD, color="red", ls="--",
               label=f"threshold {WEAK_THRESHOLD:.0f} dBm")
    ax.axvline(valid.rssi_dbm.mean(), color="k", ls=":", label="mean")
    ax.set(xlabel="RSSI (dBm)", ylabel="points", title="Distribution of readings")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{prefix}_hist.png", dpi=130)
    plt.close(fig)

def report(df, cells, mean_grid, count_grid, rejected, xy): #report r lelha gulo net theke neyo hoyache to make it more cool and professional 1!
    valid = df.rssi_dbm.dropna()
    print("=" * 60)
    print("DATA QUALITY")
    print(f"  rows rejected on load : {len(rejected)}")
    for line, why in rejected:
        print(f"    line {line}: {why}")
    print(f"  points kept           : {len(df)}")
    print(f"  missing readings      : {df.rssi_dbm.isna().sum()} (excluded from stats)")
    unsurveyed = int(np.isnan(mean_grid).sum())
    print(f"  grid cells w/o data   : {unsurveyed} of {mean_grid.size} (unknown, not weak)")
    print(f"  mean nearest-neighbour spacing: {nearest_neighbour_distance(xy).mean():.1f} m")

    print("\nSUMMARY")
    print(f"  mean {valid.mean():.1f} dBm | median {valid.median():.1f} | "
          f"min {valid.min():.1f} | max {valid.max():.1f}")
    print(f"  weak points (< {WEAK_THRESHOLD:.0f} dBm): "
          f"{int(df.weak.sum())} of {len(valid)} ({100 * df.weak.sum() / len(valid):.0f}%)")

    zones = cells[cells.weak_zone]
    print(f"\nWEAK ZONES ({len(zones)} cells, mean below threshold, >=2 samples)")
    print(zones[["samples", "mean_dbm", "worst_dbm", "pct_weak", "vs_overall"]]
          .to_string() if len(zones) else "  none")

    print("\nTHRESHOLD SENSITIVITY (how the answer changes with the cut-off)")
    for t in (-65, -67, -70, -75, -80):
        n = int((valid < t).sum())
        print(f"  < {t} dBm : {n:3d} points ({100 * n / len(valid):4.0f}%)")

    print("""
JUSTIFICATION
  Threshold -70 dBm: vendor guidance (e.g. Cisco/Meraki, Ubiquiti) treats about
  -67 dBm as the minimum for voice/video and -70 dBm as the lowest level for
  reliable data; below roughly -75 dBm throughput drops sharply. -70 sits
  between "good enough for video" and "clearly poor", so it flags real problems
  without marking half the floor as weak. The sensitivity table above shows
  how much the conclusion depends on this choice; adjust WEAK_THRESHOLD for
  different use cases (e.g. IoT sensors tolerate weaker signals).

MISSING DATA
  - Missing/invalid coordinates: row rejected (an unlocated reading cannot be
    mapped, and guessing a location would invent data).
  - Missing reading at a known location: kept as a visit but excluded from
    means and NOT counted as weak (absence of a reading is not a low reading).
    Marked with grey crosses on the map for re-measurement.
  - Cells with no readings: reported as unsurveyed/unknown, never as weak.
  - A cell is called a weak zone only with >=2 samples, so one noisy reading
    cannot condemn an area (RSSI fluctuates by several dB).
""")
def parse_netsh(text): #here oi dekh soumik and anish toder windows w netsh e ja oi theke kor cmd prompt e

    m = re.search(r"^\s*Rssi\s*:\s*(-?\d+)", text, re.M | re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"^\s*Signal\s*:\s*(\d+)\s*%", text, re.M | re.I)
    if m:
        return int(m.group(1)) / 2 - 100
    return None


def read_wifi_signal(quiet=False):
    try:
        out = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                             capture_output=True, text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        if not quiet:
            print("  netsh not available (needs Windows with a Wi-Fi adapter).")
        return None
    value = parse_netsh(out)
    if value is None and not quiet:
        low = out.lower()
        if "elevation" in low or "location permission" in low:
            print("  Windows blocked netsh: turn on Location services "
                  "(ms-settings:privacy-location) and run as Administrator.")
        else:
            print("  No signal found - are you connected to Wi-Fi?")
    return value


def read_wifi_average(samples=3, delay=1.0):
    vals = []
    for i in range(samples):
        v = read_wifi_signal()
        if v is not None:
            vals.append(v)
        if i < samples - 1:
            time.sleep(delay)
    return round(sum(vals) / len(vals), 1) if vals else None


def collect_points(path=CSV_FILE):
    mode = "a"
    if os.path.exists(path):
        ans = input(f"{path} exists. [A]ppend or start [N]ew? ").strip().lower()
        mode = "w" if ans.startswith("n") else "a"
    new_file = mode == "w" or not os.path.exists(path)
    print(f"Area is {WIDTH} x {HEIGHT} m. Press Enter on x to finish.")
    n = 0
    with open(path, mode, newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["label", "x", "y", "rssi_dbm"])
        while True:
            x = input("\nx position (m): ").strip()
            if x == "":
                break
            y = input("y position (m): ").strip()
            print("  measuring...")
            rssi = read_wifi_average()
            try:
                pt = SurveyPoint(x, y, rssi, f"P{n + 1:03d}")
            except ValueError as e:
                print(f"  rejected: {e}")
                continue
            if not pt.has_reading:
                print("  no signal reading (not connected?) - saved as missing")
            else:
                print(f"  {pt.reading} dBm saved")
            w.writerow(pt.to_row())
            f.flush()
            n += 1
    print(f"\n{n} point(s) recorded in {path}.")


def _ask_float(prompt, default=None):
    raw = input(prompt).strip()
    if raw == "":
        return default
    return float(raw)


def _open_csv(path):

    mode, rows = "a", 0
    if os.path.exists(path):
        ans = input(f"{path} exists. [A]ppend or start [N]ew? ").strip().lower()
        mode = "w" if ans.startswith("n") else "a"
        if mode == "a":
            with open(path, newline="") as f:
                rows = max(0, sum(1 for _ in f) - 1)
    new_file = mode == "w" or not os.path.exists(path)
    f = open(path, mode, newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["label", "x", "y", "rssi_dbm"])
    return f, w, rows


def auto_walk(path=CSV_FILE):
    print("Checking Wi-Fi access...")
    if read_wifi_signal() is None:
        print("Fix the problem above, then try again.")
        return
    f, w, n = _open_csv(path)
    print(f"Area is {WIDTH} x {HEIGHT} m. Press Enter on 'start x' to finish.")
    with f:
        while True:
            try:
                sx = _ask_float("\nWalk start x (m): ")
                if sx is None:
                    break
                sy = _ask_float("Walk start y (m): ")
                ex = _ask_float("Walk end   x (m): ")
                ey = _ask_float("Walk end   y (m): ")
                secs = _ask_float("Walk time in seconds [30]: ", 30.0)
                gap = _ask_float("Seconds between readings [2]: ", 2.0)
                SurveyPoint(sx, sy)           # validate both ends
                SurveyPoint(ex, ey)
                if secs <= 0 or gap <= 0:
                    raise ValueError("times must be positive")
            except (TypeError, ValueError) as e:
                print(f"  invalid input: {e}")
                continue
            count = max(2, int(secs // gap) + 1)
            input(f"Stand at the start, press Enter, then walk steadily to the end "
                  f"({count} readings)...")
            t0 = time.time()
            for i in range(count):
                time.sleep(max(0.0, t0 + i * gap - time.time()))
                frac = i / (count - 1)
                x, y = sx + (ex - sx) * frac, sy + (ey - sy) * frac
                n += 1
                pt = SurveyPoint(x, y, read_wifi_signal(quiet=True), f"P{n:03d}")
                w.writerow(pt.to_row())
                f.flush()
                shown = f"{pt.reading} dBm" if pt.has_reading else "no reading"
                print(f"  {pt.label} at ({x:5.1f}, {y:5.1f}) m -> {shown}")
    print(f"\nDone. {n} total point(s) in {path}.")


def analyse(path):
    if not os.path.exists(path):
        print(f"{path} not found.")
        return
    points, rejected = load_points(path)
    xy, rssi = to_arrays(points) if points else (np.empty((0, 2)), np.array([]))
    if not points or np.isnan(rssi).all():
        print("No usable readings in this file yet.")
        return
    mean_grid, count_grid = grid_summary(xy, rssi)
    df = build_dataframe(points)
    cells = compare_locations(df)
    make_plots(df, mean_grid)
    report(df, cells, mean_grid, count_grid, rejected, xy)
    print("Saved: survey_map.png, survey_hist.png")
    for img in ("survey_map.png", "survey_hist.png"):
        try:
            os.startfile(img)
        except (AttributeError, OSError):
            pass


def main(): #lol juist easy fuck asss man you know it !
    print("1) AUTOMATIC survey  - walk a path, readings taken for you (netsh)")
    print("2) MANUAL survey     - type the x, y of each spot yourself (netsh)")
    print("3) ANALYSE survey.csv")
    print("4) ANALYSE a demo with synthetic data (survey_demo.csv)")
    choice = input("Choose 1-4: ").strip()
    if choice == "1":
        auto_walk()
    elif choice == "2":
        collect_points()
    elif choice == "4":
        make_sample_data(path="survey_demo.csv")
        analyse("survey_demo.csv")
        return
    elif choice != "3":
        print("Not a valid choice.")
        return
    if choice in ("1", "2"):
        if input("Analyse now? [y/n] ").strip().lower() != "y":
            return
    analyse(CSV_FILE)

if __name__ == "__main__": #baal r main function
    main()
