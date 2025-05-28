/**
 * アプリケーション状態管理
 * 全体的な状態の一元管理を行う
 */

class AppState {
    constructor() {
        this.state = this.getInitialState();
        this.listeners = new Map();
    }

    /**
     * 初期状態の取得
     */
    getInitialState() {
        return {
            video: {
                element: null,
                naturalWidth: 0,
                naturalHeight: 0,
                loaded: false,
                playing: false,
                currentTime: 0,
                duration: 0
            },
            capture: {
                canvas: null,
                imageElement: null,
                imageWidth: 0,
                imageHeight: 0,
                zoomLevel: 1.0,
                viewOffsetX: 0,
                viewOffsetY: 0,
                isPanning: false,
                lastMouseX: 0,
                lastMouseY: 0
            },
            measurement: {
                mode: 'none',
                referencePoints: [],
                targetPoints: [],
                referenceSize: 0,
                scale: 0,
                estimatedSize: 0
            },
            ui: {
                isInitialized: false,
                currentStep: 1,
                debugMode: false
            }
        };
    }

    /**
     * 状態の取得
     */
    get(path = null) {
        if (!path) return this.state;
        
        const keys = path.split('.');
        let value = this.state;
        
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return undefined;
            }
        }
        
        return value;
    }

    /**
     * 状態の設定
     */
    set(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let current = this.state;
        
        // ネストしたオブジェクトを作成
        for (const key of keys) {
            if (!(key in current) || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        const oldValue = current[lastKey];
        current[lastKey] = value;
        
        // 変更通知
        this.notify(path, value, oldValue);
        
        return this;
    }

    /**
     * 複数の状態を一度に更新
     */
    update(updates) {
        Object.entries(updates).forEach(([path, value]) => {
            this.set(path, value);
        });
        return this;
    }

    /**
     * 状態変更の監視
     */
    subscribe(path, callback) {
        if (!this.listeners.has(path)) {
            this.listeners.set(path, new Set());
        }
        this.listeners.get(path).add(callback);
        
        console.log(`🔄 Subscribed to path: ${path}`);
        console.log(`🔄 Current listeners:`, Array.from(this.listeners.keys()));
        
        // 購読解除関数を返す
        return () => {
            const pathListeners = this.listeners.get(path);
            if (pathListeners) {
                pathListeners.delete(callback);
                if (pathListeners.size === 0) {
                    this.listeners.delete(path);
                }
            }
        };
    }

    /**
     * 変更通知
     */
    notify(path, newValue, oldValue) {
        console.log(`🔄 Notifying path: ${path} = ${newValue}`);
        console.log(`🔄 Available listeners:`, Array.from(this.listeners.keys()));
        
        // 直接のパスリスナー
        const pathListeners = this.listeners.get(path);
        if (pathListeners) {
            console.log(`🔄 Found direct listeners for ${path}:`, pathListeners.size);
            pathListeners.forEach(callback => {
                try {
                    callback(newValue, oldValue, path);
                } catch (error) {
                    console.error(`State listener error for path "${path}":`, error);
                }
            });
        } else {
            console.log(`🔄 No direct listeners for ${path}`);
        }

        // ワイルドカードリスナーをチェック
        this.listeners.forEach((listeners, listenerPath) => {
            if (listenerPath.includes('*')) {
                const wildcardPattern = listenerPath.replace(/\*/g, '[^.]+');
                const regex = new RegExp(`^${wildcardPattern}$`);
                if (regex.test(path)) {
                    console.log(`🔄 Found wildcard listeners for ${listenerPath} matching ${path}:`, listeners.size);
                    listeners.forEach(callback => {
                        try {
                            callback(newValue, oldValue, path);
                        } catch (error) {
                            console.error(`Wildcard state listener error for path "${listenerPath}":`, error);
                        }
                    });
                }
            }
        });
        
        // 親パスの監視者にも通知
        const pathParts = path.split('.');
        for (let i = pathParts.length - 1; i > 0; i--) {
            const parentPath = pathParts.slice(0, i).join('.');
            console.log(`🔄 Checking parent path: ${parentPath}`);
            const parentListeners = this.listeners.get(parentPath);
            if (parentListeners) {
                console.log(`🔄 Found parent listeners for ${parentPath}:`, parentListeners.size);
                parentListeners.forEach(callback => {
                    try {
                        callback(this.get(parentPath), undefined, parentPath);
                    } catch (error) {
                        console.error(`Parent state listener error for path "${parentPath}":`, error);
                    }
                });
            }
        }
    }

    /**
     * 状態のリセット
     */
    reset(path = null) {
        if (path) {
            const keys = path.split('.');
            const lastKey = keys.pop();
            let current = this.state;
            
            for (const key of keys) {
                if (!(key in current)) return this;
                current = current[key];
            }
            
            delete current[lastKey];
        } else {
            // 全体リセット
            this.state = this.getInitialState();
        }
        
        return this;
    }

    /**
     * 状態の検証
     */
    validate() {
        const errors = [];
        
        // 必要な要素が存在するかチェック
        if (this.get('measurement.mode') === 'reference' && this.get('measurement.referencePoints').length === 0) {
            errors.push('参照点が設定されていません');
        }
        
        if (this.get('measurement.mode') === 'target' && this.get('measurement.targetPoints').length === 0) {
            errors.push('測定点が設定されていません');
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }

    /**
     * 状態のダンプ（デバッグ用）
     */
    dump() {
        return JSON.stringify(this.state, (key, value) => {
            if (value instanceof HTMLElement) {
                return `[HTMLElement: ${value.tagName}]`;
            }
            return value;
        }, 2);
    }
}

// シングルトンインスタンス
const appState = new AppState();

// グローバルアクセス用（デバッグ時）
if (typeof window !== 'undefined') {
    window.appState = appState;
}

export default appState;
