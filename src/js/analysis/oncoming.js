// Oncoming vehicle analysis functionality - 対向車進路分析機能

/**
 * フレームキャプチャ処理
 */
function captureFrame() {
    if (!videoPlayer.src || videoPlayer.paused === false) { 
        showMessage("動画を一時停止してください。"); 
        return; 
    }
    if (videoPlayer.readyState < 2) { 
        showMessage("動画データ未読込。"); 
        return; 
    }
    
    videoPlayer.pause();
      // 現在のフレームをキャプチャエリアに表示
    if (!captureFrameToImageArea()) {
        showMessage("フレームのキャプチャに失敗しました。");
        return;
    }
    
    // 従来のキャプチャも実行（互換性のため - ただし表示はしない）
    if (!captureCurrentFrame()) {
        showMessage("フレームのキャプチャに失敗しました。");
        return;
    }

    // 動画キャンバスを非表示にして、専用エリアでの操作に切り替え
    videoCanvas.style.display = 'none';
    videoCanvas.style.pointerEvents = 'none';

    sharedControlsContainer.classList.remove('hidden'); 
    zoomControlsContainer.classList.remove('hidden');
    dimensionMeasurementInputs.classList.add('hidden'); 
    resultsArea.classList.remove('hidden'); 
    oncomingAnalysisResultsDisplay.classList.remove('hidden');
    dimensionResultsDisplay.classList.add('hidden');

    if (oncomingMarkingStep < 1) { 
        // 1回目のフレームキャプチャ
        oncomingMarkingStep = 0.5; 
        vehicleSnapshot1.frameCaptured = true;
        vehicleSnapshot1.points = []; 
        showUIMessage(oncomingAnalysisInstructionText, "フレーム1をキャプチャしました。良ければ「この車両をマーク(1回目)」を押してマーキングを開始してください。フレームを調整する場合は再度キャプチャしてください。");
        startVehicleMarkingButton.textContent = "この車両をマーク (1回目)";
        startVehicleMarkingButton.classList.remove('hidden');
        captureFrameButton.textContent = "このフレームを再キャプチャ (1回目)";
        
    } else if (oncomingMarkingStep >= 1 && oncomingMarkingStep < 2) { 
        // 2回目のフレームキャプチャ
        oncomingMarkingStep = 1.7; 
        vehicleSnapshot2.frameCaptured = true;
        vehicleSnapshot2.points = []; 
        showUIMessage(oncomingAnalysisInstructionText, "フレーム2をキャプチャしました。良ければ「この車両をマーク(2回目)」を押してマーキングを開始してください。フレームを調整する場合は再度キャプチャしてください。");
        startVehicleMarkingButton.textContent = "この車両をマーク (2回目)";
        startVehicleMarkingButton.classList.remove('hidden');
        captureFrameButton.textContent = "このフレームを再キャプチャ (2回目)";
        
    } else if (oncomingMarkingStep === 3) { 
        // 分析完了後のリセット
        resetOncomingAnalysisState();
        return; 
    }
    
    resetZoomAndPan(); 
    updateOncomingAnalysisResultsDisplay(); 
    redrawDisplayCanvas(); 
}

/**
 * 車両マーキング開始
 */
function startVehicleMarking() {
    // 動画キャンバスを非表示にして、専用エリアでの操作に切り替え
    videoCanvas.style.display = 'none'; 
    videoCanvas.style.pointerEvents = 'none';
    
    startVehicleMarkingButton.classList.add('hidden'); 
    captureFrameButton.disabled = true; 

    if (oncomingMarkingStep === 0.5) { 
        // 1回目のマーキング開始
        oncomingMarkingStep = 1;
        measurementState = 'oncoming_F1_P1_click';
        points = []; 
        showUIMessage(oncomingAnalysisInstructionText, "キャプチャ画像エリアで対向車両の代表的な2点 (例: 前面の両端) をクリックしてください (1回目)。");
        
        // キャプチャエリアでのマーキングを有効化
        setCaptureMarkingMode(true, 'oncoming_F1');
        
    } else if (oncomingMarkingStep === 1.7) { 
        // 2回目のマーキング開始
        oncomingMarkingStep = 2;
        measurementState = 'oncoming_F2_P1_click';
        points = []; 
        showUIMessage(oncomingAnalysisInstructionText, "キャプチャ画像エリアで同じ対向車両の対応する2点を再度クリックしてください (2回目)。");
        
        // キャプチャエリアでのマーキングを有効化
        setCaptureMarkingMode(true, 'oncoming_F2');
    }
}

