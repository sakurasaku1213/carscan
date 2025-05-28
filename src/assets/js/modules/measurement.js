/**
 * 測定（Measurement）モジュール
 * 
 * 寸法測定機能を提供：
 * - 参照線と測定対象線の設定
 * -    initializeUIElements() {
        this.uiElements.statusText = DOMUtils.getElement('#dimensionStatusText');
        this.uiElements.instructionText = DOMUtils.getElement('#commonInstructionText');
        this.uiElements.startButton = DOMUtils.getElement('#startMeasurementButton');
        this.uiElements.clearButton = DOMUtils.getElement('#clearMeasurementButton');
        this.uiElements.refPixelLengthText = DOMUtils.getElement('#refPixelLengthText');
        this.uiElements.targetPixelLengthText = DOMUtils.getElement('#targetPixelLengthText');
        this.uiElements.scaleText = DOMUtils.getElement('#scaleText');
        this.uiElements.estimatedSizeText = DOMUtils.getElement('#estimatedSizeText');
        this.uiElements.refActualSizeInput = DOMUtils.getElement('#refObjectActualSizeInput');
        
        // デバッグ要素（オプション）
        this.debugStateElement = DOMUtils.getElement('#debugMeasurementState');ル変換
 * - 実際のサイズ計算
 * - 測定点の描画とUI連携
 */

import { MathUtils } from '../utils/math.js';
import { CanvasUtils } from '../utils/canvas.js';
import { DOMUtils } from '../utils/dom.js';

export class MeasurementManager {
    constructor() {
        this.mode = 'none'; // 'none', 'reference', 'target', 'completed'
        this.referencePoints = [];
        this.targetPoints = [];
        this.isDrawingLine = false;
        this.isInitialized = false;
        
        // 測定結果
        this.referencePixelDistance = 0;
        this.targetPixelDistance = 0;
        this.scale = 0; // mm/pixel
        this.estimatedSize = 0; // mm
        
        // UI参照
        this.uiElements = {
            statusText: null,
            instructionText: null,
            startButton: null,
            clearButton: null,
            refPixelLengthText: null,
            targetPixelLengthText: null,
            scaleText: null,
            estimatedSizeText: null,
            refActualSizeInput: null
        };
        
        this.subscribers = new Set();
        this.canvas = null;
        this.state = null;
        
        console.log('📏 MeasurementManager initialized');
    }
      /**
     * 初期化
     */
    async init() {
        try {
            this.canvas = DOMUtils.getElement('#captureCanvas');
            if (!this.canvas) {
                throw new Error('Capture canvas not found');
            }
            
            this.initializeUIElements();
            this.setupEventListeners();
            this.reset();
            this.isInitialized = true;
            
            console.log('📏 MeasurementManager initialized');
            return true;
        } catch (error) {
            console.error('❌ MeasurementManager initialization failed:', error);
            return false;
        }
    }
    
    /**
     * UI要素の初期化
     */    initializeUIElements() {
        this.uiElements.statusText = DOMUtils.getElement('#dimensionStatusText');
        this.uiElements.instructionText = DOMUtils.getElement('#commonInstructionText');
        this.uiElements.startButton = DOMUtils.getElement('#startMeasurementButton');
        this.uiElements.clearButton = DOMUtils.getElement('#clearMeasurementButton');
        this.uiElements.refPixelLengthText = DOMUtils.getElement('#refPixelLengthText');
        this.uiElements.targetPixelLengthText = DOMUtils.getElement('#targetPixelLengthText');
        this.uiElements.scaleText = DOMUtils.getElement('#scaleText');
        this.uiElements.estimatedSizeText = DOMUtils.getElement('#estimatedSizeText');
        this.uiElements.refActualSizeInput = DOMUtils.getElement('#refObjectActualSizeInput');
          // デバッグ用要素
        this.debugStateElement = DOMUtils.getElement('#debugMeasurementState');
    }
    
