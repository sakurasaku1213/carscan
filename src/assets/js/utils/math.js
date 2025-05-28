/**
 * 数学計算ユーティリティ
 * 座標変換、距離計算、スケール計算などを担当
 */

export const MathUtils = {
    /**
     * 2点間の距離を計算
     */
    calculateDistance(point1, point2) {
        const dx = point2.x - point1.x;
        const dy = point2.y - point1.y;
        return Math.sqrt(dx * dx + dy * dy);
    },
    
    /**
     * キャンバス座標を画像座標に変換
     */
    canvasToImageCoords(canvasX, canvasY, zoomLevel, viewOffsetX, viewOffsetY) {
        const imageX = (canvasX - viewOffsetX) / zoomLevel;
        const imageY = (canvasY - viewOffsetY) / zoomLevel;
        return { x: imageX, y: imageY };
    },
    
    /**
     * 画像座標をキャンバス座標に変換
     */
    imageToCanvasCoords(imageX, imageY, zoomLevel, viewOffsetX, viewOffsetY) {
        const canvasX = imageX * zoomLevel + viewOffsetX;
        const canvasY = imageY * zoomLevel + viewOffsetY;
        return { x: canvasX, y: canvasY };
    },
    
    /**
     * スケールを計算（mm/pixel）
     */
    calculateScale(pixelDistance, realSizeMm) {
        if (pixelDistance <= 0 || realSizeMm <= 0) {
            return 0;
        }
        return realSizeMm / pixelDistance;
    },
    
    /**
     * 実際のサイズを推定（mm）
     */
    estimateRealSize(pixelDistance, scale) {
        if (scale <= 0) return 0;
        return pixelDistance * scale;
    },
    
    /**
     * 点が矩形範囲内にあるかチェック
     */
    isPointInBounds(point, width, height) {
        return point.x >= 0 && point.x <= width && 
               point.y >= 0 && point.y <= height;
    },
    
    /**
     * 値を指定範囲内にクランプ
     */
    clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    },
    
    /**
     * 2つの矩形の交差判定
     */
    rectangleIntersection(rect1, rect2) {
        return !(rect1.x + rect1.width < rect2.x || 
                rect2.x + rect2.width < rect1.x || 
                rect1.y + rect1.height < rect2.y || 
                rect2.y + rect2.height < rect1.y);
    },
    
    /**
     * 角度を度からラジアンに変換
     */
    degToRad(degrees) {
        return degrees * (Math.PI / 180);
    },
    
    /**
     * 角度をラジアンから度に変換
     */
    radToDeg(radians) {
        return radians * (180 / Math.PI);
    },
    
    /**
     * 線分の角度を計算
     */
    calculateLineAngle(point1, point2) {
        const dx = point2.x - point1.x;
        const dy = point2.y - point1.y;
        return Math.atan2(dy, dx);
    },
    
    /**
     * 数値を指定桁数で丸める
     */
    roundTo(value, decimals = 2) {
        const factor = Math.pow(10, decimals);
        return Math.round(value * factor) / factor;
    },
    
    /**
     * 線形補間
     */
    lerp(start, end, t) {
        return start + (end - start) * t;
    },
    
    /**
     * ベジェ曲線の点を計算
     */
    bezierPoint(t, p0, p1, p2, p3) {
        const u = 1 - t;
        const tt = t * t;
        const uu = u * u;
        const uuu = uu * u;
        const ttt = tt * t;
        
        return {
            x: uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x,
            y: uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y
        };
    },
    
    /**
     * 統計情報の計算
     */
    calculateStats(values) {
        if (!values || values.length === 0) {
            return { min: 0, max: 0, avg: 0, median: 0, std: 0 };
        }
        
        const sorted = [...values].sort((a, b) => a - b);
        const sum = values.reduce((acc, val) => acc + val, 0);
        const avg = sum / values.length;
        
        const variance = values.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / values.length;
        const std = Math.sqrt(variance);
        
        const median = sorted.length % 2 === 0
            ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
            : sorted[Math.floor(sorted.length / 2)];
        
        return {
            min: sorted[0],
            max: sorted[sorted.length - 1],
            avg: this.roundTo(avg),
            median: this.roundTo(median),
            std: this.roundTo(std)
        };
    }
};
