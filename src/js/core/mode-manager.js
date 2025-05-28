// Mode manager - モード管理機能

/**
 * アプリケーションモードを設定
 * @param {string} mode - モード ('dimension', 'oncoming', 'none')
 */
function setAppMode(mode) {
    currentAppMode = mode;
    resetAllMeasurementStates(); 
    
    // モードボタンのアクティブ状態更新
    dimensionModeButton.classList.toggle('active', mode === 'dimension');
    oncomingAnalysisModeButton.classList.toggle('active', mode === 'oncoming');

    // コントロールエリアの表示/非表示
    dimensionControlsArea.classList.toggle('hidden', mode !== 'dimension');
    oncomingAnalysisControlsArea.classList.toggle('hidden', mode !== 'oncoming');
    startVehicleMarkingButton.classList.add('hidden');
    
    dimensionMeasurementInputs.classList.toggle('hidden', mode !== 'dimension');
    zoomControlsContainer.classList.add('hidden'); 
    
    sharedControlsContainer.classList.add('hidden'); 
    resultsArea.classList.add('hidden'); 
    dimensionResultsDisplay.classList.add('hidden');
    oncomingAnalysisResultsDisplay.classList.add('hidden');
    
    // キャンバス状態をリセット
    videoCanvas.style.display = 'none'; 
    videoCanvas.style.pointerEvents = 'none'; 
    videoCanvas.style.cursor = 'default';
    if (visibleCtx) {
        visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    }

    // モード別のUI更新
    if (mode === 'dimension') {
        appSubtitle.textContent = "寸法測定モード: 参照物を使って長さを測ります。";
        showUIMessage(commonInstructionText, "動画を一時停止し、「現在のフレームで寸法測定開始」を押してください。");
        
    } else if (mode === 'oncoming') {
        appSubtitle.textContent = "対向車進路分析モード: 2フレーム間の車両の向きの変化を分析します。";
        showUIMessage(oncomingAnalysisInstructionText, "分析したい最初のフレームで動画を一時停止し、「このフレームをキャプチャ (1回目)」を押してください。");
        captureFrameButton.textContent = "このフレームをキャプチャ (1回目)";
        oncomingMarkingStep = 0;
        
    } else {
        appSubtitle.textContent = "高度動画解析ツール - 寸法測定・軌跡追跡・速度分析";
    }
}

/**
 * 全測定状態をリセット
 */
function resetAllMeasurementStates() {
    if (typeof resetDimensionState === 'function') {
        resetDimensionState();
    }
    if (typeof resetOncomingAnalysisState === 'function') {
        resetOncomingAnalysisState();
    }
    measurementState = 'idle';
}

/**
 * 全測定状態の完全リセット
 */
function resetAllMeasurementStatesComplete() {
    points = []; 
    pointsForRefLine = []; 
    pointsForTargetLine = [];
    measurementState = 'idle';
    refPixelLength = 0; 
    scale = 0; 
    currentEstimatedSizeMm = 0;
    vehicleSnapshot1 = { points: [], time: 0, angle: null, frameCaptured: false };
    vehicleSnapshot2 = { points: [], time: 0, angle: null, frameCaptured: false };
    oncomingMarkingStep = 0;

    if (videoCanvas) {
        videoCanvas.style.display = 'none'; 
        videoCanvas.style.pointerEvents = 'none';
        videoCanvas.style.cursor = 'default';
    }
    
    if (visibleCtx) {
        visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    }

    // 結果表示を更新
    if (typeof updateDimensionResultsDisplay === 'function') {
        updateDimensionResultsDisplay(); 
    }
    if (typeof updateOncomingAnalysisResultsDisplay === 'function') {
        updateOncomingAnalysisResultsDisplay(); 
    }
    
    // AIコメント関連をリセット
    if (aiCommentText) aiCommentText.textContent = '';
    if (targetObjectNameInput) targetObjectNameInput.value = '';
    if (getAiCommentButton) getAiCommentButton.disabled = true;
    if (aiCommentSection) aiCommentSection.classList.add('hidden');
    if (startVehicleMarkingButton) startVehicleMarkingButton.classList.add('hidden');
    if (captureFrameButton) captureFrameButton.disabled = false;
}

/**
 * 現在のモードをリセット
 */
function resetCurrentMode() {
    if (currentAppMode === 'dimension') {
        resetDimensionState();
        showUIMessage(dimensionStatusText, "リセット完了");
        showUIMessage(commonInstructionText, "動画を一時停止し、「現在のフレームで寸法測定開始」を押してください。");
        
        // AIコメントセクションを非表示
        aiCommentSection.classList.add('hidden');
        getAiCommentButton.disabled = true;
        aiCommentText.textContent = "";
        
    } else if (currentAppMode === 'oncoming') {
        resetOncomingAnalysisState();
    }
    
    // 共通のリセット処理
    videoCanvas.style.display = 'none';
    videoCanvas.style.pointerEvents = 'none';
    sharedControlsContainer.classList.add('hidden');
    resultsArea.classList.add('hidden');
    
    if (visibleCtx) {
        visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    }
}

/**
 * モード管理機能を初期化
 */
function initModeManager() {
    // モード選択ボタンのイベントリスナー
    dimensionModeButton.addEventListener('click', () => setAppMode('dimension'));
    oncomingAnalysisModeButton.addEventListener('click', () => setAppMode('oncoming'));
    
    // リセットボタンのイベントリスナー
    resetCurrentModeButton.addEventListener('click', resetCurrentMode);
}