/**
 * キャプチャエリアでのクリック処理
 */
function handleOncomingCaptureClick(point, pointCount) {
    console.log(`🎯 Oncoming capture click: point ${pointCount}`, point);
      if (measurementState === 'oncoming_F1_P1_click') {
        if (pointCount === 1) {
            showUIMessage(oncomingAnalysisInstructionText, "キャプチャ画像エリアで対向車両の代表的な2点目 (例: 前面の右端) をクリックしてください (1回目)。");
        } else if (pointCount === 2) {
            // 1回目のマーキング完了
            const capturePoints = getCaptureMarkingPoints();
            vehicleSnapshot1.points = [...capturePoints];
            vehicleSnapshot1.time = videoPlayer.currentTime;
            vehicleSnapshot1.angle = calculateAngle(capturePoints[0], capturePoints[1]);
            
            showUIMessage(oncomingStatusText, "1回目のマーク完了。");
            vehicleAngle1Text.textContent = vehicleSnapshot1.angle !== null ? vehicleSnapshot1.angle.toFixed(1) : '-';
            
            oncomingMarkingStep = 1.5;
            measurementState = 'idle';
            setCaptureMarkingMode(false);
            
            showUIMessage(oncomingAnalysisInstructionText, "動画を数フレーム進め、同じ車両が見える次の重要フレームで一時停止し、「このフレームをキャプチャ (2回目)」を押してください。");
            captureFrameButton.textContent = "このフレームをキャプチャ (2回目)";
            captureFrameButton.disabled = false;
        }
        
    } else if (measurementState === 'oncoming_F2_P1_click') {
        if (pointCount === 1) {
            showUIMessage(oncomingAnalysisInstructionText, "キャプチャ画像エリアで対向車両の対応する2点目をクリックしてください (2回目)。");
        } else if (pointCount === 2) {
            // 2回目のマーキング完了 - 分析実行
            const capturePoints = getCaptureMarkingPoints();
            vehicleSnapshot2.points = [...capturePoints];
            vehicleSnapshot2.time = videoPlayer.currentTime;
            vehicleSnapshot2.angle = calculateAngle(capturePoints[0], capturePoints[1]);
            
            // 分析結果の計算
            const angleChange = vehicleSnapshot2.angle - vehicleSnapshot1.angle;
            const timeDiff = vehicleSnapshot2.time - vehicleSnapshot1.time;
            
            // 結果表示
            showUIMessage(oncomingStatusText, "2回目のマーク完了。分析結果を表示しています。");
            vehicleAngle2Text.textContent = vehicleSnapshot2.angle.toFixed(1);
            angleChangeText.textContent = angleChange.toFixed(1);
            timeDiffText.textContent = timeDiff.toFixed(2);
            
            oncomingMarkingStep = 3;
            measurementState = 'completed';
            setCaptureMarkingMode(false);
            
            captureFrameButton.textContent = "新しい分析を開始";
            captureFrameButton.disabled = false;
            
            showUIMessage(oncomingAnalysisInstructionText, "分析完了！角度変化から対向車の進路傾向を確認できます。新しい分析を開始するか、「現在のモードをリセット」でリセットしてください。");
        }
    }
    
    updateOncomingAnalysisResultsDisplay();
}

/**
 * 対向車分析のクリック処理
 */
