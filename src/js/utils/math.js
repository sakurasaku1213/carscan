// Math utilities - 計算関連のユーティリティ関数

/**
 * 2点間の距離を計算
 * @param {Object} p1 - 点1 {x, y}
 * @param {Object} p2 - 点2 {x, y}
 * @returns {number} 距離
 */
function calculateDistance(p1, p2) { 
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
}

/**
 * 2点間の角度を計算（度数法）
 * @param {Object} p1 - 点1 {x, y}
 * @param {Object} p2 - 点2 {x, y}
 * @returns {number|null} 角度（度）
 */
function calculateAngle(p1, p2) { 
    if (!p1 || !p2) return null;
    const angleRad = Math.atan2(p2.y - p1.y, p2.x - p1.x);
    return angleRad * 180 / Math.PI;
}

/**
 * 画像座標をキャンバス表示座標に変換
 * @param {Object} imageCoords - 画像座標 {x, y}
 * @returns {Object|null} 表示座標 {x, y}
 */
function toDisplayCoords(imageCoords) {
    if (!imageCoords) return null;
    const displayX = (imageCoords.x - viewOffsetX) * zoomLevel;
    const displayY = (imageCoords.y - viewOffsetY) * zoomLevel;
    return { x: displayX, y: displayY };
}

/**
 * キャンバス座標を画像座標に変換
 * @param {Object} canvasCoords - キャンバス座標 {x, y}
 * @returns {Object} 画像座標 {x, y}
 */
function toImageCoords(canvasCoords) {
    const imageX = (canvasCoords.x / zoomLevel) + viewOffsetX;
    const imageY = (canvasCoords.y / zoomLevel) + viewOffsetY;
    return { x: imageX, y: imageY };
}
