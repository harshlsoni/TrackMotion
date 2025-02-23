from flask import Flask, request, render_template, send_file, jsonify, session, url_for
import cv2
import numpy as np
import os
import uuid

app = Flask(__name__)
app.secret_key = 'replace_with_any_random_secret_key'

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """
    1) Receive the uploaded video.
    2) Compress it to 640x480 using MP4 (mp4v).
    3) Return a JSON with the compressed video URL and file name for preview.
    """
    file = request.files['video']
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    original_filename = file.filename
    input_path = os.path.join(UPLOAD_FOLDER, original_filename)
    file.save(input_path)

    # Generate a unique compressed filename with .mp4 extension
    compressed_name = f'compressed_{uuid.uuid4().hex}.mp4'
    compressed_path = os.path.join(UPLOAD_FOLDER, compressed_name)
    compress_video(input_path, compressed_path)

    # Save compressed video path in session for later use
    session['compressed_video'] = compressed_path

    return jsonify({
        'compressedVideoURL': url_for('serve_video', filename=compressed_name),
        'fileName': original_filename
    })

@app.route('/video/<filename>')
def serve_video(filename):
    """
    Serve the compressed MP4 so the <video> tag can play it in the browser.
    """
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return "Video not found!", 404
    return send_file(path, mimetype='video/mp4')

@app.route('/process', methods=['POST'])
def process():
    """
    1) Receive bounding box (x1, y1, x2, y2) and background option from frontend.
    2) Run motion tracking and heatmap generation.
    3) Return the final heatmap image.
    """
    data = request.json
    x1, y1, x2, y2 = data['x1'], data['y1'], data['x2'], data['y2']
    bg_option = data.get('bg', 'black')

    compressed_path = session.get('compressed_video')
    if not compressed_path or not os.path.exists(compressed_path):
        default_img = os.path.join(RESULT_FOLDER, 'default.png')
        return send_file(default_img, mimetype='image/png')

    heatmap_path = process_video(compressed_path, (x1, y1, x2, y2), bg_option)
    return send_file(heatmap_path, mimetype='image/png')

def compress_video(input_path, output_path):
    """
    Resize video to 640x480, encode with mp4v at 20 FPS (MP4).
    """
    cap = cv2.VideoCapture(input_path)
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (640, 480))
        out.write(frame)

    cap.release()
    out.release()

def process_video(video_path, roi_points, bg_option="black"):
    """
    Track motion from the first frame using a CSRT tracker initiated with the user-selected ROI.
    Collect motion points and generate a heatmap.
    Depending on bg_option, set the background pixels to black or white.
    """
    (x1, y1, x2, y2) = roi_points
    x, w = sorted([x1, x2])
    y, h = sorted([y1, y2])
    w -= x
    h -= y

    tracker = cv2.TrackerCSRT_create()
    cap = cv2.VideoCapture(video_path)
    ret, frame1 = cap.read()
    if not ret:
        return os.path.join(RESULT_FOLDER, 'default.png')

    # Flip the first frame horizontally
    frame1 = cv2.flip(frame1, 1)
    tracker.init(frame1, (x, y, w, h))

    motion_points = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        success, updated_roi = tracker.update(frame)
        if success:
            rx, ry, rw, rh = map(int, updated_roi)
            # Add a thicker cluster of points
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    motion_points.append([rx + dx, ry + dy])
    cap.release()

    # Build the heatmap
    heatmap_data = np.zeros((480, 640), dtype=np.float32)
    for px, py in motion_points:
        if 0 <= py < 480 and 0 <= px < 640:
            heatmap_data[py, px] += 1

    heatmap_normalized = cv2.normalize(heatmap_data, None, 0, 255, cv2.NORM_MINMAX)
    heatmap_colored = cv2.applyColorMap(heatmap_normalized.astype(np.uint8), cv2.COLORMAP_JET)

    # Replace background (where no motion) based on user selection:
    mask = (heatmap_data == 0)
    if bg_option == "white":
        heatmap_colored[mask] = [255, 255, 255]
    else:
        heatmap_colored[mask] = [0, 0, 0]

    heatmap_path = os.path.join(RESULT_FOLDER, 'heatmap.png')
    cv2.imwrite(heatmap_path, heatmap_colored)
    return heatmap_path

if __name__ == '__main__':
    app.run(debug=True)