    /**
     * イベントリスナーの設定
     */
    setupEventListeners() {
        // 測定開始ボタン
        if (this.uiElements.startButton) {
            this.uiElements.startButton.addEventListener('click', () => {
                this.startMeasurement();
            });
        }
        
        // 測定クリアボタン
        if (this.uiElements.clearButton) {
            this.uiElements.clearButton.addEventListener('click', () => {
                this.reset();
            });
        }
        
        // 参照サイズ入力の変更
        if (this.uiElements.refActualSizeInput) {
            this.uiElements.refActualSizeInput.addEventListener('input', () => {
                if (this.referencePoints.length >= 2 && this.targetPoints.length >= 2) {
                    this.calculateDimensions();
                }
            });
        }
    }
    
    /**
     * 測定開始
     */
    startMeasurement() {
        this.reset();
        this.mode = 'reference';
        this.updateUI();
        this.notifySubscribers('measurementStarted');
        console.log('📏 Measurement started - reference mode');
    }
    
    /**
     * 測定をリセット
     */
    reset() {
        this.mode = 'none';
        this.referencePoints = [];
        this.targetPoints = [];
        this.isDrawingLine = false;
        this.referencePixelDistance = 0;
        this.targetPixelDistance = 0;
        this.scale = 0;
        this.estimatedSize = 0;
        
        this.updateUI();
        this.notifySubscribers('measurementReset');
        console.log('📏 Measurement reset');
    }
    
    /**
     * 測定をクリア（resetのエイリアス）
     */
    clearMeasurement() {
        this.reset();
        this.updateUI();
        console.log('📏 Measurement cleared');
    }
    
    /**
     * 測定クリック処理
     * @param {number} canvasX - キャンバスX座標
     * @param {number} canvasY - キャンバスY座標
     * @returns {boolean} クリックが処理されたかどうか
     */
    handleClick(canvasX, canvasY) {
        if (this.mode === 'none' || this.mode === 'completed') {
            return false;
        }
        
        if (!this.state) {
            console.error('State not available for measurement click');
            return false;
        }
        
        // キャンバス座標を画像座標に変換
        const imageCoords = MathUtils.canvasToImageCoords(
            canvasX, 
            canvasY,
            this.state.getState('capture.viewOffsetX'),
            this.state.getState('capture.viewOffsetY'),
            this.state.getState('capture.zoomLevel')
        );
        
        // 画像範囲内かチェック
        const imageWidth = this.state.getState('capture.imageWidth');
        const imageHeight = this.state.getState('capture.imageHeight');
        
        if (imageCoords.x < 0 || imageCoords.x > imageWidth || 
            imageCoords.y < 0 || imageCoords.y > imageHeight) {
            console.log('📏 Click outside image bounds');
            return false;
        }
        
        if (this.mode === 'reference') {
            return this.handleReferenceClick(imageCoords);
        } else if (this.mode === 'target') {
            return this.handleTargetClick(imageCoords);
        }
        
        return false;
    }
    
    /**
     * 参照線クリック処理
     * @param {Object} imageCoords - 画像座標 {x, y}
     * @returns {boolean} 処理されたかどうか
     */
    handleReferenceClick(imageCoords) {
        this.referencePoints.push(imageCoords);
        console.log(`📏 Reference point ${this.referencePoints.length} added:`, imageCoords);
        
        if (this.referencePoints.length >= 2) {
            this.referencePixelDistance = MathUtils.calculateDistance(
                this.referencePoints[0], 
                this.referencePoints[1]
            );
            
            console.log(`📏 Reference line length: ${this.referencePixelDistance.toFixed(2)} pixels`);
            
            // UI更新
            this.updateReferenceDisplay();
            this.showStatusMessage("参照線を設定しました。参照オブジェクトの実際のサイズを入力してください。");
            this.showInstructionMessage("参照オブジェクトの実際のサイズ（mm）を入力し、次に測定対象線を設定してください。");
            
            // 測定対象線モードに切り替え
            this.mode = 'target';
            this.updateUI();
        }
        
        this.notifySubscribers('referencePointAdded', { point: imageCoords, total: this.referencePoints.length });
        return true;
    }
    