function handleOncomingAnalysisClickLogic() {
    if (measurementState === 'oncoming_F1_P1_click') { 
        measurementState = 'oncoming_F1_P2_click';
        showUIMessage(oncomingAnalysisInstructionText, "対向車両の代表的な2点目 (例: 前面の右端) をクリックしてください (1回目)。");
        
    } else if (measurementState === 'oncoming_F1_P2_click') { 
        if (points.length === 2) {
            // 1回目のマーキング完了
            vehicleSnapshot1.points = [...points];
            vehicleSnapshot1.time = videoPlayer.currentTime;
            vehicleSnapshot1.angle = calculateAngle(points[0], points[1]);
            
            showUIMessage(oncomingStatusText, "1回目のマーク完了。");
            vehicleAngle1Text.textContent = vehicleSnapshot1.angle !== null ? vehicleSnapshot1.angle.toFixed(1) : '-';
            
            oncomingMarkingStep = 1.5; 
            showUIMessage(oncomingAnalysisInstructionText, "動画を数フレーム進め、同じ車両が見える次の重要フレームで一時停止し、「このフレームをキャプチャ (2回目)」を押してください。");
            measurementState = 'idle'; 
            points = [];
            captureFrameButton.textContent = "このフレームをキャプチャ (2回目)";
            captureFrameButton.disabled = false;
            
            // キャンバスを非表示にして次のキャプチャ待ち
            videoCanvas.style.display = 'none'; 
            videoCanvas.style.pointerEvents = 'none';
        }
        
    } else if (measurementState === 'oncoming_F2_P1_click') { 
        measurementState = 'oncoming_F2_P2_click';
        showUIMessage(oncomingAnalysisInstructionText, "対向車両の対応する2点目をクリックしてください (2回目)。");
        
    } else if (measurementState === 'oncoming_F2_P2_click') { 
        if (points.length === 2) {
            // 2回目のマーキング完了 - 分析実行
            vehicleSnapshot2.points = [...points];
            vehicleSnapshot2.time = videoPlayer.currentTime;
            vehicleSnapshot2.angle = calculateAngle(points[0], points[1]);
            
            // 分析結果の計算
            const angleChange = vehicleSnapshot2.angle - vehicleSnapshot1.angle;
            const timeDiff = vehicleSnapshot2.time - vehicleSnapshot1.time;
            
            // 結果表示
            showUIMessage(oncomingStatusText, "2回目のマーク完了。分析結果を表示中。");
            vehicleAngle2Text.textContent = vehicleSnapshot2.angle !== null ? vehicleSnapshot2.angle.toFixed(1) : '-';
            angleChangeText.textContent = angleChange.toFixed(1);
            timeDiffText.textContent = timeDiff.toFixed(2);
            
            oncomingMarkingStep = 3; 
            showUIMessage(oncomingAnalysisInstructionText, "分析完了! 角度変化: " + angleChange.toFixed(1) + "°、時間差: " + timeDiff.toFixed(2) + "秒。「現在のモードをリセット」で新しい分析を開始できます。");
            measurementState = 'oncoming_done'; 
            points = [];
            
            // パンモードに切り替え
            videoCanvas.style.pointerEvents = 'auto'; 
            videoCanvas.style.cursor = 'grab'; 
            captureFrameButton.disabled = true;
        }
    }
    
    updateOncomingAnalysisResultsDisplay();
}

/**
 * 対向車分析状態をリセット
 */
function resetOncomingAnalysisState() {
    vehicleSnapshot1 = { points: [], time: 0, angle: null, midPoint: null, frameCaptured: false };
    vehicleSnapshot2 = { points: [], time: 0, angle: null, midPoint: null, frameCaptured: false };
    oncomingMarkingStep = 0;
    measurementState = 'idle';
    points = [];
    
    // キャプチャエリアをクリア
    setCaptureMarkingMode(false);
    clearCaptureMarkingPoints();
    hideCaptureImage();
    
    // UI状態をリセット
    showUIMessage(oncomingAnalysisInstructionText, "分析したい最初のフレームで動画を一時停止し、「このフレームをキャプチャ (1回目)」を押してください。");
    captureFrameButton.textContent = "このフレームをキャプチャ (1回目)";
    captureFrameButton.disabled = false;
    startVehicleMarkingButton.classList.add('hidden');
    
    // 結果表示をクリア
    oncomingStatusText.textContent = "待機中";
    vehicleAngle1Text.textContent = "-";
    vehicleAngle2Text.textContent = "-";
    angleChangeText.textContent = "-";
    timeDiffText.textContent = "-";
}

/**
 * 対向車分析状態の完全リセット（拡張版）
 */
