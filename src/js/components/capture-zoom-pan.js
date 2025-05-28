// Capture Image Zoom & Pan - キャプチャ画像専用のズーム・パン機能
let captureZoomLevel = 1;
let captureViewOffsetX = 0;
let captureViewOffsetY = 0;
let captureImageData = null;
let captureImageWidth = 0;
let captureImageHeight = 0;

// パン操作用の変数
let captureIsDragging = false;
let captureLastMouseX = 0;
let captureLastMouseY = 0;

function initializeCaptureZoomPan() {
    // DOM要素の存在チェック
    if (!captureCanvas || !captureZoomInButton || !captureZoomOutButton || !captureZoomResetButton) {
        console.warn('🎯 Capture elements not found, skipping initialization');
        return;
    }
      console.log('🎯 Initializing capture zoom-pan functionality');
    
    // ズームボタンのイベントリスナー（中心点ズーム）
    captureZoomInButton.addEventListener('click', () => {
        console.log('🔍 Capture zoom in clicked');
        zoomAtCenter(1.2);
    });
    
    captureZoomOutButton.addEventListener('click', () => {
        console.log('🔍 Capture zoom out clicked');
        zoomAtCenter(0.8);
    });
    
    captureZoomResetButton.addEventListener('click', () => {
        console.log('🔍 Capture zoom reset clicked');
        captureZoomLevel = 1;
        captureViewOffsetX = 0;
        captureViewOffsetY = 0;
        renderCaptureImage();
    });
    
    // マウスイベント（パン操作）
    captureCanvas.addEventListener('mousedown', startCapturePan);
    captureCanvas.addEventListener('mousemove', doCapturePan);
    captureCanvas.addEventListener('mouseup', endCapturePan);
    captureCanvas.addEventListener('mouseleave', endCapturePan);
      // ホイールズーム（マウス位置を中心としたズーム）
    captureCanvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        
        const rect = captureCanvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        // ズーム前のマウス位置での画像座標
        const beforeZoomImageX = (mouseX / captureZoomLevel) - captureViewOffsetX;
        const beforeZoomImageY = (mouseY / captureZoomLevel) - captureViewOffsetY;
        
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const oldZoom = captureZoomLevel;
        captureZoomLevel *= zoomFactor;
        if (captureZoomLevel < 0.1) captureZoomLevel = 0.1;
        if (captureZoomLevel > 10) captureZoomLevel = 10;
        
        // ズーム後もマウス位置が同じ画像座標を指すようにオフセットを調整
        const afterZoomImageX = (mouseX / captureZoomLevel) - captureViewOffsetX;
        const afterZoomImageY = (mouseY / captureZoomLevel) - captureViewOffsetY;
        
        captureViewOffsetX += beforeZoomImageX - afterZoomImageX;
        captureViewOffsetY += beforeZoomImageY - afterZoomImageY;
        
        console.log(`🔍 Zoom: ${oldZoom.toFixed(3)} → ${captureZoomLevel.toFixed(3)}, mouse: (${mouseX}, ${mouseY}), offset adjusted: (${captureViewOffsetX.toFixed(1)}, ${captureViewOffsetY.toFixed(1)})`);
        
        renderCaptureImage();
    });
}

function zoomAtCenter(zoomFactor) {
    // キャンバスの中心点を取得
    const centerX = captureCanvas.width / 2;
    const centerY = captureCanvas.height / 2;
    
    // ズーム前の中心点での画像座標
    const beforeZoomImageX = (centerX / captureZoomLevel) - captureViewOffsetX;
    const beforeZoomImageY = (centerY / captureZoomLevel) - captureViewOffsetY;
    
    const oldZoom = captureZoomLevel;
    captureZoomLevel *= zoomFactor;
    if (captureZoomLevel < 0.1) captureZoomLevel = 0.1;
    if (captureZoomLevel > 10) captureZoomLevel = 10;
    
    // ズーム後も中心点が同じ画像座標を指すようにオフセットを調整
    const afterZoomImageX = (centerX / captureZoomLevel) - captureViewOffsetX;
    const afterZoomImageY = (centerY / captureZoomLevel) - captureViewOffsetY;
    
    captureViewOffsetX += beforeZoomImageX - afterZoomImageX;
    captureViewOffsetY += beforeZoomImageY - afterZoomImageY;
    
    console.log(`🔍 Center zoom: ${oldZoom.toFixed(3)} → ${captureZoomLevel.toFixed(3)}, center: (${centerX}, ${centerY}), offset adjusted: (${captureViewOffsetX.toFixed(1)}, ${captureViewOffsetY.toFixed(1)})`);
    
    renderCaptureImage();
}

