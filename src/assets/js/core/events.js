/**
 * イベント管理システム
 * 
 * モジュール間の通信とイベント処理を統一管理：
 * - グローバルイベントバス
 * - イベントの型安全性確保
 * - デバッグとログ機能
 * - メモリリーク防止
 */

export class EventManager {
    constructor() {
        this.listeners = new Map(); // eventType -> Set of listeners
        this.oneTimeListeners = new Map(); // eventType -> Set of one-time listeners
        this.debugMode = false;
        this.eventHistory = [];
        this.maxHistorySize = 100;
        
        console.log('📡 EventManager initialized');
    }
    
    /**
     * イベントリスナーを追加
     * @param {string} eventType - イベントタイプ
     * @param {Function} callback - コールバック関数
     * @param {Object} options - オプション
     * @returns {Function} リスナー削除用関数
     */
    on(eventType, callback, options = {}) {
        if (typeof callback !== 'function') {
            throw new Error('Callback must be a function');
        }
        
        const listenersMap = options.once ? this.oneTimeListeners : this.listeners;
        
        if (!listenersMap.has(eventType)) {
            listenersMap.set(eventType, new Set());
        }
        
        const listenerSet = listenersMap.get(eventType);
        
        // 重複チェック
        if (listenerSet.has(callback)) {
            console.warn(`⚠️ Duplicate listener for event: ${eventType}`);
            return () => {}; // 何もしない関数を返す
        }
        
        listenerSet.add(callback);
        
        if (this.debugMode) {
            console.log(`📡 Listener added for event: ${eventType}`);
        }
        
        // リスナー削除用関数を返す
        return () => this.off(eventType, callback);
    }
    
    /**
     * 一回限りのイベントリスナーを追加
     * @param {string} eventType - イベントタイプ
     * @param {Function} callback - コールバック関数
     * @returns {Function} リスナー削除用関数
     */
    once(eventType, callback) {
        return this.on(eventType, callback, { once: true });
    }
    
    /**
     * イベントリスナーを削除
     * @param {string} eventType - イベントタイプ
     * @param {Function} callback - コールバック関数
     */
    off(eventType, callback) {
        // 通常のリスナーから削除
        if (this.listeners.has(eventType)) {
            const listenerSet = this.listeners.get(eventType);
            listenerSet.delete(callback);
            
            if (listenerSet.size === 0) {
                this.listeners.delete(eventType);
            }
        }
        
        // 一回限りのリスナーからも削除
        if (this.oneTimeListeners.has(eventType)) {
            const oneTimeSet = this.oneTimeListeners.get(eventType);
            oneTimeSet.delete(callback);
            
            if (oneTimeSet.size === 0) {
                this.oneTimeListeners.delete(eventType);
            }
        }
        
        if (this.debugMode) {
            console.log(`📡 Listener removed for event: ${eventType}`);
        }
    }
    
    /**
     * 特定のイベントタイプのすべてのリスナーを削除
     * @param {string} eventType - イベントタイプ
     */
    removeAllListeners(eventType) {
        if (eventType) {
            this.listeners.delete(eventType);
            this.oneTimeListeners.delete(eventType);
            
            if (this.debugMode) {
                console.log(`📡 All listeners removed for event: ${eventType}`);
            }
        } else {
            // すべてのリスナーを削除
            this.listeners.clear();
            this.oneTimeListeners.clear();
            
            if (this.debugMode) {
                console.log('📡 All listeners removed');
            }
        }
    }
    
    /**
     * イベントを発火
     * @param {string} eventType - イベントタイプ
     * @param {*} data - イベントデータ
     * @param {Object} options - オプション
     */
    emit(eventType, data = null, options = {}) {
        const event = {
            type: eventType,
            data: data,
            timestamp: Date.now(),
            target: options.target || null
        };
        
        // イベント履歴に追加
        this.addToHistory(event);
        
        if (this.debugMode) {
            console.log(`📡 Event emitted: ${eventType}`, data);
        }
        
        // 通常のリスナーを実行
        this.executeListeners(this.listeners.get(eventType), event);
        
        // 一回限りのリスナーを実行して削除
        const oneTimeListeners = this.oneTimeListeners.get(eventType);
        if (oneTimeListeners) {
            this.executeListeners(oneTimeListeners, event);
            this.oneTimeListeners.delete(eventType);
        }
    }
    
    /**
     * リスナーを実行
     * @param {Set} listenerSet - リスナーのセット
     * @param {Object} event - イベントオブジェクト
     */
    executeListeners(listenerSet, event) {
        if (!listenerSet) return;
        
        // リスナーのコピーを作成して実行中の変更に対応
        const listenersArray = Array.from(listenerSet);
        
        for (const listener of listenersArray) {
            try {
                listener(event);
            } catch (error) {
                console.error(`❌ Error in event listener for ${event.type}:`, error);
                
                // エラーイベントを発火（無限ループ防止のため、エラーイベント自体はキャッチしない）
                if (event.type !== 'error') {
                    this.emit('error', {
                        originalEvent: event,
                        error: error,
                        listener: listener
                    });
                }
            }
        }
    }
    
