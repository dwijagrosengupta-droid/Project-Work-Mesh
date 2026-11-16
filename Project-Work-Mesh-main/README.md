# Wi-Fi Signal Strength Survey Tool

A single-file Python tool that measures Wi-Fi signal strength (RSSI, in dBm) at different spots in a room or building, then analyses the readings to find weak-signal zones. It can collect data live on a Windows laptop, or run on built-in synthetic data as a demo.

## What it does

- **Collects readings** from your laptop's Wi-Fi adapter using the Windows command `netsh wlan show interfaces`.
  - *Automatic mode:* you give a start point, an end point and a walk time, and the tool takes readings at regular intervals while you walk, placing each one along the line.
  - *Manual mode:* you type the x, y position of each spot, and the tool averages 3 readings taken a second apart.
- **Validates every point** with a `SurveyPoint` class: coordinates must be numbers inside the survey area, and readings must be between -100 and -20 dBm. Bad rows are rejected with a reason.
- **Analyses the data** with NumPy and Pandas: overall statistics, a 10 m × 10 m grid of average signal per cell, and a list of weak zones.
- **Draws two plots:** a colour-coded survey map and a histogram of readings.

## Requirements

- Python 3.9+
- `numpy`, `pandas`, `matplotlib`

```
pip install numpy pandas matplotlib
```

Live surveying (options 1 and 2) needs **Windows with a Wi-Fi adapter**. Analysis and the demo (options 3 and 4) work on any system.

## First-time setup (Windows)

1. Turn on **Location services** in Windows (Settings → Privacy → Location). Newer Windows versions block `netsh` from reading Wi-Fi details without it.
2. Run PyCharm (or your terminal) **as Administrator** the first time.
3. Check that Windows can see your Wi-Fi by running this in Command Prompt:
   ```
   netsh wlan show interfaces
   ```
   You should see a `Signal` line (and on some systems an `Rssi` line). If you do, the tool will work.
4. Make sure the laptop is **connected to the Wi-Fi network** you want to survey.

## How to run

```
python wifi_survey.py
```

(Use whatever name you saved the file under.) You will see a menu:

| Option | What it does |
|---|---|
| 1 | **Automatic survey.** Enter walk start (x, y), end (x, y), duration and the gap between readings. Press Enter, then walk steadily to the end point. |
| 2 | **Manual survey.** Enter x and y for each spot. Press Enter on an empty x to finish. |
| 3 | **Analyse `survey.csv`.** |
| 4 | **Demo.** Creates synthetic data in `survey_demo.csv` and analyses it. |

After options 1 and 2 the tool asks whether to analyse straight away.

## Settings

These constants sit at the top of the file and are easy to change:

| Constant | Default | Meaning |
|---|---|---|
| `WIDTH`, `HEIGHT` | 100, 60 | Survey area in metres. Set these to match your real space. |
| `CELL` | 10 | Grid cell size in metres. |
| `RSSI_MIN`, `RSSI_MAX` | -100, -20 | Readings outside this range are rejected. |
| `WEAK_THRESHOLD` | -70 | Readings below this (dBm) count as weak. |
| `CSV_FILE` | `survey.csv` | Where live survey data is stored. |

## Data file format

Data is stored as a plain CSV, so you can also create or edit it by hand:

```
label,x,y,rssi_dbm
P001,12.5,30.0,-54.0
P002,40.0,22.5,
```

An empty `rssi_dbm` means "visited, but no reading".

## Output

The analysis prints a report to the console and saves two images in the folder you ran the script from:

- `survey_map.png`: every reading as a coloured dot (red = weak, green = strong), weak points circled in red, missing readings as grey crosses, and grid lines for the cells.
- `survey_hist.png`: distribution of readings with the weak threshold and mean marked.

The console report covers:

1. **Data quality:** rows rejected, missing readings, grid cells with no data, average spacing between points.
2. **Summary:** mean, median, minimum and maximum signal, and how many points are weak.
3. **Weak zones:** grid cells whose average is below the threshold.
4. **Threshold sensitivity:** how many points would count as weak at -65, -67, -70, -75 and -80 dBm.
5. **Justification:** why -70 dBm is used, and how missing data is handled.

## How missing and bad data are handled

- **Missing or invalid coordinates:** the row is rejected, because a reading with no location can't be mapped and guessing would invent data.
- **Missing reading at a known location:** kept as a visit but left out of the averages, and *not* counted as weak.
- **Cells with no readings:** reported as unknown, never as weak.
- **Weak zones:** a cell is only called a weak zone if it has at least 2 samples, so one noisy reading can't condemn an area.

## Project structure

Everything is in one file:

| Section | Purpose |
|---|---|
| `SurveyPoint` | Validated survey point (position, reading, label). |
| `save_points`, `load_points` | CSV reading and writing, with rejection of bad rows. |
| `make_sample_data` | Synthetic data: 2 access points, a dead corner, missing readings and a few deliberately bad rows. |
| `grid_summary`, `distance_matrix`, `nearest_neighbour_distance` | NumPy calculations. |
| `build_dataframe`, `compare_locations` | Pandas tables and per-cell comparison. |
| `make_plots`, `report` | Plots and the console report. |
| `read_wifi_signal`, `auto_walk`, `collect_points` | Live data collection through `netsh`. |

## Troubleshooting

- **"netsh not available":** you are not on Windows, or there is no Wi-Fi adapter.
- **"Windows blocked netsh":** enable Location services and run as Administrator.
- **"No signal found":** the laptop isn't connected to Wi-Fi.
- **Plot windows:** the script saves images without opening windows. To see live plot windows, remove the line `matplotlib.use("Agg")` and add `plt.show()` after plotting.


