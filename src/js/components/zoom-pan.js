// Zoom and Pan functionality - ズーム・パン機能

/**
 * ズーム・パンをリセット
 */
function resetZoomAndPan() {
    zoomLevel = 1.0;
    viewOffsetX = 0;
    viewOffsetY = 0;
    isPanning = false;
}

/**
 * ズームイン
 */
function zoomIn() {
    if (zoomLevel < MAX_ZOOM) {
        const centerX = videoCanvas.width / 2;
        const centerY = videoCanvas.height / 2;
        const imagePointBeforeZoom = toImageCoords({ x: centerX, y: centerY });
        
        zoomLevel += ZOOM_STEP;
        zoomLevel = Math.min(zoomLevel, MAX_ZOOM);
        
        const imagePointAfterZoom = toImageCoords({ x: centerX, y: centerY });
        viewOffsetX += imagePointBeforeZoom.x - imagePointAfterZoom.x;
        viewOffsetY += imagePointBeforeZoom.y - imagePointAfterZoom.y;
        
        applyPanBoundaries();
        redrawDisplayCanvas();
    }
}

/**
 * ズームアウト
 */
function zoomOut() {
    if (zoomLevel > MIN_ZOOM) {
        const centerX = videoCanvas.width / 2;
        const centerY = videoCanvas.height / 2;
        const imagePointBeforeZoom = toImageCoords({ x: centerX, y: centerY });
        
        zoomLevel -= ZOOM_STEP;
        zoomLevel = Math.max(zoomLevel, MIN_ZOOM);
        
        const imagePointAfterZoom = toImageCoords({ x: centerX, y: centerY });
        viewOffsetX += imagePointBeforeZoom.x - imagePointAfterZoom.x;
        viewOffsetY += imagePointBeforeZoom.y - imagePointAfterZoom.y;
        
        applyPanBoundaries();
        redrawDisplayCanvas();
    }
}

/**
 * ズームリセット
 */
function resetZoom() {
    resetZoomAndPan();
    redrawDisplayCanvas();
}

/**
 * パンの境界を適用
 */
function applyPanBoundaries() {
    const maxOffsetX = Math.max(0, videoNaturalWidth - (videoCanvas.width / zoomLevel));
    const maxOffsetY = Math.max(0, videoNaturalHeight - (videoCanvas.height / zoomLevel));
    
    viewOffsetX = Math.max(0, Math.min(viewOffsetX, maxOffsetX));
    viewOffsetY = Math.max(0, Math.min(viewOffsetY, maxOffsetY));
}

/**
 * パン開始
 * @param {MouseEvent} e - マウスイベント
 */
function startPan(e) {
    isPanning = true;
    const rect = videoCanvas.getBoundingClientRect();
    lastPanX = e.clientX - rect.left;
    lastPanY = e.clientY - rect.top;
    videoCanvas.style.cursor = 'grabbing';
}

/**
 * パン実行
 * @param {MouseEvent} e - マウスイベント
 */
function doPan(e) {
    if (!isPanning) return;
    
    const rect = videoCanvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    const deltaX = (lastPanX - currentX) / zoomLevel;
    const deltaY = (lastPanY - currentY) / zoomLevel;
    
    viewOffsetX += deltaX;
    viewOffsetY += deltaY;
    
    applyPanBoundaries();
    redrawDisplayCanvas();
    
    lastPanX = currentX;
    lastPanY = currentY;
}

/**
 * パン終了
 */
function endPan() {
    isPanning = false;
    // モードに応じて適切なカーソルに戻す
    const isInActiveMarkingMode = measurementState.includes('_click');
    if (isInActiveMarkingMode) {
        videoCanvas.style.cursor = 'crosshair';
    } else if (zoomLevel > 1.0) {
        videoCanvas.style.cursor = 'grab';
    } else {
        videoCanvas.style.cursor = 'default';
    }
}

/**
 * ズーム・パンのイベントリスナーを初期化
 */
function initZoomPanEvents() {
    // ズームボタンのイベント
    zoomInButton.addEventListener('click', zoomIn);
    zoomOutButton.addEventListener('click', zoomOut);
    zoomResetButton.addEventListener('click', resetZoom);    // マウスイベント
    videoCanvas.addEventListener('mousedown', (e) => {
        if (e.button === 0 && zoomLevel > 1.0) { // 左クリック & ズーム時のみパン
            // フレームキャプチャ後やマーキング待機中でもパンを許可
            const isInActiveMarkingMode = measurementState.includes('_click');
            console.log('MouseDown - measurementState:', measurementState, 'isInActiveMarkingMode:', isInActiveMarkingMode, 'zoomLevel:', zoomLevel);
            if (!isInActiveMarkingMode) {
                console.log('Starting pan...');
                startPan(e);
                e.preventDefault();
            }
        }
    });
      videoCanvas.addEventListener('mousemove', (e) => {
        doPan(e);
        // ズーム時かつアクティブなマーキング中でない場合はgrabカーソルを表示
        const isInActiveMarkingMode = measurementState.includes('_click');
        if (!isPanning && zoomLevel > 1.0 && !isInActiveMarkingMode) {
            videoCanvas.style.cursor = 'grab';
        }
    });
    
    document.addEventListener('mouseup', endPan);
    
    // タッチイベント（モバイル対応）
    videoCanvas.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1 && zoomLevel > 1.0) {
            const touch = e.touches[0];
            const rect = videoCanvas.getBoundingClientRect();
            const mockEvent = {
                clientX: touch.clientX,
                clientY: touch.clientY,
                button: 0
            };
            startPan(mockEvent);
            e.preventDefault();
        }
    });
    
    videoCanvas.addEventListener('touchmove', (e) => {
        if (e.touches.length === 1 && isPanning) {
            const touch = e.touches[0];
            const mockEvent = {
                clientX: touch.clientX,
                clientY: touch.clientY
            };
            doPan(mockEvent);
            e.preventDefault();
        }
    });
    
    document.addEventListener('touchend', endPan);
}