function startCapturePan(e) {
    console.log('🖱️ Starting capture pan');
    captureIsDragging = true;
    captureLastMouseX = e.clientX;
    captureLastMouseY = e.clientY;
    captureCanvas.style.cursor = 'grabbing';
}

function doCapturePan(e) {
    if (!captureIsDragging) return;
    
    const dx = e.clientX - captureLastMouseX;
    const dy = e.clientY - captureLastMouseY;
    
    console.log(`🖱️ Capture pan: dx=${dx}, dy=${dy}, zoom=${captureZoomLevel}`);
    
    // パンの移動量を正しく計算（座標変換と同じ方式で）
    // マウスの移動量をズームレベルで逆スケールして画像座標系での移動量に変換
    captureViewOffsetX += dx / captureZoomLevel;
    captureViewOffsetY += dy / captureZoomLevel;
    
    console.log(`🖱️ Updated offsets: (${captureViewOffsetX.toFixed(1)}, ${captureViewOffsetY.toFixed(1)})`);
    
    captureLastMouseX = e.clientX;
    captureLastMouseY = e.clientY;
    
    renderCaptureImage();
}

function endCapturePan() {
    console.log('🖱️ Ending capture pan');
    captureIsDragging = false;
    captureCanvas.style.cursor = 'grab';
}

function setCaptureImage(imageData, width, height) {
    console.log(`📸 Setting capture image: ${width}x${height}`);
    captureImageData = imageData;
    captureImageWidth = width;
    captureImageHeight = height;
    
    // 一時的なキャンバスを作成してImageDataをImageに変換
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.putImageData(imageData, 0, 0);
    
    // ImageオブジェクトとしてキャプチャImage要素を作成
    window.captureImageElement = new Image();
    window.captureImageElement.onload = function() {
        console.log('📸 Capture image loaded for rendering');
        renderCaptureImage();
    };
    window.captureImageElement.src = tempCanvas.toDataURL();
    
    // キャンバスサイズを設定
    captureCanvas.width = Math.min(width, 800);
    captureCanvas.height = Math.min(height, 600);
    
    // 初期化
    captureZoomLevel = 1;
    captureViewOffsetX = 0;
    captureViewOffsetY = 0;
    
    // 表示エリアを表示
    captureImageArea.classList.remove('hidden');
}

function renderCaptureImage() {
    if (!window.captureImageElement || !captureImageData) return;
    
    console.log(`🖼️ Rendering capture image: zoom=${captureZoomLevel}, offset=(${captureViewOffsetX}, ${captureViewOffsetY})`);
    
    captureCtx.clearRect(0, 0, captureCanvas.width, captureCanvas.height);
    
    // 変換行列を設定
    captureCtx.save();
    captureCtx.scale(captureZoomLevel, captureZoomLevel);
    captureCtx.translate(captureViewOffsetX, captureViewOffsetY);
    
    // 画像を描画（ImageElementを使用）
    captureCtx.drawImage(window.captureImageElement, 0, 0);
    
    captureCtx.restore();
    
    // デバッグ情報を更新
    updateCaptureDebugInfo();
    
    // マーキングポイントを再描画
    if (typeof redrawCaptureMarkings === 'function') {
        redrawCaptureMarkings();
    }
}

function updateCaptureDebugInfo() {
    const debugZoom = document.getElementById('debugZoom');
    const debugOffsetX = document.getElementById('debugOffsetX');
    const debugOffsetY = document.getElementById('debugOffsetY');
    const debugImageSize = document.getElementById('debugImageSize');
    const debugCanvasSize = document.getElementById('debugCanvasSize');
    
    if (debugZoom) debugZoom.textContent = captureZoomLevel.toFixed(3);
    if (debugOffsetX) debugOffsetX.textContent = captureViewOffsetX.toFixed(1);
    if (debugOffsetY) debugOffsetY.textContent = captureViewOffsetY.toFixed(1);
    if (debugImageSize) debugImageSize.textContent = `${captureImageWidth}x${captureImageHeight}`;
    if (debugCanvasSize) debugCanvasSize.textContent = `${captureCanvas.width}x${captureCanvas.height}`;
}

function hideCaptureImage() {
    console.log('📸 Hiding capture image');
    captureImageArea.classList.add('hidden');
    captureImageData = null;
    captureImageWidth = 0;
    captureImageHeight = 0;
    window.captureImageElement = null;
}

function getCaptureCanvas() {
    return captureCanvas;
}

function getCaptureContext() {
    return captureCtx;
}
