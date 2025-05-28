// Dimension measurement functionality - 寸法測定機能

/**
 * 寸法測定を開始
 */
function startDimensionMeasurement() {
    if (!videoPlayer.src || videoPlayer.paused === false) { 
        showMessage("動画を一時停止してください。"); 
        return; 
    }
    if (videoPlayer.readyState < 2) { 
        showMessage("動画データ未読込。"); 
        return; 
    }
    
    videoPlayer.pause();
    
    // 現在のフレームをキャプチャ
    if (!captureCurrentFrame()) {
        showMessage("フレームのキャプチャに失敗しました。");
        return;
    }

    // UIを測定モードに切り替え
    videoCanvas.style.display = 'block'; 
    videoCanvas.style.pointerEvents = 'auto';
    videoCanvas.style.cursor = 'crosshair';
    sharedControlsContainer.classList.remove('hidden'); 
    zoomControlsContainer.classList.remove('hidden');
    dimensionMeasurementInputs.classList.remove('hidden'); 
    resultsArea.classList.remove('hidden');
    dimensionResultsDisplay.classList.remove('hidden');
    oncomingAnalysisResultsDisplay.classList.add('hidden');
    
    showUIMessage(commonInstructionText, "参照オブジェクトの実際のサイズを入力し、参照オブジェクトの始点と終点をクリックしてください。");
    showUIMessage(dimensionStatusText, "参照オブジェクトのサイズ入力待ち");
    
    measurementState = 'dim_waiting_ref1';
    resetDimensionState();
    resetZoomAndPan();
    updateDimensionResultsDisplay();
    redrawDisplayCanvas();
}

/**
 * 寸法測定状態をリセット
 */
function resetDimensionState() {
    points = []; 
    pointsForRefLine = []; 
    pointsForTargetLine = [];
    refPixelLength = 0;
    scale = 0;
    currentEstimatedSizeMm = 0;
    measurementState = 'idle';
}

/**
 * 寸法測定のクリック処理
 */
function handleDimensionClickLogic() {
    if (measurementState === 'dim_waiting_ref1') {
        const refActualSize = parseFloat(refObjectActualSizeInput.value);
        if (isNaN(refActualSize) || refActualSize <= 0) {
            showMessage("参照オブジェクトの実際のサイズを正しく入力してください。");
            points = []; 
            redrawDisplayCanvas(); 
            return;
        }
        showUIMessage(dimensionStatusText, "参照オブジェクトの終点待ち");
        showUIMessage(commonInstructionText, "参照オブジェクトの終点をクリックしてください。");
        measurementState = 'dim_waiting_ref2';
        
    } else if (measurementState === 'dim_waiting_ref2') {
        if (points.length === 2) {
            pointsForRefLine = [...points];
            refPixelLength = calculateDistance(pointsForRefLine[0], pointsForRefLine[1]);
            const refActualSize = parseFloat(refObjectActualSizeInput.value);
            
            if (refPixelLength > 0 && refActualSize > 0) {
                scale = refActualSize / refPixelLength;
                showUIMessage(dimensionStatusText, "スケール計算完了。対象オブジェクトの始点待ち。");
                showUIMessage(commonInstructionText, "測定したい対象オブジェクトの始点をクリックしてください。");
                measurementState = 'dim_waiting_target1';
                refPixelLengthText.textContent = refPixelLength.toFixed(2);
                scaleText.textContent = scale.toFixed(4);
                points = []; 
            } else { 
                showMessage("参照オブジェクトのピクセル長が0です。異なる2点をクリックしてください。");
                points = []; 
                pointsForRefLine = []; 
                measurementState = 'dim_waiting_ref1';
                showUIMessage(dimensionStatusText, "参照オブジェクトの始点待ち");
                showUIMessage(commonInstructionText, "参照オブジェクトの始点を再度クリックしてください。");
            }
            redrawDisplayCanvas();
        }
        
    } else if (measurementState === 'dim_waiting_target1') {
        showUIMessage(dimensionStatusText, "対象オブジェクトの終点待ち");
        showUIMessage(commonInstructionText, "測定したい対象オブジェクトの終点をクリックしてください。");
        measurementState = 'dim_waiting_target2';
        
    } else if (measurementState === 'dim_waiting_target2') {
        if (points.length === 2) {
            pointsForTargetLine = [...points];
            const targetPixelLengthVal = calculateDistance(pointsForTargetLine[0], pointsForTargetLine[1]);
            
            if (scale > 0 && targetPixelLengthVal > 0) {
                currentEstimatedSizeMm = targetPixelLengthVal * scale;
                showUIMessage(dimensionStatusText, "測定完了");
                showUIMessage(commonInstructionText, "測定が完了しました。対象物の名前を入力してAIコメントを生成できます。");
                targetPixelLengthText.textContent = targetPixelLengthVal.toFixed(2);
                estimatedSizeText.textContent = currentEstimatedSizeMm.toFixed(2);
                measurementState = 'dim_done'; 
                
                // AIコメント機能を有効化
                aiCommentSection.classList.remove('hidden');
                getAiCommentButton.disabled = false;
                
                // パンモードに切り替え
                videoCanvas.style.pointerEvents = 'auto'; 
                videoCanvas.style.cursor = 'grab';
                
                // 測定完了イベントを発火
                document.dispatchEvent(new CustomEvent('measurementComplete'));
                
            } else { 
                showMessage("対象オブジェクトのピクセル長が0またはスケールが未設定です。");
                points = []; 
                pointsForTargetLine = []; 
                measurementState = 'dim_waiting_target1';
                showUIMessage(dimensionStatusText, "対象オブジェクトの始点待ち");
                showUIMessage(commonInstructionText, "対象オブジェクトの始点を再度クリックしてください。");
            }
            redrawDisplayCanvas();
        }
    }
    
    updateDimensionResultsDisplay();
}

