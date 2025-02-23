const uploadForm = document.getElementById('uploadForm');
const videoInput = document.getElementById('videoInput');
const previewBox = document.getElementById('previewBox');
const videoPreview = document.getElementById('videoPreview');
const canvasOverlay = document.getElementById('canvasOverlay');
const processBtn = document.getElementById('processBtn');
const loadingDiv = document.getElementById('loading');
const resultDiv = document.getElementById('result');
const heatmapImage = document.getElementById('heatmapImage');
const fileNameDiv = document.getElementById('fileName');

// For drag ROI
let isDragging = false;
let startX = 0, startY = 0;
let endX = 0, endY = 0;
let ctx = null;

// 1) Upload the video -> compress -> return URL & file name
uploadForm.addEventListener('submit', (e) => {
  e.preventDefault();
  if (!videoInput.files.length) return;

  // Hide sections and show loading
  previewBox.classList.add('hidden');
  processBtn.classList.add('hidden');
  resultDiv.classList.add('hidden');
  loadingDiv.classList.remove('hidden');
  fileNameDiv.classList.add('hidden');
  heatmapImage.src = '';

  const formData = new FormData();
  formData.append('video', videoInput.files[0]);

  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      console.error(data.error);
      loadingDiv.classList.add('hidden');
      return;
    }
    // Set the compressed video URL for preview and force load it
    videoPreview.src = data.compressedVideoURL;
    videoPreview.load();
    videoPreview.addEventListener("loadedmetadata", () => {
      videoPreview.pause(); // Pause to show the first frame for ROI selection
      setupCanvas();
    }, { once: true });
    // Display the file name
    fileNameDiv.textContent = "Uploaded file: " + data.fileName;
    fileNameDiv.classList.remove('hidden');
    // Show preview and ROI selection options
    previewBox.classList.remove('hidden');
    processBtn.classList.remove('hidden');
    loadingDiv.classList.add('hidden');
  })
  .catch(err => {
    console.error(err);
    loadingDiv.classList.add('hidden');
  });
});

// 2) Setup canvas overlay after video is ready
function setupCanvas() {
  canvasOverlay.width = videoPreview.videoWidth;
  canvasOverlay.height = videoPreview.videoHeight;
  ctx = canvasOverlay.getContext('2d');
}

// 3) Mouse events on the canvas for ROI selection
canvasOverlay.addEventListener('mousedown', (e) => {
  isDragging = true;
  const rect = canvasOverlay.getBoundingClientRect();
  startX = e.clientX - rect.left;
  startY = e.clientY - rect.top;
});

canvasOverlay.addEventListener('mousemove', (e) => {
  if (!isDragging) return;
  const rect = canvasOverlay.getBoundingClientRect();
  endX = e.clientX - rect.left;
  endY = e.clientY - rect.top;

  // Draw the ROI rectangle
  ctx.clearRect(0, 0, canvasOverlay.width, canvasOverlay.height);
  ctx.beginPath();
  ctx.lineWidth = 2;
  ctx.strokeStyle = 'lime';
  ctx.rect(startX, startY, endX - startX, endY - startY);
  ctx.stroke();
});

canvasOverlay.addEventListener('mouseup', (e) => {
  isDragging = false;
  const rect = canvasOverlay.getBoundingClientRect();
  endX = e.clientX - rect.left;
  endY = e.clientY - rect.top;
});

// 4) When user clicks "Generate Heatmap"
processBtn.addEventListener('click', () => {
  // Hide preview and show loading indicator
  previewBox.classList.add('hidden');
  loadingDiv.classList.remove('hidden');
  resultDiv.classList.add('hidden');

  // Get ROI coordinates
  const coords = {
    x1: Math.round(startX),
    y1: Math.round(startY),
    x2: Math.round(endX),
    y2: Math.round(endY)
  };
  // Get background option for heatmap (black or white)
  const bgOption = document.querySelector('input[name="bgOption"]:checked').value;

  fetch('/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...coords, bg: bgOption })
  })
  .then(response => response.blob())
  .then(blob => {
    const url = URL.createObjectURL(blob);
    heatmapImage.src = url;
    loadingDiv.classList.add('hidden');
    resultDiv.classList.remove('hidden');
  })
  .catch(err => {
    console.error(err);
    loadingDiv.classList.add('hidden');
  });
});
