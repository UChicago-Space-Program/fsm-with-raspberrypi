# Camera calibration and voltage mapping — usage

Run these steps on the **Raspberry Pi** (Picamera2 + OpenCV). Commands assume your **current working directory** is the project root that contains `config/`, `src/`, and `voltage_mapping_main.py` (this repo’s `rasppi_src` folder).

---

## 1. Prerequisites

- Python environment with **`picamera2`**, **`opencv-python`** (or system OpenCV), **`numpy`**, **`click`**.
- ChArUco board that matches **`config/calibrate_picam.py`** (`SQUARES_X`, `SQUARES_Y`, `SQUARE_LENGTH`, `MARKER_LENGTH`, dictionary).
- **Resolution:** Capture, calibration stills, and mapping must use the **same frame size**. Default is **640×480** (`src/picam.DEFAULT_FRAME_SIZE` and `FRAME_SIZE` in `config/get_calib_photos.py`). If you change width, pass the same value to mapping as `--resolution`.

---

## 2. Capture calibration images (Picamera2)

Saves JPEGs under `config/calib_images/`. In the preview window: **SPACE** = save frame, **ESC** = quit.

```bash
cd /path/to/rasppi_src
python3 config/get_calib_photos.py
```

Tips:

- Use **10–20** images with the board at different angles and distances.
- Keep lighting and focus representative of mapping runs.

---

## 3. Lens calibration (ChArUco → `camera_params.npz`)

Reads `config/calib_images/*.jpg` and writes **`config/camera_params.npz`** with `mtx`, `dist`, and `rms`. Fails if detections are weak or RMS is too high (see `MAX_RMS_PIXELS` in the script).

```bash
cd /path/to/rasppi_src
python3 config/calibrate_picam.py
```

---

## 4. Homography (optional — mm coordinates in CSV)

Homography **`H`** maps undistorted **pixels** to the **ChArUco board plane (meters/mm as defined by your square length in `calibrate_picam.py`)**. Use a single image where the **full board is clearly visible** and the board is in the **same physical relationship** to the camera you care about for mapping.

### Option A — lens cal + homography in one run

Runs lens calibration from `calib_images`, then computes **`H`** from the reference image and saves everything into one `npz`:

```bash
cd /path/to/rasppi_src
python3 config/calibrate_picam.py --homography-ref /path/to/board_visible.jpg
```

### Option B — update **`H`** only (keep existing `mtx` / `dist`)

After you move the board or camera mount but **not** lens focus or resolution:

```bash
cd /path/to/rasppi_src
python3 config/calibrate_picam.py --update-homography /path/to/board_visible.jpg
```

---

## 5. Voltage mapping (uses calibration by default)

`voltage_mapping_main.py` loads **`config/camera_params.npz`** automatically, applies **undistortion**, then optionally **mm** via **`H`** if present.

### Default calibration path + resolution

```bash
cd /path/to/rasppi_src
python3 voltage_mapping_main.py --resolution 640 --mode man
```

### Custom `npz` location

```bash
python3 voltage_mapping_main.py --calibration /path/to/camera_params.npz --mode auto --axis x --start 0 --end 175 --step-size 1
```

### Raw pixels (no `npz`; for quick tests)

```bash
python3 voltage_mapping_main.py --no-calib --mode man
```

### Camera sanity check (writes `gray1.jpg`; undistorted if `npz` exists)

```bash
python3 voltage_mapping_main.py --mode test-cam
```

---

## 6. CSV output columns

The first two columns are always **`vdiffx`**, **`vdiffy`**. The centroid columns depend on calibration:

| Situation | Columns 3–4 |
|-----------|----------------|
| Default: `npz` with `mtx`, `dist` only | `cx_ud_px`, `cy_ud_px` (undistorted pixels) |
| `npz` also contains **`H`** | `x_mm`, `y_mm` (board plane) |
| **`--no-calib`** | `cx_raw`, `cy_raw` |

---

## 7. When to redo which step

| Change | Redo capture | Redo `calibrate_picam.py` (lens) | Redo **`H`** |
|--------|----------------|----------------------------------|--------------|
| Lens focus, zoom, or **resolution** | Yes | Yes | Yes |
| Camera rigid move, **same** focus/resolution | Optional for lens | Usually no | **Yes** if you use mm |
| Board moved / scene geometry changed | No (for lens) | No | **Yes** |
| New printed board or wrong board params in script | Yes | Yes | Yes (after new lens cal) |

---

## 8. File locations

| File / directory | Role |
|------------------|------|
| `config/calib_images/` | JPEGs from `get_calib_photos.py` |
| `config/camera_params.npz` | `mtx`, `dist`, `rms`, optional `H` |
| `voltage_mapping_out.csv` (or `-o`) | Mapping output |
