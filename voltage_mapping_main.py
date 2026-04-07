
import time
import csv
import click
from pathlib import Path

import cv2
import numpy as np

from src import FSM, picam, centroiding, VDIFF_MAX_VOLTS, VDIFF_MIN_VOLTS


"""
Testing file for fast mirrorcle mirror benchmarking. Allows for user to input 
several parameters to sweep mirror across an axis and calculate angular displacement
-voltage mapping. 

BE CAREFUL WITH THE MIRROR IF YOU USE IT WRONG MINUS LOTS OF MONEY (1000 i thjink)
"""

_DEFAULT_CAL = Path(__file__).resolve().parent / "config" / "camera_params.npz"


def _csv_header(calib):
    if calib is None:
        return ["vdiffx", "vdiffy", "cx_raw", "cy_raw"]
    if calib.H is not None:
        return ["vdiffx", "vdiffy", "cx_ud_px", "cy_ud_px", "x_mm", "y_mm"]
    return ["vdiffx", "vdiffy", "cx_ud_px", "cy_ud_px"]


def get_frames(cam, num_frames, roi, calib=None):
    """
    Average centroid over num_frames. Returns a list matching _csv_header(calib):
    raw px | undistorted px | undistorted px + board mm (when H present).
    """
    if calib is not None and calib.H is not None:
        cx, cy, mx, my = [], [], [], []
        for _ in range(num_frames):
            gray = picam.get_gray_frame(cam)
            time.sleep(0.05)
            rect = calib.undistort_gray(gray)
            pt = centroiding.find_laser_centroid(rect, roi)
            if pt is None:
                continue
            pix = np.array([[[pt[0], pt[1]]]], dtype=np.float32)
            world = cv2.perspectiveTransform(pix, calib.H)
            cx.append(float(pt[0]))
            cy.append(float(pt[1]))
            mx.append(float(world[0, 0, 0]))
            my.append(float(world[0, 0, 1]))
        if not cx:
            return [float("nan"), float("nan"), float("nan"), float("nan")]
        n = len(cx)
        return [sum(cx) / n, sum(cy) / n, sum(mx) / n, sum(my) / n]

    cx, cy = [], []
    for _ in range(num_frames):
        gray = picam.get_gray_frame(cam)
        time.sleep(0.05)
        if calib is None:
            res = centroiding.find_laser_centroid(gray, roi)
        else:
            res = calib.find_corrected_rectified_centroid(gray, roi)
        if res is None:
            continue
        cx.append(res[0])
        cy.append(res[1])

    if not cx:
        return [float("nan"), float("nan")]

    return [sum(cx) / len(cx), sum(cy) / len(cy)]

def write_to_outfile(outfile, coords, mode, header_row):
    """
    Write data from results array into outfile
    """
    with open(outfile, mode, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header_row)
        writer.writerows(coords)

