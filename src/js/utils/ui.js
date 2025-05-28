// UI utilities - UI関連のユーティリティ関数

/**
 * UI要素にテキストを表示
 * @param {HTMLElement} element - 対象要素
 * @param {string} text - 表示テキスト
 */
function showUIMessage(element, text) {
    element.textContent = text;
}

/**
 * メッセージボックスを表示
 * @param {string} message - メッセージ
 * @param {boolean} isError - エラーメッセージかどうか
 */
function showMessage(message, isError = true) {  
    messageText.textContent = message;
    messageBox.classList.remove('hidden');
    
    // エラーメッセージのスタイル
    messageBox.classList.toggle('bg-red-100', isError); 
    messageBox.classList.toggle('border-red-400', isError); 
    messageBox.classList.toggle('text-red-700', isError);
    
    // 成功メッセージのスタイル
    messageBox.classList.toggle('bg-green-100', !isError); 
    messageBox.classList.toggle('border-green-400', !isError); 
    messageBox.classList.toggle('text-green-700', !isError);
    
    messageBox.querySelector('strong').textContent = isError ? "エラー: " : "情報: ";
}

/**
 * メッセージボックスを隠す
 */
function hideMessage() {
    messageBox.classList.add('hidden');
}