    /**
     * 測定対象線クリック処理
     * @param {Object} imageCoords - 画像座標 {x, y}
     * @returns {boolean} 処理されたかどうか
     */
    handleTargetClick(imageCoords) {
        this.targetPoints.push(imageCoords);
        console.log(`📏 Target point ${this.targetPoints.length} added:`, imageCoords);
        
        if (this.targetPoints.length >= 2) {
            this.targetPixelDistance = MathUtils.calculateDistance(
                this.targetPoints[0], 
                this.targetPoints[1]
            );
            
            console.log(`📏 Target line length: ${this.targetPixelDistance.toFixed(2)} pixels`);
            
            // 寸法計算を実行
            this.calculateDimensions();
            
            // 測定完了
            this.mode = 'completed';
            this.updateUI();
        }
        
        this.notifySubscribers('targetPointAdded', { point: imageCoords, total: this.targetPoints.length });
        return true;
    }
    
    /**
     * 寸法計算
     */
    calculateDimensions() {
        if (this.referencePoints.length < 2 || this.targetPoints.length < 2) {
            console.warn('📏 Insufficient points for dimension calculation');
            return;
        }
        
        // 参照オブジェクトの実際のサイズを取得
        const refActualSize = this.getReferenceActualSize();
        
        if (!refActualSize || refActualSize <= 0) {
            this.showStatusMessage("参照オブジェクトの実際のサイズを入力してください。");
            return;
        }
        
        // スケール計算（mm/pixel）
        this.scale = refActualSize / this.referencePixelDistance;
        
        // 測定対象の実際のサイズ計算
        this.estimatedSize = this.targetPixelDistance * this.scale;
        
        // 結果をUIに表示
        this.updateCalculationDisplay();
        
        console.log(`📏 Measurement result: ${this.estimatedSize.toFixed(2)} mm`);
        this.showStatusMessage("測定完了！");
        this.showInstructionMessage(`測定結果: ${this.estimatedSize.toFixed(2)} mm`);
        
        this.notifySubscribers('measurementCompleted', {
            referencePixelDistance: this.referencePixelDistance,
            targetPixelDistance: this.targetPixelDistance,
            scale: this.scale,
            estimatedSize: this.estimatedSize
        });
    }
    
    /**
     * 参照オブジェクトの実際のサイズを取得
     * @returns {number} サイズ（mm）
     */
    getReferenceActualSize() {
        if (!this.uiElements.refActualSizeInput) return 0;
        return parseFloat(this.uiElements.refActualSizeInput.value) || 0;
    }
    
    /**
     * 測定要素を描画
     * @param {CanvasRenderingContext2D} ctx - キャンバスコンテキスト
     */
    drawMeasurementElements(ctx) {
        if (!this.state) return;
        
        const viewOffsetX = this.state.getState('capture.viewOffsetX');
        const viewOffsetY = this.state.getState('capture.viewOffsetY');
        const zoomLevel = this.state.getState('capture.zoomLevel');
        
        // 参照線を描画（赤）
        if (this.referencePoints.length >= 2) {
            this.drawLine(ctx, this.referencePoints[0], this.referencePoints[1], '#FF0000', 3, '参照線', viewOffsetX, viewOffsetY, zoomLevel);
        } else if (this.referencePoints.length === 1) {
            this.drawPoint(ctx, this.referencePoints[0], '#FF0000', '参照点1', viewOffsetX, viewOffsetY, zoomLevel);
        }
        
        // 測定対象線を描画（青）
        if (this.targetPoints.length >= 2) {
            this.drawLine(ctx, this.targetPoints[0], this.targetPoints[1], '#0000FF', 3, '測定線', viewOffsetX, viewOffsetY, zoomLevel);
        } else if (this.targetPoints.length === 1) {
            this.drawPoint(ctx, this.targetPoints[0], '#0000FF', '測定点1', viewOffsetX, viewOffsetY, zoomLevel);
        }
    }
    