function resetOncomingAnalysisStateComplete() {
    points = [];
    vehicleSnapshot1 = { points: [], time: 0, angle: null, frameCaptured: false };
    vehicleSnapshot2 = { points: [], time: 0, angle: null, frameCaptured: false };
    oncomingMarkingStep = 0;
    measurementState = 'idle'; 
    
    // キャプチャエリアをクリア
    setCaptureMarkingMode(false);
    clearCaptureMarkingPoints();
    hideCaptureImage();
    
    updateOncomingAnalysisResultsDisplay();
    
    showUIMessage(oncomingAnalysisInstructionText, "分析したい最初のフレームで動画を一時停止し、「このフレームをキャプチャ (1回目)」を押してください。");
    captureFrameButton.textContent = "このフレームをキャプチャ (1回目)";
    captureFrameButton.disabled = false;
    startVehicleMarkingButton.classList.add('hidden');
    
    videoCanvas.style.display = 'none';
    videoCanvas.style.pointerEvents = 'none'; 
    videoCanvas.style.cursor = 'default';
    
    if (visibleCtx) visibleCtx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
}

/**
 * 対向車分析結果表示を更新
 */
function updateOncomingAnalysisResultsDisplay() {
    vehicleAngle1Text.textContent = vehicleSnapshot1.angle !== null ? vehicleSnapshot1.angle.toFixed(1) : '-';
    vehicleAngle2Text.textContent = vehicleSnapshot2.angle !== null ? vehicleSnapshot2.angle.toFixed(1) : '-';
    
    if (vehicleSnapshot1.angle !== null && vehicleSnapshot2.angle !== null) {
        let angleDiff = vehicleSnapshot2.angle - vehicleSnapshot1.angle;
        // 角度差を-180から180の範囲に正規化
        if (angleDiff > 180) angleDiff -= 360; 
        if (angleDiff < -180) angleDiff += 360;
        angleChangeText.textContent = angleDiff.toFixed(1);
    } else {
        angleChangeText.textContent = '-';
    }
    
    timeDiffText.textContent = (vehicleSnapshot1.time && vehicleSnapshot2.time && vehicleSnapshot1.time !== vehicleSnapshot2.time) 
        ? (vehicleSnapshot2.time - vehicleSnapshot1.time).toFixed(2) : '-';
    
    if (measurementState === 'idle' || !oncomingAnalysisResultsDisplay.classList.contains('hidden')) {
        showUIMessage(oncomingStatusText, measurementState.startsWith('oncoming_') || oncomingMarkingStep > 0 ? oncomingStatusText.textContent : "待機中");
    }
}

/**
 * 対向車分析の描画要素を再描画
 */
function redrawOncomingElements() {
    // 1回目のマーキング点の描画
    if (vehicleSnapshot1.points.length === 2) {
        const p1Display = toDisplayCoords(vehicleSnapshot1.points[0]);
        const p2Display = toDisplayCoords(vehicleSnapshot1.points[1]);
        if (p1Display && p2Display) {
            drawLineOnCanvas(p1Display, p2Display, 'green', 3);
            drawPointOnCanvas(p1Display.x, p1Display.y, 'green', 6);
            drawPointOnCanvas(p2Display.x, p2Display.y, 'green', 6);
        }
    }
    
    // 2回目のマーキング点の描画
    if (vehicleSnapshot2.points.length === 2) {
        const p1Display = toDisplayCoords(vehicleSnapshot2.points[0]);
        const p2Display = toDisplayCoords(vehicleSnapshot2.points[1]);
        if (p1Display && p2Display) {
            drawLineOnCanvas(p1Display, p2Display, 'orange', 3);
            drawPointOnCanvas(p1Display.x, p1Display.y, 'orange', 6);
            drawPointOnCanvas(p2Display.x, p2Display.y, 'orange', 6);
        }
    }
    
    // 現在選択中の点の描画
    if (measurementState.startsWith('oncoming_')) {
        points.forEach((point, index) => {
            const displayPoint = toDisplayCoords(point);
            if (displayPoint) {
                const color = measurementState.includes('F1') ? 'green' : 'orange';
                drawPointOnCanvas(displayPoint.x, displayPoint.y, color, 5);
            }
        });
    }
}

/**
 * 対向車分析機能を初期化
 */
function initOncomingAnalysis() {
    captureFrameButton.addEventListener('click', captureFrame);
    startVehicleMarkingButton.addEventListener('click', startVehicleMarking);
}
