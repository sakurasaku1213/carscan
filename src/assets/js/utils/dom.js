/**
 * DOM操作ユーティリティ
 * 要素の取得、イベント管理、UI更新などを担当
 */

export const DOMUtils = {
    /**
     * 要素を安全に取得
     */
    getElement(selector) {
        if (typeof selector === 'string') {
            return document.querySelector(selector);
        }
        return selector; // 既にDOM要素の場合
    },
    
    /**
     * 複数要素を取得
     */
    getElements(selector) {
        return Array.from(document.querySelectorAll(selector));
    },
    
    /**
     * 要素の存在チェック
     */
    exists(selector) {
        return this.getElement(selector) !== null;
    },
    
    /**
     * 要素の表示/非表示切り替え
     */
    toggle(selector, show = null) {
        const element = this.getElement(selector);
        if (!element) return false;
        
        if (show === null) {
            element.classList.toggle('hidden');
        } else {
            element.classList.toggle('hidden', !show);
        }
        return true;
    },
    
    /**
     * 要素を表示
     */
    show(selector) {
        return this.toggle(selector, true);
    },
    
    /**
     * 要素を非表示
     */
    hide(selector) {
        return this.toggle(selector, false);
    },
    
    /**
     * 要素のクラス操作
     */
    addClass(selector, className) {
        const element = this.getElement(selector);
        if (element) {
            element.classList.add(className);
            return true;
        }
        return false;
    },
    
    removeClass(selector, className) {
        const element = this.getElement(selector);
        if (element) {
            element.classList.remove(className);
            return true;
        }
        return false;
    },
    
    hasClass(selector, className) {
        const element = this.getElement(selector);
        return element ? element.classList.contains(className) : false;
    },
    
    /**
     * 要素の内容を設定
     */
    setText(selector, text) {
        const element = this.getElement(selector);
        if (element) {
            element.textContent = text;
            return true;
        }
        return false;
    },
    
    setHTML(selector, html) {
        const element = this.getElement(selector);
        if (element) {
            element.innerHTML = html;
            return true;
        }
        return false;
    },
    
    /**
     * 要素の値を取得/設定
     */
    getValue(selector) {
        const element = this.getElement(selector);
        return element ? element.value : null;
    },
    
    setValue(selector, value) {
        const element = this.getElement(selector);
        if (element) {
            element.value = value;
            return true;
        }
        return false;
    },
    
    /**
     * 要素の属性操作
     */
    getAttribute(selector, attribute) {
        const element = this.getElement(selector);
        return element ? element.getAttribute(attribute) : null;
    },
    
    setAttribute(selector, attribute, value) {
        const element = this.getElement(selector);
        if (element) {
            element.setAttribute(attribute, value);
            return true;
        }
        return false;
    },
    
    removeAttribute(selector, attribute) {
        const element = this.getElement(selector);
        if (element) {
            element.removeAttribute(attribute);
            return true;
        }
        return false;
    },
    
    /**
     * ボタンの有効/無効切り替え
     */
    enableButton(selector, enabled = true) {
        const element = this.getElement(selector);
        if (element) {
            element.disabled = !enabled;
            return true;
        }
        return false;
    },
    
    disableButton(selector) {
        return this.enableButton(selector, false);
    },
    
    /**
     * イベントリスナーの管理
     */
    addEventListener(selector, event, callback, options = {}) {
        const element = this.getElement(selector);
        if (element) {
            element.addEventListener(event, callback, options);
            return () => element.removeEventListener(event, callback, options);
        }
        return null;
    },
    
    /**
     * 要素の作成
     */
    createElement(tagName, attributes = {}, textContent = '') {
        const element = document.createElement(tagName);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else {
                element.setAttribute(key, value);
            }
        });
        
        if (textContent) {
            element.textContent = textContent;
        }
        
        return element;
    },
    
    /**
     * 要素の追加
     */
    appendChild(parentSelector, childElement) {
        const parent = this.getElement(parentSelector);
        if (parent && childElement) {
            parent.appendChild(childElement);
            return true;
        }
        return false;
    },
    
    /**
     * 要素の削除
     */
    removeElement(selector) {
        const element = this.getElement(selector);
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
            return true;
        }
        return false;
    },
    
    /**
     * フォームデータの取得
     */
    getFormData(formSelector) {
        const form = this.getElement(formSelector);
        if (!form) return null;
        
        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    },
    
    /**
     * ステータスメッセージの表示
     */
    showMessage(message, type = 'info', duration = 5000) {
        const messageContainer = this.getElement('#message-container') || this.createMessageContainer();
        
        const messageElement = this.createElement('div', {
            className: `status-message status-${type} fade-in`
        }, message);
        
        messageContainer.appendChild(messageElement);
        
        // 自動削除
        if (duration > 0) {
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.parentNode.removeChild(messageElement);
                }
            }, duration);
        }
        
        return messageElement;
    },
    
    /**
     * メッセージコンテナの作成
     */
    createMessageContainer() {
        const container = this.createElement('div', {
            id: 'message-container',
            className: 'fixed top-4 right-4 z-50 space-y-2'
        });
        
        document.body.appendChild(container);
        return container;
    },
    
    /**
     * 要素のサイズ取得
     */
    getElementSize(selector) {
        const element = this.getElement(selector);
        if (!element) return null;
        
        const rect = element.getBoundingClientRect();
        return {
            width: rect.width,
            height: rect.height,
            top: rect.top,
            left: rect.left,
            right: rect.right,
            bottom: rect.bottom
        };
    },
    
    /**
     * 要素が表示されているかチェック
     */
    isVisible(selector) {
        const element = this.getElement(selector);
        if (!element) return false;
        
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               style.opacity !== '0';
    },
    
    /**
     * 要素をスムーズスクロール
     */
    scrollToElement(selector, behavior = 'smooth') {
        const element = this.getElement(selector);
        if (element) {
            element.scrollIntoView({ behavior, block: 'center' });
            return true;
        }
        return false;
    },
    
    /**
     * 要素のアニメーション
     */
    animate(selector, keyframes, options = {}) {
        const element = this.getElement(selector);
        if (element && element.animate) {
            return element.animate(keyframes, {
                duration: 300,
                easing: 'ease-out',
                ...options
            });
        }
        return null;
    },
    
    /**
     * ファイル選択ダイアログの表示
     */
    selectFile(accept = '*/*', multiple = false) {
        return new Promise((resolve) => {
            const input = this.createElement('input', {
                type: 'file',
                accept: accept,
                multiple: multiple,
                style: 'display: none'
            });
            
            input.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                resolve(multiple ? files : files[0] || null);
                document.body.removeChild(input);
            });
            
            document.body.appendChild(input);
            input.click();
        });
    }
};
