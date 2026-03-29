# MEMS FSM Characterization & API Specification

## 1. Experimental Setup
* **FSM:** 2-axis (Decoupled X/Y), $\pm 4.5^{\circ}$ range.
* **Target:** Matte grey surface (reduces laser "bloom" and speckle).
* **Camera:** Raspberry Pi Camera with Wide-Angle Lens.
* **Geometry:** Distance ($L$) between FSM and Screen: **30cm – 50cm**.
* **Laser Spot:** Focus/Defocus until the spot is **5–10 pixels** wide on the sensor.

---

## 2. Calibration Workflow
To convert raw camera pixels into true angular displacement, follow these three stages:

### Stage A: Lens Undistortion (The "Fish-eye" Fix)
Wide-angle lenses curve straight lines. Use a chessboard pattern and OpenCV to find your camera matrix.
1. Capture 10–20 images of a chessboard at various angles.
2. Use `cv2.calibrateCamera()` to get `mtx` (Camera Matrix) and `dist` (Distortion Coefficients).

### Stage B: Homography (The "Keystone" Fix)
Maps skewed camera pixels to real-world millimeters on the screen.
1. Place graph paper on the matte screen.
2. Run `cv2.undistort()` on a frame using the coefficients from Stage A.
3. Pick 4 points on the graph paper (e.g., the corners of a 100mm x 100mm square).
4. Use `cv2.getPerspectiveTransform()` to create the **Homography Matrix ($H$)**.

### Stage C: The Zero Point
1. Apply "Neutral" voltage to the FSM (center of range).
2. Record the $(x, y)$ millimeter coordinate. This is your $(0,0)$ origin.
3. All future measurements are calculated as:
   $$Dist = \sqrt{(x_{raw} - x_{zero})^2 + (y_{raw} - y_{zero})^2}$$

---

## 5. Maintenance & Repeatability
* **Hysteresis Check:** Periodically sweep $0 \rightarrow 4.5 \rightarrow 0$ to ensure the "up-slope" and "down-slope" match. If they deviate, average the values or use a directional lookup.
* **Rigidity:** If the camera or screen is bumped, re-run **Stage B** (Homography) only. You do not need to re-characterize the FSM voltages as long as the FSM-to-Screen distance ($L$) remains constant.