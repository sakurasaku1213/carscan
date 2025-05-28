// Capture Image Marking - キャプチャ画像上でのマーキング機能

// キャプチャ画像上でのマーキング用変数
let captureMarkingPoints = [];
let captureMarkingState = '';
let captureIsCrosshairMode = false;

function initializeCaptureMarking() {
    // DOM要素の存在チェック
    if (!captureCanvas) {
        console.warn('📍 Capture canvas not found, skipping marking initialization');
        return;
    }
    
    console.log('📍 Initializing capture marking functionality');
    
    // キャプチャキャンバスのクリックイベント
    captureCanvas.addEventListener('click', handleCaptureClick);
    
    // リアルタイムマウス座標追跡を初期化
    initializeCaptureMouseTracking();
}

function handleCaptureClick(e) {
    if (!captureIsCrosshairMode || captureIsDragging) return;
    
    const rect = captureCanvas.getBoundingClientRect();
    // CSSサイズと実ピクセルサイズの比率を考慮
    const scaleX = captureCanvas.width / rect.width;
    const scaleY = captureCanvas.height / rect.height;
    const canvasX = (e.clientX - rect.left) * scaleX;
    const canvasY = (e.clientY - rect.top) * scaleY;
    
    // より詳細なデバッグ情報
    console.log(`📍 === CLICK DEBUG START ===`);
    console.log(`📍 Raw coordinates:`, {
        clientX: e.clientX,
        clientY: e.clientY,
        rectLeft: rect.left,
        rectTop: rect.top,
        rectWidth: rect.width,
        rectHeight: rect.height
    });
    
    console.log(`📍 Canvas coordinates:`, {
        canvasX: canvasX,
        canvasY: canvasY,
        canvasWidth: captureCanvas.width,
        canvasHeight: captureCanvas.height
    });
    
    console.log(`📍 Transform state:`, {
        zoom: captureZoomLevel,
        offsetX: captureViewOffsetX,
        offsetY: captureViewOffsetY,
        imageWidth: captureImageWidth,
        imageHeight: captureImageHeight
    });
    
    // 複数の座標変換方式を試してデバッグ
    const method1_X = (canvasX / captureZoomLevel) - captureViewOffsetX;
    const method1_Y = (canvasY / captureZoomLevel) - captureViewOffsetY;
    
    const method2_X = canvasX / captureZoomLevel - captureViewOffsetX;
    const method2_Y = canvasY / captureZoomLevel - captureViewOffsetY;
    
    // Canvas変換行列を考慮した方法
    const method3_X = (canvasX - captureViewOffsetX * captureZoomLevel) / captureZoomLevel;
    const method3_Y = (canvasY - captureViewOffsetY * captureZoomLevel) / captureZoomLevel;
      console.log(`📍 Transformation methods:`, {
        method1: `(${method1_X.toFixed(1)}, ${method1_Y.toFixed(1)}) - (canvas/zoom) - offset`,
        method2: `(${method2_X.toFixed(1)}, ${method2_Y.toFixed(1)}) - canvas/zoom - offset (same as method1)`,
        method3: `(${method3_X.toFixed(1)}, ${method3_Y.toFixed(1)}) - (canvas - offset*zoom) / zoom`
    });
    
    // Canvas変換行列に基づく正しい逆変換を選択
    // renderCaptureImage()では: scale(zoom) → translate(offset) → drawImage(0,0)
    // つまり画像の(x,y)は画面上で(x+offset)*zoom座標に表示される
    // 逆変換: 画面座標canvasCoordから画像座標 = canvasCoord/zoom - offset
    const imageX = canvasX / captureZoomLevel - captureViewOffsetX;
    const imageY = canvasY / captureZoomLevel - captureViewOffsetY;
    
    console.log(`📍 Final selected coordinates:`, {
        imageX: imageX.toFixed(1),
        imageY: imageY.toFixed(1)
    });
    
    // 画像範囲内かチェック（実際の画像サイズに対して）
    if (imageX < 0 || imageY < 0 || imageX >= captureImageWidth || imageY >= captureImageHeight) {
        console.log(`📍 Click outside image bounds:`, {
            x: imageX < 0 ? `left (${imageX.toFixed(1)})` : imageX >= captureImageWidth ? `right (${imageX.toFixed(1)} >= ${captureImageWidth})` : 'valid',
            y: imageY < 0 ? `top (${imageY.toFixed(1)})` : imageY >= captureImageHeight ? `bottom (${imageY.toFixed(1)} >= ${captureImageHeight})` : 'valid'
        });
        console.log(`📍 === CLICK DEBUG END (OUT OF BOUNDS) ===`);
        return;
    }
      // ポイントを追加
    const point = { x: imageX, y: imageY };
    captureMarkingPoints.push(point);
    
    console.log(`📍 Added marking point #${captureMarkingPoints.length}:`, {
        x: point.x.toFixed(1),
        y: point.y.toFixed(1)
    });
    console.log(`📍 === CLICK DEBUG END ===`);
    
    // デバッグ情報を更新
    updateDebugLastClick(point);
    
    // 画像を再描画してマーキングを表示
    renderCaptureImage();
    
    // 状態に応じた処理
    if (typeof handleOncomingCaptureClick === 'function') {
        handleOncomingCaptureClick(point, captureMarkingPoints.length);
    }
}

