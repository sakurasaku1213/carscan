// Video handler - 動画処理機能

/**
 * 動画ファイル読み込み処理
 */
function handleVideoFileLoad(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // ローディング開始
    loadingIndicator.classList.remove('hidden'); 
    loadingIndicator.classList.add('flex');
    
    const fileURL = URL.createObjectURL(file);
    videoPlayer.src = fileURL;
    
    // UI状態をリセット
    modeSelectionContainer.classList.remove('hidden');
    dimensionControlsArea.classList.add('hidden');
    oncomingAnalysisControlsArea.classList.add('hidden');
    startVehicleMarkingButton.classList.add('hidden');
    sharedControlsContainer.classList.add('hidden');
    resultsArea.classList.add('hidden');
    dimensionResultsDisplay.classList.add('hidden');
    oncomingAnalysisResultsDisplay.classList.add('hidden');
    
    resetAllApplicationStates(); 
    
    // メタデータ読み込み完了時の処理
    videoPlayer.onloadedmetadata = () => {
        videoNaturalWidth = videoPlayer.videoWidth;
        videoNaturalHeight = videoPlayer.videoHeight;
        
        // ソースフレームキャンバスのサイズ設定
        sourceFrameCanvas.width = videoNaturalWidth; 
        sourceFrameCanvas.height = videoNaturalHeight;
        
        // 表示用キャンバスのサイズ設定
        const displayWidth = videoPlayer.clientWidth; 
        const displayHeight = videoPlayer.clientHeight;
        videoCanvas.width = displayWidth; 
        videoCanvas.height = displayHeight;
        videoCanvas.style.width = `${displayWidth}px`; 
        videoCanvas.style.height = `${displayHeight}px`;
        videoCanvas.style.pointerEvents = 'none';
        videoCanvas.style.display = 'none'; 
        
        // ローディング終了
        loadingIndicator.classList.add('hidden'); 
        loadingIndicator.classList.remove('flex');
        
        resetZoomAndPan();
        setAppMode('none'); 
    };
    
    // エラー処理
    videoPlayer.onerror = () => {
        showMessage("動画ファイルの読み込みに失敗しました。");
        loadingIndicator.classList.add('hidden'); 
        loadingIndicator.classList.remove('flex');
    };
}

/**
 * ウィンドウリサイズ処理
 */
function handleWindowResize() {
    if (videoPlayer.src && videoPlayer.readyState >= 2) {
        const displayWidth = videoPlayer.clientWidth; 
        const displayHeight = videoPlayer.clientHeight;
        videoCanvas.width = displayWidth; 
        videoCanvas.height = displayHeight;
        videoCanvas.style.width = `${displayWidth}px`; 
        videoCanvas.style.height = `${displayHeight}px`;
        
        if (measurementState !== 'idle' && 
            sharedControlsContainer.classList.contains('hidden') === false && 
            videoCanvas.style.display === 'block') {
            applyPanBoundaries();
            redrawDisplayCanvas();
        }
    }
}

/**
 * 全アプリケーション状態をリセット
 */
function resetAllApplicationStates() {
    if (typeof resetDimensionState === 'function') {
        resetDimensionState();
    }
    if (typeof resetOncomingAnalysisState === 'function') {
        resetOncomingAnalysisState();
    }
    resetZoomAndPan();
    
    if (visibleCtx) {
        visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    }
}

/**
 * 動画ハンドラーを初期化
 */
function initVideoHandler() {
    videoFile.addEventListener('change', handleVideoFileLoad);
    window.addEventListener('resize', handleWindowResize);
}