/**
 * 寸法測定結果表示を更新
 */
function updateDimensionResultsDisplay() {
    refPixelLengthText.textContent = refPixelLength > 0 ? refPixelLength.toFixed(2) : '-';
    scaleText.textContent = scale > 0 ? scale.toFixed(4) : '-';
    targetPixelLengthText.textContent = '-'; 
    estimatedSizeText.textContent = '-'; 
    
    if (measurementState === 'idle' || !dimensionResultsDisplay.classList.contains('hidden')) { 
        showUIMessage(dimensionStatusText, measurementState.startsWith('dim_') ? dimensionStatusText.textContent : "待機中");
    }
}

/**
 * 寸法測定状態の完全リセット
 */
function resetDimensionMeasurementState() {
    points = []; 
    pointsForRefLine = []; 
    pointsForTargetLine = [];
    measurementState = 'idle'; 
    refPixelLength = 0; 
    scale = 0; 
    currentEstimatedSizeMm = 0;
    
    updateDimensionResultsDisplay();
    
    // AIコメント関連をリセット
    aiCommentText.textContent = ''; 
    targetObjectNameInput.value = '';
    getAiCommentButton.disabled = true; 
    aiCommentSection.classList.add('hidden');
    
    if (sourceFrameCanvas.width > 0 && currentAppMode === 'dimension') { 
        videoCanvas.style.display = 'block';
        videoCanvas.style.pointerEvents = 'auto';
        videoCanvas.style.cursor = 'crosshair';
        measurementState = 'dim_waiting_ref1';
        showUIMessage(commonInstructionText, "参照オブジェクトの実際のサイズを入力し、参照オブジェクトの始点と終点をクリックしてください。");
        showUIMessage(dimensionStatusText, "参照オブジェクトのサイズ入力待ち");
        resetZoomAndPan(); 
        redrawDisplayCanvas();
    } else {
        videoCanvas.style.display = 'none';
        videoCanvas.style.pointerEvents = 'none';
        videoCanvas.style.cursor = 'default';
        if (visibleCtx) visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    }
}

/**
 * 寸法測定の描画要素を再描画
 */
function redrawDimensionElements() {
    // 参照線の描画
    if (pointsForRefLine.length === 2) {
        const refP1Display = toDisplayCoords(pointsForRefLine[0]);
        const refP2Display = toDisplayCoords(pointsForRefLine[1]);
        if (refP1Display && refP2Display) {
            drawLineOnCanvas(refP1Display, refP2Display, 'red', 3);
            drawPointOnCanvas(refP1Display.x, refP1Display.y, 'red', 6);
            drawPointOnCanvas(refP2Display.x, refP2Display.y, 'red', 6);
        }
    }
    
    // 対象線の描画
    if (pointsForTargetLine.length === 2) {
        const targetP1Display = toDisplayCoords(pointsForTargetLine[0]);
        const targetP2Display = toDisplayCoords(pointsForTargetLine[1]);
        if (targetP1Display && targetP2Display) {
            drawLineOnCanvas(targetP1Display, targetP2Display, 'blue', 3);
            drawPointOnCanvas(targetP1Display.x, targetP1Display.y, 'blue', 6);
            drawPointOnCanvas(targetP2Display.x, targetP2Display.y, 'blue', 6);
        }
    }
    
    // 現在選択中の点の描画
    if (measurementState.startsWith('dim_')) {
        points.forEach((point, index) => {
            const displayPoint = toDisplayCoords(point);
            if (displayPoint) {
                const color = measurementState.includes('ref') ? 'red' : 'blue';
                drawPointOnCanvas(displayPoint.x, displayPoint.y, color, 5);
            }
        });
    }
}

/**
 * 寸法測定機能を初期化
 */
function initDimensionMeasurement() {
    startDimensionMeasurementButton.addEventListener('click', startDimensionMeasurement);
}
