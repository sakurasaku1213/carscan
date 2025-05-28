/**
 * キャンバス操作ユーティリティ
 * 描画、座標変換、イベント処理などを担当
 */

export const CanvasUtils = {
    /**
     * キャンバスを初期化
     */
    initCanvas(canvas, width = 800, height = 600) {
        if (!canvas) return null;
        
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        
        // 高DPI対応
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
        
        ctx.scale(dpr, dpr);
        
        return ctx;
    },
    
    /**
     * キャンバスをクリア
     */
    clearCanvas(canvas) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    },
    
    /**
     * 画像をキャンバスに描画
     */
    drawImage(ctx, image, x = 0, y = 0, width = null, height = null) {
        if (!ctx || !image) return;
        
        const drawWidth = width || image.width || image.naturalWidth;
        const drawHeight = height || image.height || image.naturalHeight;
        
        ctx.drawImage(image, x, y, drawWidth, drawHeight);
    },
    
    /**
     * 点を描画
     */
    drawPoint(ctx, point, color = '#FF0000', radius = 5, label = '') {
        if (!ctx || !point) return;
        
        // 点を描画
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
        ctx.fill();
        
        // 白い縁取り
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // ラベル描画
        if (label) {
            ctx.fillStyle = color;
            ctx.font = '12px Arial';
            ctx.fillText(label, point.x + radius + 5, point.y - radius);
        }
    },
    
    /**
     * 線を描画
     */
    drawLine(ctx, point1, point2, color = '#FF0000', width = 2, label = '') {
        if (!ctx || !point1 || !point2) return;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.setLineDash([]);
        
        ctx.beginPath();
        ctx.moveTo(point1.x, point1.y);
        ctx.lineTo(point2.x, point2.y);
        ctx.stroke();
        
        // 両端の点を描画
        this.drawPoint(ctx, point1, color, 4);
        this.drawPoint(ctx, point2, color, 4);
        
        // ラベル描画（線の中点）
        if (label) {
            const midX = (point1.x + point2.x) / 2;
            const midY = (point1.y + point2.y) / 2;
            
            ctx.fillStyle = color;
            ctx.font = '14px Arial';
            ctx.strokeStyle = '#FFFFFF';
            ctx.lineWidth = 3;
            ctx.strokeText(label, midX + 10, midY - 10);
            ctx.fillText(label, midX + 10, midY - 10);
        }
    },
    
    /**
     * 破線を描画
     */
    drawDashedLine(ctx, point1, point2, color = '#999999', dashPattern = [5, 5]) {
        if (!ctx || !point1 || !point2) return;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.setLineDash(dashPattern);
        
        ctx.beginPath();
        ctx.moveTo(point1.x, point1.y);
        ctx.lineTo(point2.x, point2.y);
        ctx.stroke();
        
        ctx.setLineDash([]); // リセット
    },
    
    /**
     * 矩形を描画
     */
    drawRectangle(ctx, x, y, width, height, strokeColor = '#000000', fillColor = null, lineWidth = 1) {
        if (!ctx) return;
        
        if (fillColor) {
            ctx.fillStyle = fillColor;
            ctx.fillRect(x, y, width, height);
        }
        
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.strokeRect(x, y, width, height);
    },
    
    /**
     * 円を描画
     */
    drawCircle(ctx, centerX, centerY, radius, strokeColor = '#000000', fillColor = null, lineWidth = 1) {
        if (!ctx) return;
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        
        if (fillColor) {
            ctx.fillStyle = fillColor;
            ctx.fill();
        }
        
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.stroke();
    },
    
    /**
     * テキストを描画（背景付き）
     */
    drawTextWithBackground(ctx, text, x, y, textColor = '#000000', backgroundColor = '#FFFFFF', padding = 4) {
        if (!ctx || !text) return;
        
        ctx.font = ctx.font || '12px Arial';
        const metrics = ctx.measureText(text);
        const textWidth = metrics.width;
        const textHeight = 12; // フォントサイズに依存
        
        // 背景描画
        ctx.fillStyle = backgroundColor;
        ctx.fillRect(x - padding, y - textHeight - padding, textWidth + padding * 2, textHeight + padding * 2);
        
        // 背景の縁取り
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 1;
        ctx.strokeRect(x - padding, y - textHeight - padding, textWidth + padding * 2, textHeight + padding * 2);
        
        // テキスト描画
        ctx.fillStyle = textColor;
        ctx.fillText(text, x, y);
    },
    
    /**
     * キャンバス座標を取得
     */
    getCanvasCoordinates(canvas, event) {
        if (!canvas || !event) return null;
        
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        
        return {
            x: (event.clientX - rect.left) * scaleX,
            y: (event.clientY - rect.top) * scaleY
        };
    },
    
    /**
     * キャンバスからデータURLを取得
     */
    toDataURL(canvas, type = 'image/png', quality = 0.9) {
        if (!canvas) return null;
        return canvas.toDataURL(type, quality);
    },
    
    /**
     * キャンバスのピクセルデータを取得
     */
    getImageData(canvas, x = 0, y = 0, width = null, height = null) {
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        const w = width || canvas.width;
        const h = height || canvas.height;
        
        return ctx.getImageData(x, y, w, h);
    },
    
    /**
     * グリッドを描画
     */
    drawGrid(ctx, width, height, gridSize = 20, color = '#E5E5E5') {
        if (!ctx) return;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 0.5;
        ctx.setLineDash([]);
        
        // 垂直線
        for (let x = 0; x <= width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        
        // 水平線
        for (let y = 0; y <= height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
    },
    
    /**
     * 十字線を描画
     */
    drawCrosshair(ctx, centerX, centerY, size = 20, color = '#FF0000') {
        if (!ctx) return;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
        
        // 水平線
        ctx.beginPath();
        ctx.moveTo(centerX - size, centerY);
        ctx.lineTo(centerX + size, centerY);
        ctx.stroke();
        
        // 垂直線
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - size);
        ctx.lineTo(centerX, centerY + size);
        ctx.stroke();
    }
};