    /**
     * 線を描画
     * @param {CanvasRenderingContext2D} ctx - キャンバスコンテキスト
     * @param {Object} point1 - 開始点の画像座標
     * @param {Object} point2 - 終了点の画像座標
     * @param {string} color - 線の色
     * @param {number} width - 線の太さ
     * @param {string} label - ラベル
     * @param {number} viewOffsetX - ビューオフセットX
     * @param {number} viewOffsetY - ビューオフセットY
     * @param {number} zoomLevel - ズームレベル
     */
    drawLine(ctx, point1, point2, color, width, label, viewOffsetX, viewOffsetY, zoomLevel) {
        const canvasPoint1 = MathUtils.imageToCanvasCoords(point1.x, point1.y, viewOffsetX, viewOffsetY, zoomLevel);
        const canvasPoint2 = MathUtils.imageToCanvasCoords(point2.x, point2.y, viewOffsetX, viewOffsetY, zoomLevel);
        
        // 線を描画
        CanvasUtils.drawLine(ctx, canvasPoint1, canvasPoint2, {
            color: color,
            width: width,
            style: 'solid'
        });
        
        // 点を描画
        this.drawPoint(ctx, point1, color, '', viewOffsetX, viewOffsetY, zoomLevel);
        this.drawPoint(ctx, point2, color, '', viewOffsetX, viewOffsetY, zoomLevel);
        
        // ラベルを描画
        const midX = (canvasPoint1.x + canvasPoint2.x) / 2;
        const midY = (canvasPoint1.y + canvasPoint2.y) / 2;
        
        CanvasUtils.drawText(ctx, label, midX + 10, midY - 10, {
            color: color,
            font: '14px Arial'
        });
    }
    
    /**
     * 点を描画
     * @param {CanvasRenderingContext2D} ctx - キャンバスコンテキスト
     * @param {Object} point - 画像座標
     * @param {string} color - 点の色
     * @param {string} label - ラベル
     * @param {number} viewOffsetX - ビューオフセットX
     * @param {number} viewOffsetY - ビューオフセットY
     * @param {number} zoomLevel - ズームレベル
     */
    drawPoint(ctx, point, color, label, viewOffsetX, viewOffsetY, zoomLevel) {
        const canvasPoint = MathUtils.imageToCanvasCoords(point.x, point.y, viewOffsetX, viewOffsetY, zoomLevel);
        
        // 点を描画
        CanvasUtils.drawCircle(ctx, canvasPoint.x, canvasPoint.y, 5, {
            fillColor: color,
            strokeColor: '#FFFFFF',
            strokeWidth: 2
        });
        
        // ラベルを描画
        if (label) {
            CanvasUtils.drawText(ctx, label, canvasPoint.x + 10, canvasPoint.y - 10, {
                color: color,
                font: '12px Arial'
            });
        }
    }
    
    /**
     * UI更新
     */
    updateUI() {
        this.updateModeUI();
        this.updateDebugInfo();
    }
    
    /**
     * モードUIの更新
     */
    updateModeUI() {
        if (!this.uiElements.startButton) return;
        
        switch (this.mode) {
            case 'reference':
                this.uiElements.startButton.textContent = '参照線設定中...';
                this.uiElements.startButton.disabled = true;
                break;
            case 'target':
                this.uiElements.startButton.textContent = '測定線設定中...';
                this.uiElements.startButton.disabled = true;
                break;
            case 'completed':
                this.uiElements.startButton.textContent = '測定完了';
                this.uiElements.startButton.disabled = false;
                break;
            default:
                this.uiElements.startButton.textContent = '測定開始';
                this.uiElements.startButton.disabled = false;
                break;
        }
    }
    
    /**
     * 参照線表示の更新
     */
    updateReferenceDisplay() {
        if (this.uiElements.refPixelLengthText) {
            this.uiElements.refPixelLengthText.textContent = this.referencePixelDistance.toFixed(2);
        }
    }
    