# click is just an easy library for handling CLI interface --> configure parameters using cmd line
@click.command()
@click.option('-n', '--num_frames', default=5, type=int, help="Number of frames to capture per step")
@click.option('-t', '--settling_time', default=0.1, type=float, help="Settling time in between voltage steps in seconds")
@click.option('-a', '--axis', default="x", type=str, help="Axis to sweep. <x> for x-axis, <y> for y-axis <b> for both")
@click.option('-o', '--outfile', default="voltage_mapping_out.csv", type=str, help="CSV outfile name")
@click.option('-s', '--step-size', default=1, type=float, help="VDIFF step size between frames in V")
@click.option('--start', default=0, type=float, help="Start voltage in V")
@click.option('--end', default=175, type=float, help="End voltage in V")
@click.option('--resolution', default=640, type=int, help='Frame width in pixels (height is 480; match config/calibration)')
@click.option('--roi', default=50, type=int, help="Size in pixels of roi around centroid")
@click.option('--mode', default="man", type=str, help="Set mode <auto> for a fast sweep <man> for stepping")
@click.option('--image_outfile', default=None, type=str, help="If set, writes grayscale image to outfile")
@click.option(
    '--calibration',
    'calibration_path',
    type=click.Path(path_type=Path, dir_okay=False),
    default=_DEFAULT_CAL,
    help="camera_params.npz from config/calibrate_picam.py (lens + optional H).",
)
@click.option(
    '--no-calib',
    is_flag=True,
    help="Use raw sensor pixels in CSV (skip undistort / mm transform).",
)
def cmd(num_frames, settling_time, axis, outfile, step_size, start, end, resolution, roi, mode, image_outfile,
        calibration_path, no_calib):
    """
    cmd function for click to enable easy CLI
    """

    fsm = FSM()
    cam = None
    calib = None
    try:
        try:
            cam = picam.init_camera(resolution)
        except Exception as exc:
            print(f"Camera failed: {exc}")
            input("Cam not connected. Press any key to shutdown and end.")
            return

        if not no_calib:
            try:
                calib = centroiding.CameraCalibration.load(calibration_path)
                if calib.H is not None:
                    print("Calibration: undistort + homography (CSV in board mm).")
                else:
                    print("Calibration: undistorted pixels only (add H via calibrate_picam for mm).")
            except FileNotFoundError as exc:
                print(exc)
                print("Run config/calibrate_picam.py first, or pass --no-calib.")
                input("Press any key to exit.")
                return
        header = _csv_header(calib)

        if mode == "test-cam":
            print("Taking picture with picam to test dat jit")
            gray = picam.get_gray_frame(cam)
            if calib is not None:
                gray = calib.undistort_gray(gray)
            centroiding.grayscale_to_outfile(gray, "gray1.jpg")
            return

        active = fsm.begin()
        with open(outfile, "w", newline="") as f:
            pass
        coords = []

        if mode == "man":
            print(f'[MAN] FSM is active at {fsm.vdiff_x} Vdiff-x | {fsm.vdiff_y} Vdiff-y')
            if active == -1:
                print("FSM failed to start up, shutting down")
                fsm.close()
                return
            try:
                while True:  # main loop
                    usr = input("Input vdiffx, vdiffy (x y): ")
                    lst = usr.split()
                    if len(lst) != 2:
                        print("Bad coords. Input <x y>")
                        continue
                    x, y = tuple(lst)
                    if x and y:
                        print(f'setting vdiff: x: {x}, y: {y}')
                        fsm.set_vdiff(float(x), float(y))

                        centroid = get_frames(cam, num_frames, roi, calib)
                        vdiff_x, vdiff_y = fsm.get_voltages()
                        coords.append([vdiff_x, vdiff_y, *centroid])

                    else:
                        print("Bad coords. Input <x y>")
                        continue

            except KeyboardInterrupt:
                print("Keyboard interrupt received — shutting down")
            except Exception:
                print("Other error occurred, shutting down.")
            finally:
                fsm.close()
                write_to_outfile(outfile, coords, "a", header)
            return

        elif mode == "auto":
            if active == -1:
                print("FSM failed to start up, shutting down")
                fsm.close()
                return

            print(f'[AUTO] FSM is active at {fsm.vdiff_x} Vdiff-x | {fsm.vdiff_y} Vdiff-y')

            if VDIFF_MIN_VOLTS > start or start > VDIFF_MAX_VOLTS:
                print("[AUTO] Start val not in vdiff allowed range")
                fsm.close()
                return
            if VDIFF_MIN_VOLTS > end or end > VDIFF_MAX_VOLTS:
                print("[AUTO] End val not in vdiff allowed range")
                fsm.close()
                return

            curr_vdiff = start
            try:
                while curr_vdiff <= end:

                    if axis == "x":
                        fsm.set_vdiff(curr_vdiff, 0)
                    elif axis == "y":
                        fsm.set_vdiff(0, curr_vdiff)
                    else:
                        break

                    centroid = get_frames(cam, num_frames, roi, calib)
                    vdiff_x, vdiff_y = fsm.get_voltages()
                    coords.append([vdiff_x, vdiff_y, *centroid])

                    time.sleep(settling_time)

                    curr_vdiff += step_size

            except KeyboardInterrupt:
                print("Keyboard interrupt received — shutting down")
            except Exception:
                print("Other error occurred, shutting down.")
            finally:
                fsm.close()
                write_to_outfile(outfile, coords, "w", header)
            return

        else:
            print("Invalid mode, shutting down")
            fsm.close()
            return

    finally:
        picam.close_camera(cam)


if __name__ == "__main__":
    cmd()
