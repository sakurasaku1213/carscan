// Main application - メインアプリケーション

/**
 * キャンバスクリック処理
 * @param {MouseEvent} event - マウスイベント
 */
function handleCanvasClick(event) {
    if (videoCanvas.style.pointerEvents === 'none' || isPanning) return;
    if (measurementState === 'idle' && currentAppMode === 'none') return;

    const rect = videoCanvas.getBoundingClientRect();
    const canvasClickCoords = { 
        x: event.clientX - rect.left, 
        y: event.clientY - rect.top 
    };
    const imageCoords = toImageCoords(canvasClickCoords); 
    
    points.push(imageCoords);
    redrawDisplayCanvas(); 

    // モード別のクリック処理
    if (currentAppMode === 'dimension') {
        handleDimensionClickLogic();
    } else if (currentAppMode === 'oncoming') {
        handleOncomingAnalysisClickLogic();
    }
}

/**
 * アプリケーション初期化
 */
function initApp() {
    // メッセージボックスの閉じるボタン
    closeMessageButton.addEventListener('click', hideMessage);
    
    // キャンバスクリックイベント
    videoCanvas.addEventListener('click', handleCanvasClick);
    
    // 各モジュールの初期化
    initVideoHandler();
    initModeManager();
    initZoomPanEvents();
    initDimensionMeasurement();
    initOncomingAnalysis();
    initAIComment();
    
    console.log('CarScan Pro アプリケーションが初期化されました');
}

// DOMContentLoaded時にアプリケーションを初期化
document.addEventListener('DOMContentLoaded', initApp);
