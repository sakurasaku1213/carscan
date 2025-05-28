/**
 * 動画処理モジュール
 * 動画の読み込み、再生、制御を担当
 */

import { DOMUtils } from '../utils/dom.js';
import appState from '../core/state.js';

export class VideoManager {
    constructor() {
        this.videoElement = null;
        this.isInitialized = false;
    }
    
    /**
     * 初期化
     */
    async init() {
        try {
            this.setupVideoElement();
            this.setupEventListeners();
            this.isInitialized = true;
            console.log('✅ Video module initialized');
            return true;
        } catch (error) {
            console.error('❌ Video module initialization failed:', error);
            return false;
        }
    }
    
    /**
     * 動画要素のセットアップ
     */
    setupVideoElement() {
        this.videoElement = DOMUtils.getElement('#videoElement');
        if (!this.videoElement) {
            throw new Error('Video element not found');
        }
        
        // 動画要素の基本設定
        this.videoElement.controls = true;
        this.videoElement.preload = 'metadata';
        this.videoElement.muted = true; // Chrome自動再生ポリシー対応
        
        // 状態に設定
        appState.set('video.element', this.videoElement);
    }
    
    /**
     * イベントリスナーのセットアップ
     */
    setupEventListeners() {
        if (!this.videoElement) return;
        
        // 動画読み込み完了
        this.videoElement.addEventListener('loadedmetadata', () => {
            appState.update({
                'video.naturalWidth': this.videoElement.videoWidth,
                'video.naturalHeight': this.videoElement.videoHeight,
                'video.loaded': true
            });
            
            DOMUtils.showMessage('動画が読み込まれました', 'success');
            console.log(`Video loaded: ${this.videoElement.videoWidth}x${this.videoElement.videoHeight}`);
        });
        
        // 再生開始
        this.videoElement.addEventListener('play', () => {
            appState.set('video.playing', true);
        });
        
        // 再生停止
        this.videoElement.addEventListener('pause', () => {
            appState.set('video.playing', false);
        });
        
        // エラーハンドリング
        this.videoElement.addEventListener('error', (e) => {
            const error = this.videoElement.error;
            let message = '動画読み込みエラーが発生しました';
            
            if (error) {
                switch (error.code) {
                    case error.MEDIA_ERR_ABORTED:
                        message = '動画読み込みが中断されました';
                        break;
                    case error.MEDIA_ERR_NETWORK:
                        message = 'ネットワークエラーが発生しました';
                        break;
                    case error.MEDIA_ERR_DECODE:
                        message = '動画デコードエラーが発生しました';
                        break;
                    case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                        message = 'サポートされていない動画形式です';
                        break;
                }
            }
            
            DOMUtils.showMessage(message, 'error');
            console.error('Video error:', error);
        });
        
        // ファイル選択イベント
        const fileInput = DOMUtils.getElement('#videoFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // ファイル選択ボタン
        const selectButton = DOMUtils.getElement('#selectVideoButton');
        if (selectButton) {
            selectButton.addEventListener('click', () => this.selectVideoFile());
        }
    }
    
    /**
     * 動画ファイル選択
     */
    async selectVideoFile() {
        try {
            const file = await DOMUtils.selectFile('video/*');
            if (file) {
                await this.loadVideoFile(file);
            }
        } catch (error) {
            console.error('File selection error:', error);
            DOMUtils.showMessage('ファイル選択エラーが発生しました', 'error');
        }
    }
    
    /**
     * ファイル選択ハンドラー
     */
    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            await this.loadVideoFile(file);
        }
    }
    
    /**
     * 動画ファイルの読み込み
     */
    async loadVideoFile(file) {
        if (!this.videoElement) {
            throw new Error('Video element not initialized');
        }
        
        // ファイル形式チェック
        if (!this.isValidVideoFile(file)) {
            DOMUtils.showMessage('サポートされていない動画形式です', 'error');
            return false;
        }
        
        try {
            // 既存の動画をクリア
            this.clearVideo();
            
            // ファイルサイズチェック（100MB制限）
            const maxSize = 100 * 1024 * 1024; // 100MB
            if (file.size > maxSize) {
                DOMUtils.showMessage('ファイルサイズが大きすぎます（100MB以下にしてください）', 'warning');
            }
            
            // Object URLを作成
            const objectURL = URL.createObjectURL(file);
            
            // 動画を読み込み
            this.videoElement.src = objectURL;
            
            // 読み込み完了を待つ
            await new Promise((resolve, reject) => {
                const onLoad = () => {
                    cleanup();
                    resolve();
                };
                
                const onError = () => {
                    cleanup();
                    reject(new Error('動画読み込みに失敗しました'));
                };
                
                const cleanup = () => {
                    this.videoElement.removeEventListener('loadedmetadata', onLoad);
                    this.videoElement.removeEventListener('error', onError);
                };
                
                this.videoElement.addEventListener('loadedmetadata', onLoad, { once: true });
                this.videoElement.addEventListener('error', onError, { once: true });
                
                // タイムアウト設定（30秒）
                setTimeout(() => {
                    cleanup();
                    reject(new Error('動画読み込みがタイムアウトしました'));
                }, 30000);            });
            
            // 動画プレイヤーコンテナを表示
            const videoPlayerContainer = document.getElementById('videoPlayerContainer');
            if (videoPlayerContainer) {
                videoPlayerContainer.style.display = 'block';
            }
            
            // プレースホルダーを非表示
            const videoPlaceholder = document.getElementById('videoPlaceholder');
            if (videoPlaceholder) {
                videoPlaceholder.style.display = 'none';
            }
              // 状態を更新
            console.log('🔄 Setting video.loaded to true...');
            appState.set('video.loaded', true);
            console.log('🔄 Current video.loaded state:', appState.get('video.loaded'));
            appState.set('video.naturalWidth', this.videoElement.videoWidth);
            appState.set('video.naturalHeight', this.videoElement.videoHeight);
            appState.set('video.duration', this.videoElement.duration);
            
            DOMUtils.showMessage(`動画が読み込まれました: ${file.name}`, 'success');
            console.log(`Video loaded: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`);
            console.log(`Video dimensions: ${this.videoElement.videoWidth}x${this.videoElement.videoHeight}`);
            
            return true;
            
        } catch (error) {
            console.error('Video load error:', error);
            DOMUtils.showMessage(error.message || '動画読み込みエラーが発生しました', 'error');
            return false;
        }
    }

    /**
     * 動画ファイルの読み込み（エイリアス）
     */
    async loadVideo(file) {
        return await this.loadVideoFile(file);
    }
    
    /**
     * 動画ファイル形式の検証
     */
    isValidVideoFile(file) {
        const validTypes = [
            'video/mp4',
            'video/webm',
            'video/ogg',
            'video/quicktime',
            'video/x-msvideo' // AVI
        ];
        
        return validTypes.includes(file.type) || 
               file.name.match(/\.(mp4|webm|ogg|mov|avi)$/i);
    }
    
    /**
     * 動画のクリア
     */    clearVideo() {
        if (this.videoElement) {
            this.videoElement.pause();
            if (this.videoElement.src) {
                URL.revokeObjectURL(this.videoElement.src);
            }
            this.videoElement.src = '';
            this.videoElement.load();
        }
        
        // 動画プレイヤーコンテナを非表示
        const videoPlayerContainer = document.getElementById('videoPlayerContainer');
        if (videoPlayerContainer) {
            videoPlayerContainer.style.display = 'none';
        }
        
        // プレースホルダーを表示
        const videoPlaceholder = document.getElementById('videoPlaceholder');
        if (videoPlaceholder) {
            videoPlaceholder.style.display = 'block';
        }
        
        appState.update({
            'video.loaded': false,
            'video.playing': false,
            'video.naturalWidth': 0,
            'video.naturalHeight': 0
        });
    }
    
    /**
     * 現在のフレームをキャンバスに描画
     */
    captureCurrentFrame(canvas) {
        if (!this.videoElement || !canvas) {
            throw new Error('Video element or canvas not available');
        }
        
        if (!appState.get('video.loaded')) {
            throw new Error('Video not loaded');
        }
        
        const ctx = canvas.getContext('2d');
        const videoWidth = this.videoElement.videoWidth;
        const videoHeight = this.videoElement.videoHeight;
        
        // キャンバスサイズを動画に合わせる
        canvas.width = videoWidth;
        canvas.height = videoHeight;
        
        // 動画フレームを描画
        ctx.drawImage(this.videoElement, 0, 0, videoWidth, videoHeight);
        
        return {
            width: videoWidth,
            height: videoHeight,
            timestamp: this.videoElement.currentTime
        };
    }
    
    /**
     * 動画の再生
     */
    async play() {
        if (!this.videoElement) return false;
        
        try {
            await this.videoElement.play();
            return true;
        } catch (error) {
            console.error('Play error:', error);
            DOMUtils.showMessage('再生エラーが発生しました', 'error');
            return false;
        }
    }
    
    /**
     * 動画の一時停止
     */
    pause() {
        if (this.videoElement) {
            this.videoElement.pause();
            return true;
        }
        return false;
    }
    
    /**
     * 再生/一時停止の切り替え
     */
    togglePlayPause() {
        if (!this.videoElement) {
            console.warn('Video element not available for togglePlayPause.');
            return;
        }
        if (this.videoElement.paused) {
            this.play();
        } else {
            this.pause();
        }
    }
    
    /**
     * 指定時間にシーク
     */
    seekTo(time) {
        if (this.videoElement && appState.get('video.loaded')) {
            this.videoElement.currentTime = Math.max(0, Math.min(time, this.videoElement.duration));
            return true;
        }
        return false;
    }
    
    /**
     * 現在の時間を取得
     */
    getCurrentTime() {
        return this.videoElement ? this.videoElement.currentTime : 0;
    }
    
    /**
     * 動画の長さを取得
     */
    getDuration() {
        return this.videoElement ? this.videoElement.duration : 0;
    }
    
    /**
     * 動画情報の取得
     */
    getVideoInfo() {
        if (!this.videoElement || !appState.get('video.loaded')) {
            return null;
        }
        
        return {
            width: this.videoElement.videoWidth,
            height: this.videoElement.videoHeight,
            duration: this.videoElement.duration,
            currentTime: this.videoElement.currentTime,
            readyState: this.videoElement.readyState,
            paused: this.videoElement.paused,
            ended: this.videoElement.ended
        };
    }
    
    /**
     * リソースの解放
     */
    destroy() {
        this.clearVideo();
        this.videoElement = null;
        this.isInitialized = false;
    }
}
