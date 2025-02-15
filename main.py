# Heatmap with Thicker Lines and Horizontal Flip using cv2.applyColorMap
import cv2
import pandas as pd
import numpy as np

# Global variables
motion_points = []
tracker = cv2.TrackerCSRT_create()

# Video capture
cap = cv2.VideoCapture(0)
ret, frame1 = cap.read()
roi = cv2.selectROI('Object Tracker', frame1)
tracker.init(frame1, roi)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Flip frame horizontally
    frame = cv2.flip(frame, 1)

    success, roi = tracker.update(frame)
    (x, y, w, h) = map(int, roi)

    # Collect motion points with increased thickness
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            motion_points.append([x + dx, y + dy])

    if success:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

    if len(motion_points) > 1:
        heatmap_data = np.zeros((480, 640), dtype=np.float32)
        for point in motion_points:
            if 0 <= point[1] < 480 and 0 <= point[0] < 640:
                heatmap_data[point[1], point[0]] += 1

        heatmap_normalized = cv2.normalize(heatmap_data, None, 0, 255, cv2.NORM_MINMAX)
        heatmap_colored = cv2.applyColorMap(heatmap_normalized.astype(np.uint8), cv2.COLORMAP_JET)
        heatmap_resized = cv2.resize(heatmap_colored, (frame.shape[1], frame.shape[0]))

        combined = cv2.addWeighted(frame, 0.7, heatmap_resized, 0.3, 0)
        cv2.imshow('Object Tracker with Heatmap', combined)
    else:
        cv2.imshow('Object Tracker', frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

# Export final heatmap as image
heatmap_normalized = cv2.normalize(heatmap_data, None, 0, 255, cv2.NORM_MINMAX)
final_heatmap = cv2.applyColorMap(heatmap_normalized.astype(np.uint8), cv2.COLORMAP_JET)
cv2.imwrite('final_heatmap.png', final_heatmap)