    /**
     * イベント履歴に追加
     * @param {Object} event - イベントオブジェクト
     */
    addToHistory(event) {
        this.eventHistory.push(event);
        
        // 履歴サイズの制限
        if (this.eventHistory.length > this.maxHistorySize) {
            this.eventHistory.shift();
        }
    }
    
    /**
     * イベント履歴を取得
     * @param {number} limit - 取得する件数の上限
     * @returns {Array} イベント履歴
     */
    getHistory(limit = 10) {
        return this.eventHistory.slice(-limit);
    }
    
    /**
     * 特定のイベントタイプの履歴を取得
     * @param {string} eventType - イベントタイプ
     * @param {number} limit - 取得する件数の上限
     * @returns {Array} フィルタされたイベント履歴
     */
    getHistoryByType(eventType, limit = 10) {
        return this.eventHistory
            .filter(event => event.type === eventType)
            .slice(-limit);
    }
    
    /**
     * イベントタイプのリスナー数を取得
     * @param {string} eventType - イベントタイプ
     * @returns {number} リスナー数
     */
    getListenerCount(eventType) {
        const regularCount = this.listeners.has(eventType) ? this.listeners.get(eventType).size : 0;
        const onceCount = this.oneTimeListeners.has(eventType) ? this.oneTimeListeners.get(eventType).size : 0;
        return regularCount + onceCount;
    }
    
    /**
     * すべてのイベントタイプとリスナー数を取得
     * @returns {Object} イベントタイプ別リスナー数
     */
    getAllListenerCounts() {
        const counts = {};
        
        // 通常のリスナー
        for (const [eventType, listenerSet] of this.listeners) {
            counts[eventType] = (counts[eventType] || 0) + listenerSet.size;
        }
        
        // 一回限りのリスナー
        for (const [eventType, listenerSet] of this.oneTimeListeners) {
            counts[eventType] = (counts[eventType] || 0) + listenerSet.size;
        }
        
        return counts;
    }
    
    /**
     * デバッグモードの設定
     * @param {boolean} enabled - デバッグモードを有効にするか
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        console.log(`📡 Debug mode ${enabled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * デバッグ情報を取得
     * @returns {Object} デバッグ情報
     */
    getDebugInfo() {
        return {
            listenerCounts: this.getAllListenerCounts(),
            historySize: this.eventHistory.length,
            recentEvents: this.getHistory(5).map(e => ({
                type: e.type,
                timestamp: e.timestamp,
                hasData: e.data !== null
            }))
        };
    }
    
    /**
     * イベント統計を取得
     * @returns {Object} イベント統計
     */
    getStatistics() {
        const typeStats = {};
        
        for (const event of this.eventHistory) {
            if (!typeStats[event.type]) {
                typeStats[event.type] = {
                    count: 0,
                    firstSeen: event.timestamp,
                    lastSeen: event.timestamp
                };
            }
            
            typeStats[event.type].count++;
            typeStats[event.type].lastSeen = event.timestamp;
        }
        
        return {
            totalEvents: this.eventHistory.length,
            uniqueTypes: Object.keys(typeStats).length,
            typeStats: typeStats,
            activeListeners: this.getAllListenerCounts()
        };
    }
    
    /**
     * リソースのクリーンアップ
     */
    destroy() {
        this.removeAllListeners();
        this.eventHistory = [];
        console.log('📡 EventManager destroyed');
    }
}

/**
 * 事前定義されたイベントタイプ
 */
export const EventTypes = {
    // アプリケーションレベル
    APP_INITIALIZED: 'app:initialized',
    APP_ERROR: 'app:error',
    
    // ビデオ関連
    VIDEO_LOADED: 'video:loaded',
    VIDEO_PLAY_STATE_CHANGED: 'video:playStateChanged',
    VIDEO_TIME_UPDATE: 'video:timeUpdate',
    VIDEO_SEEK: 'video:seek',
    VIDEO_ERROR: 'video:error',
    
    // キャプチャ関連
    FRAME_CAPTURED: 'capture:frameCaptured',
    CAPTURE_ZOOM_CHANGED: 'capture:zoomChanged',
    CAPTURE_PAN_CHANGED: 'capture:panChanged',
    CAPTURE_REDRAW_REQUESTED: 'capture:redrawRequested',
    CAPTURE_ERROR: 'capture:error',
    
    // 測定関連
    MEASUREMENT_STARTED: 'measurement:started',
    MEASUREMENT_REFERENCE_POINT_ADDED: 'measurement:referencePointAdded',
    MEASUREMENT_TARGET_POINT_ADDED: 'measurement:targetPointAdded',
    MEASUREMENT_COMPLETED: 'measurement:completed',
    MEASUREMENT_RESET: 'measurement:reset',
    MEASUREMENT_ERROR: 'measurement:error',
    
    // UI関連
    UI_MESSAGE_SHOW: 'ui:messageShow',
    UI_STATE_CHANGE: 'ui:stateChange',
    
    // システム関連
    SYSTEM_RESIZE: 'system:resize',
    SYSTEM_KEYBOARD_SHORTCUT: 'system:keyboardShortcut'
};

/**
 * グローバルイベントマネージャーインスタンス
 */
export const globalEventManager = new EventManager();

// デフォルトエクスポート
export default EventManager;