function setCaptureMarkingMode(active, state = '') {
    console.log(`📍 Setting capture marking mode: ${active}, state: ${state}`);
    captureIsCrosshairMode = active;
    captureMarkingState = state;
    
    if (active) {
        captureCanvas.style.cursor = 'crosshair';
        captureCanvas.classList.add('crosshair-mode');
    } else {
        captureCanvas.style.cursor = 'grab';
        captureCanvas.classList.remove('crosshair-mode');
        captureMarkingPoints = [];
    }
}

function getCaptureMarkingPoints() {
    return [...captureMarkingPoints];
}

function clearCaptureMarkingPoints() {
    console.log('📍 Clearing capture marking points');
    captureMarkingPoints = [];
    renderCaptureImage(); // 再描画してマーキングを削除
}

function updateDebugLastClick(point) {
    const debugLastClick = document.getElementById('debugLastClick');
    if (debugLastClick) {
        debugLastClick.textContent = `${point.x.toFixed(1)}, ${point.y.toFixed(1)}`;
    }
}

function redrawCaptureMarkings() {
    if (captureMarkingPoints.length === 0) return;
    
    console.log(`📍 Redrawing ${captureMarkingPoints.length} capture markings`);
    
    // 現在の変換行列の状態を保存
    captureCtx.save();
    
    // 変換行列を適用（ズーム・パンの現在の状態を適用）
    captureCtx.scale(captureZoomLevel, captureZoomLevel);
    captureCtx.translate(captureViewOffsetX, captureViewOffsetY);
    
    captureMarkingPoints.forEach((point, index) => {
        // ポイントの色設定
        captureCtx.fillStyle = index === 0 ? '#FFD700' : '#FF4444'; // 1番目は金色、それ以外は赤
        captureCtx.strokeStyle = '#000000';
        captureCtx.lineWidth = 2 / captureZoomLevel; // ズームに応じて線幅調整
        
        // マーキングポイントを描画（円）
        captureCtx.beginPath();
        const radius = 8 / captureZoomLevel; // ズームに応じてサイズ調整
        captureCtx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        captureCtx.fill();
        captureCtx.stroke();
        
        // ポイント番号を表示
        captureCtx.fillStyle = '#FFFFFF';
        captureCtx.strokeStyle = '#000000';
        captureCtx.font = `bold ${14 / captureZoomLevel}px Arial`; // ズームに応じてフォントサイズ調整
        captureCtx.textAlign = 'center';
        captureCtx.textBaseline = 'middle';
        captureCtx.lineWidth = 1 / captureZoomLevel;
        
        const text = (index + 1).toString();
        captureCtx.strokeText(text, point.x, point.y);
        captureCtx.fillText(text, point.x, point.y);
        
        console.log(`📍 Drew marking point #${index + 1} at (${point.x.toFixed(1)}, ${point.y.toFixed(1)})`);
    });
    
    // 変換行列の状態を復元
    captureCtx.restore();
}

// リアルタイムデバッグ用のマウス座標追跡
function initializeCaptureMouseTracking() {
    if (!captureCanvas) return;
    
    captureCanvas.addEventListener('mousemove', (e) => {
        const rect = captureCanvas.getBoundingClientRect();
        const canvasX = e.clientX - rect.left;
        const canvasY = e.clientY - rect.top;
        
        // 現在のマウス位置での画像座標を計算
        const imageX = (canvasX / captureZoomLevel) - captureViewOffsetX;
        const imageY = (canvasY / captureZoomLevel) - captureViewOffsetY;
        
        // デバッグ表示を更新
        updateDebugMousePosition(canvasX, canvasY, imageX, imageY);
    });
}

function updateDebugMousePosition(canvasX, canvasY, imageX, imageY) {
    const debugMousePos = document.getElementById('debugMousePos');
    const debugTransformTest = document.getElementById('debugTransformTest');
    
    if (debugMousePos) {
        debugMousePos.textContent = `${canvasX.toFixed(0)}, ${canvasY.toFixed(0)}`;
    }
    
    if (debugTransformTest) {
        debugTransformTest.textContent = `${imageX.toFixed(1)}, ${imageY.toFixed(1)}`;
    }
}
