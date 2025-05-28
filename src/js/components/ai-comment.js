// AI Comment functionality - AI解析コメント機能

/**
 * AIコメントを生成
 */
async function generateAIComment() {
    const targetName = targetObjectNameInput.value.trim() || "対象物";
    const sizeMm = currentEstimatedSizeMm;
    
    if (sizeMm <= 0) {
        showMessage("有効な測定結果がありません。");
        return;
    }
    
    // ローディング状態開始
    getAiCommentButton.disabled = true;
    aiButtonLoader.classList.remove('hidden');
    aiCommentText.textContent = "AIがコメントを生成中...";
    
    try {
        // AIコメント生成のシミュレーション（実際のAPI呼び出しに置き換え可能）
        const comment = await simulateAIAnalysis(targetName, sizeMm);
        aiCommentText.textContent = comment;
    } catch (error) {
        aiCommentText.textContent = "AIコメントの生成に失敗しました。";
        showMessage("AIコメントの生成中にエラーが発生しました。");
    } finally {
        // ローディング状態終了
        getAiCommentButton.disabled = false;
        aiButtonLoader.classList.add('hidden');
    }
}

/**
 * AI分析をシミュレート
 * @param {string} objectName - 対象物の名前
 * @param {number} sizeMm - 測定サイズ（mm）
 * @returns {Promise<string>} AIコメント
 */
async function simulateAIAnalysis(objectName, sizeMm) {
    // 実際の実装では、ここでAI APIを呼び出します
    return new Promise((resolve) => {
        setTimeout(() => {
            const sizeCategory = getSizeCategory(sizeMm);
            const comment = generateContextualComment(objectName, sizeMm, sizeCategory);
            resolve(comment);
        }, 1500); // 1.5秒の遅延でシミュレート
    });
}

/**
 * サイズカテゴリを判定
 * @param {number} sizeMm - サイズ（mm）
 * @returns {string} カテゴリ
 */
function getSizeCategory(sizeMm) {
    if (sizeMm < 10) return "極小";
    if (sizeMm < 50) return "小";
    if (sizeMm < 200) return "中";
    if (sizeMm < 1000) return "大";
    return "極大";
}

/**
 * 文脈に応じたコメントを生成
 * @param {string} objectName - 対象物名
 * @param {number} sizeMm - サイズ（mm）
 * @param {string} category - サイズカテゴリ
 * @returns {string} コメント
 */
function generateContextualComment(objectName, sizeMm, category) {
    const templates = {
        "極小": [
            `${objectName}の測定サイズ${sizeMm}mmは、一般的な${objectName}と比較して非常に小さいサイズです。`,
            `${sizeMm}mmという測定結果は、精密部品や小型電子部品に相当するサイズ範囲です。`
        ],
        "小": [
            `${objectName}の${sizeMm}mmという測定値は、小型物品の範囲に入ります。`,
            `測定された${sizeMm}mmは、日常的な小物のサイズとして妥当な範囲です。`
        ],
        "中": [
            `${objectName}の測定サイズ${sizeMm}mmは、中型物品として標準的なサイズです。`,
            `${sizeMm}mmという結果は、一般的な${objectName}のサイズ範囲内にあると考えられます。`
        ],
        "大": [
            `${objectName}の${sizeMm}mmという測定値は、大型物品の範囲に該当します。`,
            `測定された${sizeMm}mmは、比較的大きなサイズの物品として分類されます。`
        ],
        "極大": [
            `${objectName}の測定サイズ${sizeMm}mmは、非常に大きな物品のサイズです。`,
            `${sizeMm}mmという測定結果は、大型設備や建造物クラスのサイズ範囲です。`
        ]
    };
    
    const categoryTemplates = templates[category] || templates["中"];
    const randomTemplate = categoryTemplates[Math.floor(Math.random() * categoryTemplates.length)];
    
    // 追加の精度情報
    const precisionNote = " 測定の精度は参照物の正確性に依存するため、複数回の測定を推奨します。";
    
    return randomTemplate + precisionNote;
}

/**
 * AIコメント機能を初期化
 */
function initAIComment() {
    getAiCommentButton.addEventListener('click', generateAIComment);
    
    // 測定完了時にAIコメントボタンを有効化
    document.addEventListener('measurementComplete', () => {
        getAiCommentButton.disabled = false;
    });
}
