from picamera2 import Picamera2, Preview
import time

# Initialize camera
picam2 = Picamera2()

# Use a normal capture config (preview config not needed for headless)
camera_config = picam2.create_still_configuration()
picam2.configure(camera_config)

# Start camera
picam2.start()
time.sleep(2)  # let auto-exposure/white balance settle

# Capture a single image to file
picam2.capture_file("test3.jpg")

# Or capture to a numpy array for OpenCV processing
frame = picam2.capture_array()

# Example: show shape
print("Captured frame shape:", frame.shape)


