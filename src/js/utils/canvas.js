// Canvas utilities - キャンバス描画関連のユーティリティ関数

/**
 * キャンバスに点を描画
 * @param {number} dispX - 表示X座標
 * @param {number} dispY - 表示Y座標
 * @param {string} color - 色
 * @param {number} radius - 半径
 */
function drawPointOnCanvas(dispX, dispY, color = 'yellow', radius = 5) {
    visibleCtx.fillStyle = color;
    visibleCtx.beginPath();
    visibleCtx.arc(dispX, dispY, radius / zoomLevel, 0, Math.PI * 2); 
    visibleCtx.fill();
}

/**
 * キャンバスに線を描画
 * @param {Object} dispP1 - 開始点の表示座標 {x, y}
 * @param {Object} dispP2 - 終了点の表示座標 {x, y}
 * @param {string} color - 色
 * @param {number} lineWidth - 線の太さ
 */
function drawLineOnCanvas(dispP1, dispP2, color = 'blue', lineWidth = 2) {
    visibleCtx.strokeStyle = color;
    visibleCtx.lineWidth = lineWidth / zoomLevel; 
    visibleCtx.beginPath();
    visibleCtx.moveTo(dispP1.x, dispP1.y);
    visibleCtx.lineTo(dispP2.x, dispP2.y);
    visibleCtx.stroke();
}

/**
 * キャンバスの表示内容を再描画
 */
function redrawDisplayCanvas() {
    if (!sourceFrameCanvas || sourceFrameCanvas.width === 0) return;
    
    visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    
    // フレーム描画
    const sourceX = viewOffsetX;
    const sourceY = viewOffsetY;
    const sourceWidth = videoCanvas.width / zoomLevel;
    const sourceHeight = videoCanvas.height / zoomLevel;
    
    visibleCtx.drawImage(
        sourceFrameCanvas,
        sourceX, sourceY, sourceWidth, sourceHeight,
        0, 0, videoCanvas.width, videoCanvas.height
    );
    
    // 描画された要素を再表示
    if (typeof redrawDimensionElements === 'function' && currentAppMode === 'dimension') {
        redrawDimensionElements();
    } else if (typeof redrawOncomingElements === 'function' && currentAppMode === 'oncoming') {
        redrawOncomingElements();
    }
}

/**
 * 現在のフレームをソースキャンバスにキャプチャ
 */
function captureCurrentFrame() {
    if (videoPlayer.readyState >= 2) {
        sourceFrameCtx.drawImage(videoPlayer, 0, 0, videoNaturalWidth, videoNaturalHeight);
        return true;
    }
    return false;
}

/**
 * 現在のフレームをキャプチャエリアに表示
 */
function captureFrameToImageArea() {
    if (videoPlayer.readyState >= 2) {
        // ソースキャンバスにキャプチャ
        sourceFrameCtx.drawImage(videoPlayer, 0, 0, videoNaturalWidth, videoNaturalHeight);
        
        // キャプチャ画像用のImageDataを取得
        const imageData = sourceFrameCtx.getImageData(0, 0, videoNaturalWidth, videoNaturalHeight);
        
        // キャプチャエリアに表示
        setCaptureImage(imageData, videoNaturalWidth, videoNaturalHeight);
        
        console.log(`📸 Frame captured to image area: ${videoNaturalWidth}x${videoNaturalHeight}`);
        return true;
    }
    return false;
}