    /**
     * 計算結果表示の更新
     */
    updateCalculationDisplay() {
        if (this.uiElements.refPixelLengthText) {
            this.uiElements.refPixelLengthText.textContent = this.referencePixelDistance.toFixed(2);
        }
        if (this.uiElements.targetPixelLengthText) {
            this.uiElements.targetPixelLengthText.textContent = this.targetPixelDistance.toFixed(2);
        }
        if (this.uiElements.scaleText) {
            this.uiElements.scaleText.textContent = this.scale.toFixed(4);
        }
        if (this.uiElements.estimatedSizeText) {
            this.uiElements.estimatedSizeText.textContent = this.estimatedSize.toFixed(2) + ' mm';
        }
    }
    
    /**
     * デバッグ情報の更新
     */
    updateDebugInfo() {
        if (this.debugStateElement) {
            this.debugStateElement.textContent = this.mode;
        }
    }
    
    /**
     * ステータスメッセージの表示
     * @param {string} message - メッセージ
     */
    showStatusMessage(message) {
        if (this.uiElements.statusText) {
            DOMUtils.showMessage(this.uiElements.statusText, message);
        }
    }
    
    /**
     * インストラクションメッセージの表示
     * @param {string} message - メッセージ
     */
    showInstructionMessage(message) {
        if (this.uiElements.instructionText) {
            DOMUtils.showMessage(this.uiElements.instructionText, message);
        }
    }
    
    /**
     * 購読者を追加
     * @param {Function} callback - コールバック関数
     */
    subscribe(callback) {
        this.subscribers.add(callback);
    }
    
    /**
     * 購読者を削除
     * @param {Function} callback - コールバック関数
     */
    unsubscribe(callback) {
        this.subscribers.delete(callback);
    }
    
    /**
     * 購読者に通知
     * @param {string} event - イベント名
     * @param {*} data - データ
     */
    notifySubscribers(event, data = null) {
        this.subscribers.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('Error in measurement subscriber:', error);
            }
        });
    }
    
    /**
     * 現在の測定モードを取得
     * @returns {string} 測定モード
     */
    getMode() {
        return this.mode;
    }
    
    /**
     * 測定データを取得
     * @returns {Object} 測定データ
     */
    getMeasurementData() {
        return {
            mode: this.mode,
            referencePoints: [...this.referencePoints],
            targetPoints: [...this.targetPoints],
            referencePixelDistance: this.referencePixelDistance,
            targetPixelDistance: this.targetPixelDistance,
            scale: this.scale,
            estimatedSize: this.estimatedSize,
            referenceActualSize: this.getReferenceActualSize()
        };
    }
    
    /**
     * 測定データを設定
     * @param {Object} data - 測定データ
     */
    setMeasurementData(data) {
        if (!data) return;
        
        this.mode = data.mode || 'none';
        this.referencePoints = data.referencePoints || [];
        this.targetPoints = data.targetPoints || [];
        this.referencePixelDistance = data.referencePixelDistance || 0;
        this.targetPixelDistance = data.targetPixelDistance || 0;
        this.scale = data.scale || 0;
        this.estimatedSize = data.estimatedSize || 0;
        
        if (data.referenceActualSize && this.uiElements.refActualSizeInput) {
            this.uiElements.refActualSizeInput.value = data.referenceActualSize;
        }
        
        this.updateUI();
        this.updateCalculationDisplay();
        
        console.log('📏 Measurement data restored:', data);
    }
    
    /**
     * リソースのクリーンアップ
     */
    destroy() {
        this.subscribers.clear();
        this.canvas = null;
        this.state = null;
        
        // UI要素のクリーンアップ
        Object.keys(this.uiElements).forEach(key => {
            this.uiElements[key] = null;
        });
        
        console.log('📏 MeasurementManager destroyed');
    }
}

// デフォルトエクスポート
export default MeasurementManager;
