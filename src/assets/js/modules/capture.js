/**
 * フレームキャプチャモジュール
 * 動画フレームのキャプチャとズーム・パン機能を担当
 */

import { DOMUtils } from '../utils/dom.js';
import { CanvasUtils } from '../utils/canvas.js';
import { MathUtils } from '../utils/math.js';
import appState from '../core/state.js';

export class CaptureManager {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.isInitialized = false;
        this.eventListeners = [];
    }
    
    /**
     * 初期化
     */
    async init() {
        try {
            this.setupCanvas();
            this.setupEventListeners();
            this.setupUI();
            this.isInitialized = true;
            console.log('✅ Capture module initialized');
            return true;
        } catch (error) {
            console.error('❌ Capture module initialization failed:', error);
            return false;
        }
    }
    
    /**
     * キャンバスのセットアップ
     */
    setupCanvas() {
        this.canvas = DOMUtils.getElement('#captureCanvas');
        if (!this.canvas) {
            throw new Error('Capture canvas not found');
        }
        
        this.ctx = this.canvas.getContext('2d');
        
        // 初期サイズ設定
        this.canvas.width = 800;
        this.canvas.height = 600;
        
        // 状態に設定
        appState.set('capture.canvas', this.canvas);
        
        // 初期表示
        this.drawPlaceholder();
    }
    
    /**
     * イベントリスナーのセットアップ
     */
    setupEventListeners() {
        if (!this.canvas) return;
        
        // マウスホイールでズーム
        this.addEventListeners([
            {
                element: this.canvas,
                event: 'wheel',
                handler: (e) => this.handleWheel(e),
                options: { passive: false }
            },
            {
                element: this.canvas,
                event: 'mousedown',
                handler: (e) => this.handleMouseDown(e)
            },
            {
                element: this.canvas,
                event: 'mousemove',
                handler: (e) => this.handleMouseMove(e)
            },
            {
                element: document,
                event: 'mouseup',
                handler: (e) => this.handleMouseUp(e)
            },
            {
                element: this.canvas,
                event: 'mouseleave',
                handler: (e) => this.handleMouseLeave(e)
            },
            {
                element: this.canvas,
                event: 'contextmenu',
                handler: (e) => e.preventDefault()
            }
        ]);
    }
    
    /**
     * UIのセットアップ
     */
    setupUI() {
        // キャプチャボタン
        const captureButton = DOMUtils.getElement('#captureFrameButton');
        if (captureButton) {
            this.addEventListeners([{
                element: captureButton,
                event: 'click',
                handler: () => this.captureFrame()
            }]);
        }
        
        // ズームコントロール
        const zoomInButton = DOMUtils.getElement('#zoomInButton');
        const zoomOutButton = DOMUtils.getElement('#zoomOutButton');
        const resetZoomButton = DOMUtils.getElement('#resetZoomButton');
        
        if (zoomInButton) {
            this.addEventListeners([{
                element: zoomInButton,
                event: 'click',
                handler: () => this.zoomIn()
            }]);
        }
        
        if (zoomOutButton) {
            this.addEventListeners([{
                element: zoomOutButton,
                event: 'click',
                handler: () => this.zoomOut()
            }]);
        }
        
        if (resetZoomButton) {
            this.addEventListeners([{
                element: resetZoomButton,
                event: 'click',
                handler: () => this.resetZoom()
            }]);
        }
    }
    
    /**
     * イベントリスナーの登録（クリーンアップ用）
     */
    addEventListeners(listeners) {
        listeners.forEach(({ element, event, handler, options }) => {
            element.addEventListener(event, handler, options);
            this.eventListeners.push({ element, event, handler, options });
        });
    }
    
    /**
     * プレースホルダーの描画
     */
    drawPlaceholder() {
        if (!this.ctx) return;
        
        this.ctx.fillStyle = '#f3f4f6';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.strokeStyle = '#d1d5db';
        this.ctx.setLineDash([10, 10]);
        this.ctx.strokeRect(20, 20, this.canvas.width - 40, this.canvas.height - 40);
        
        this.ctx.fillStyle = '#6b7280';
        this.ctx.font = '16px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('フレームをキャプチャしてください', this.canvas.width / 2, this.canvas.height / 2);
        
        this.ctx.setLineDash([]);
    }
    
    /**
     * フレームキャプチャ
     */
    async captureFrame() {
        const videoElement = appState.get('video.element');
        
        if (!videoElement || !appState.get('video.loaded')) {
            DOMUtils.showMessage('動画が読み込まれていません', 'warning');
            return false;
        }
        
        try {
            // 一時キャンバスを作成
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');
            
            // 動画のサイズを取得
            const videoWidth = videoElement.videoWidth;
            const videoHeight = videoElement.videoHeight;
            
            tempCanvas.width = videoWidth;
            tempCanvas.height = videoHeight;
            
            // 動画フレームを描画
            tempCtx.drawImage(videoElement, 0, 0, videoWidth, videoHeight);
            
            // 画像データをBlobに変換
            const blob = await new Promise(resolve => tempCanvas.toBlob(resolve, 'image/png'));
            const imageUrl = URL.createObjectURL(blob);
            
            // 画像要素を作成
            const img = new Image();
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = imageUrl;
            });
            
            // 状態を更新
            appState.update({
                'capture.imageElement': img,
                'capture.imageWidth': videoWidth,
                'capture.imageHeight': videoHeight,
                'capture.zoomLevel': 1.0,
                'capture.viewOffsetX': 0,
                'capture.viewOffsetY': 0
            });
            
            // キャンバスサイズを調整
            this.adjustCanvasSize(videoWidth, videoHeight);
            
            // 描画
            this.redraw();
            
            DOMUtils.showMessage('フレームをキャプチャしました', 'success');
            console.log(`Frame captured: ${videoWidth}x${videoHeight}`);
            
            return true;
            
        } catch (error) {
            console.error('Capture error:', error);
            DOMUtils.showMessage('キャプチャエラーが発生しました', 'error');
            return false;
        }
    }
    
    /**
     * キャンバスサイズの調整
     */
    adjustCanvasSize(imageWidth, imageHeight) {
        const container = this.canvas.parentElement;
        const containerRect = container.getBoundingClientRect();
        
        // アスペクト比を維持してフィット
        const aspectRatio = imageWidth / imageHeight;
        const maxWidth = Math.min(containerRect.width - 40, 800);
        const maxHeight = Math.min(containerRect.height - 40, 600);
        
        let canvasWidth, canvasHeight;
        
        if (maxWidth / aspectRatio <= maxHeight) {
            canvasWidth = maxWidth;
            canvasHeight = maxWidth / aspectRatio;
        } else {
            canvasWidth = maxHeight * aspectRatio;
            canvasHeight = maxHeight;
        }
        
        this.canvas.width = canvasWidth;
        this.canvas.height = canvasHeight;
        this.canvas.style.width = canvasWidth + 'px';
        this.canvas.style.height = canvasHeight + 'px';
    }
    
    /**
     * 再描画
     */
    redraw() {
        if (!this.ctx) return;
        
        const imageElement = appState.get('capture.imageElement');
        if (!imageElement) {
            this.drawPlaceholder();
            return;
        }
        
        const zoomLevel = appState.get('capture.zoomLevel');
        const viewOffsetX = appState.get('capture.viewOffsetX');
        const viewOffsetY = appState.get('capture.viewOffsetY');
        const imageWidth = appState.get('capture.imageWidth');
        const imageHeight = appState.get('capture.imageHeight');
        
        // キャンバスクリア
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 画像を描画
        const drawWidth = imageWidth * zoomLevel;
        const drawHeight = imageHeight * zoomLevel;
        
        this.ctx.drawImage(
            imageElement,
            viewOffsetX,
            viewOffsetY,
            drawWidth,
            drawHeight
        );
        
        // 測定要素を描画
        this.drawMeasurementElements();
        
        // デバッグ情報を更新
        this.updateDebugInfo();
    }
    
    /**
     * 測定要素の描画
     */
    drawMeasurementElements() {
        const referencePoints = appState.get('measurement.referencePoints');
        const targetPoints = appState.get('measurement.targetPoints');
        
        // 参照線を描画（赤）
        if (referencePoints.length >= 2) {
            const p1 = this.imageToCanvasCoords(referencePoints[0]);
            const p2 = this.imageToCanvasCoords(referencePoints[1]);
            CanvasUtils.drawLine(this.ctx, p1, p2, '#FF0000', 3, '参照線');
        } else if (referencePoints.length === 1) {
            const p = this.imageToCanvasCoords(referencePoints[0]);
            CanvasUtils.drawPoint(this.ctx, p, '#FF0000', 5, '参照点1');
        }
        
        // 測定線を描画（青）
        if (targetPoints.length >= 2) {
            const p1 = this.imageToCanvasCoords(targetPoints[0]);
            const p2 = this.imageToCanvasCoords(targetPoints[1]);
            CanvasUtils.drawLine(this.ctx, p1, p2, '#0000FF', 3, '測定線');
        } else if (targetPoints.length === 1) {
            const p = this.imageToCanvasCoords(targetPoints[0]);
            CanvasUtils.drawPoint(this.ctx, p, '#0000FF', 5, '測定点1');
        }
    }
    
    /**
     * マウスホイールハンドラー
     */
    handleWheel(e) {
        e.preventDefault();
        
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const oldZoom = appState.get('capture.zoomLevel');
        const newZoom = MathUtils.clamp(oldZoom * zoomFactor, 0.1, 10);
        
        if (newZoom !== oldZoom) {
            // ズーム中心をマウス位置に合わせる
            const zoomRatio = newZoom / oldZoom;
            const oldOffsetX = appState.get('capture.viewOffsetX');
            const oldOffsetY = appState.get('capture.viewOffsetY');
            
            const newOffsetX = mouseX - (mouseX - oldOffsetX) * zoomRatio;
            const newOffsetY = mouseY - (mouseY - oldOffsetY) * zoomRatio;
            
            appState.update({
                'capture.zoomLevel': newZoom,
                'capture.viewOffsetX': newOffsetX,
                'capture.viewOffsetY': newOffsetY
            });
            
            this.redraw();
        }
    }
    
    /**
     * マウス押下ハンドラー
     */
    handleMouseDown(e) {
        if (e.button === 0) { // 左クリック
            e.preventDefault();
            
            const measurementMode = appState.get('measurement.mode');
            
            if (measurementMode === 'none') {
                // パンモード
                appState.update({
                    'capture.isPanning': true,
                    'capture.lastMouseX': e.clientX,
                    'capture.lastMouseY': e.clientY
                });
                this.canvas.style.cursor = 'grabbing';
            }
        }
    }
    
    /**
     * マウス移動ハンドラー
     */
    handleMouseMove(e) {
        const isPanning = appState.get('capture.isPanning');
        const measurementMode = appState.get('measurement.mode');
        
        if (isPanning && measurementMode === 'none') {
            const deltaX = e.clientX - appState.get('capture.lastMouseX');
            const deltaY = e.clientY - appState.get('capture.lastMouseY');
            
            appState.update({
                'capture.viewOffsetX': appState.get('capture.viewOffsetX') + deltaX,
                'capture.viewOffsetY': appState.get('capture.viewOffsetY') + deltaY,
                'capture.lastMouseX': e.clientX,
                'capture.lastMouseY': e.clientY
            });
            
            this.redraw();
        } else {
            // カーソル表示
            if (measurementMode === 'none') {
                this.canvas.style.cursor = 'grab';
            } else {
                this.canvas.style.cursor = 'crosshair';
            }
        }
    }
    
    /**
     * マウス離しハンドラー
     */
    handleMouseUp(e) {
        if (e.button === 0) {
            if (appState.get('capture.isPanning')) {
                appState.set('capture.isPanning', false);
                const measurementMode = appState.get('measurement.mode');
                this.canvas.style.cursor = measurementMode === 'none' ? 'grab' : 'crosshair';
            }
        }
    }
    
    /**
     * マウス離脱ハンドラー
     */
    handleMouseLeave(e) {
        this.canvas.style.cursor = 'default';
    }
    
    /**
     * ズームイン
     */
    zoomIn() {
        const currentZoom = appState.get('capture.zoomLevel');
        const newZoom = MathUtils.clamp(currentZoom * 1.2, 0.1, 10);
        appState.set('capture.zoomLevel', newZoom);
        this.redraw();
    }
    
    /**
     * ズームアウト
     */
    zoomOut() {
        const currentZoom = appState.get('capture.zoomLevel');
        const newZoom = MathUtils.clamp(currentZoom / 1.2, 0.1, 10);
        appState.set('capture.zoomLevel', newZoom);
        this.redraw();
    }
    
    /**
     * ズームリセット
     */
    resetZoom() {
        appState.update({
            'capture.zoomLevel': 1.0,
            'capture.viewOffsetX': 0,
            'capture.viewOffsetY': 0
        });
        this.redraw();
    }
    
    /**
     * 画像座標をキャンバス座標に変換
     */
    imageToCanvasCoords(imagePoint) {
        const zoomLevel = appState.get('capture.zoomLevel');
        const viewOffsetX = appState.get('capture.viewOffsetX');
        const viewOffsetY = appState.get('capture.viewOffsetY');
        
        return MathUtils.imageToCanvasCoords(
            imagePoint.x, imagePoint.y,
            zoomLevel, viewOffsetX, viewOffsetY
        );
    }
    
    /**
     * キャンバス座標を画像座標に変換
     */
    canvasToImageCoords(canvasPoint) {
        const zoomLevel = appState.get('capture.zoomLevel');
        const viewOffsetX = appState.get('capture.viewOffsetX');
        const viewOffsetY = appState.get('capture.viewOffsetY');
        
        return MathUtils.canvasToImageCoords(
            canvasPoint.x, canvasPoint.y,
            zoomLevel, viewOffsetX, viewOffsetY
        );
    }
    
    /**
     * クリック位置の処理（測定用）
     */
    handleMeasurementClick(event) {
        const rect = this.canvas.getBoundingClientRect();
        const canvasX = event.clientX - rect.left;
        const canvasY = event.clientY - rect.top;
        
        // 画像座標に変換
        const imageCoords = this.canvasToImageCoords({ x: canvasX, y: canvasY });
        
        // 画像範囲内かチェック
        const imageWidth = appState.get('capture.imageWidth');
        const imageHeight = appState.get('capture.imageHeight');
        
        if (!MathUtils.isPointInBounds(imageCoords, imageWidth, imageHeight)) {
            DOMUtils.showMessage('クリック位置が画像範囲外です', 'warning');
            return null;
        }
        
        return imageCoords;
    }
    
    /**
     * デバッグ情報の更新
     */
    updateDebugInfo() {
        const debugElement = DOMUtils.getElement('#captureDebugInfo');
        if (!debugElement) return;
        
        const zoomLevel = appState.get('capture.zoomLevel');
        const viewOffsetX = appState.get('capture.viewOffsetX');
        const viewOffsetY = appState.get('capture.viewOffsetY');
        const imageWidth = appState.get('capture.imageWidth');
        const imageHeight = appState.get('capture.imageHeight');
        
        debugElement.innerHTML = `
            <div class="debug-item">
                <span>ズーム:</span>
                <span>${MathUtils.roundTo(zoomLevel, 2)}x</span>
            </div>
            <div class="debug-item">
                <span>オフセット:</span>
                <span>${Math.round(viewOffsetX)}, ${Math.round(viewOffsetY)}</span>
            </div>
            <div class="debug-item">
                <span>画像サイズ:</span>
                <span>${imageWidth} × ${imageHeight}</span>
            </div>
        `;
    }
    
    /**
     * リソースの解放
     */
    destroy() {
        // イベントリスナーの削除
        this.eventListeners.forEach(({ element, event, handler, options }) => {
            element.removeEventListener(event, handler, options);
        });
        this.eventListeners = [];
        
        // キャンバスクリア
        if (this.canvas) {
            CanvasUtils.clearCanvas(this.canvas);
        }
        
        this.canvas = null;
        this.ctx = null;
        this.isInitialized = false;
    }
}
