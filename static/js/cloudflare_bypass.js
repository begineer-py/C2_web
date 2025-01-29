// Cloudflare 繞過功能模塊
const cloudflareBypass = {
    // 檢查 FlareSolverr 服務狀態
    checkFlareSolverr: async function() {
        try {
            console.log('正在檢查 FlareSolverr 服務狀態...');
            const response = await fetch('/api/flaresolverr/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            return result.status === 'running';
        } catch (error) {
            console.error('檢查 FlareSolverr 服務時發生錯誤:', error);
            return false;
        }
    },

    // 啟動 FlareSolverr 服務
    startFlareSolverr: async function() {
        try {
            console.log('正在啟動 FlareSolverr 服務...');
            const response = await fetch('/api/flaresolverr/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            return result.status === 'success';
        } catch (error) {
            console.error('啟動 FlareSolverr 服務時發生錯誤:', error);
            return false;
        }
    },

    // 等待 FlareSolverr 服務就緒
    waitForFlareSolverr: async function(maxAttempts = 10) {
        for (let i = 0; i < maxAttempts; i++) {
            if (await this.checkFlareSolverr()) {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, 2000)); // 等待2秒
        }
        return false;
    },

    // 檢查 Cloudflare 保護
    checkProtection: async function(userId, targetId) {
        try {
            console.log('正在檢查 Cloudflare 保護狀態...');
            const response = await fetch(`/user/${userId}/cloudflare/${targetId}/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            console.log('Cloudflare 檢查結果:', result);
            
            return {
                success: response.ok,
                hasProtection: result.has_protection,
                message: result.message
            };
        } catch (error) {
            console.error('檢查 Cloudflare 保護時發生錯誤:', error);
            return {
                success: false,
                hasProtection: false,
                message: '檢查失敗: ' + error.message
            };
        }
    },

    // 繞過 Cloudflare 保護
    bypass: async function(userId, targetId) {
        try {
            console.log('正在嘗試繞過 Cloudflare 保護...');
            const response = await fetch(`/user/${userId}/cloudflare/${targetId}/bypass`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            console.log('Cloudflare 繞過結果:', result);
            
            return {
                success: response.ok,
                data: result.data,
                message: result.message
            };
        } catch (error) {
            console.error('繞過 Cloudflare 保護時發生錯誤:', error);
            return {
                success: false,
                data: null,
                message: '繞過失敗: ' + error.message
            };
        }
    },

    // 更新狀態顯示
    updateStatus: function(message, isError = false, className = '') {
        const statusElement = document.querySelector('.cloudflare-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = 'cloudflare-status ' + className;
            if (isError) {
                statusElement.classList.add('error');
            }
        }
    },

    // 顯示結果
    displayResult: function(data) {
        const resultContainer = document.querySelector('.cloudflare-details');
        if (!resultContainer) return;

        // 更新基本信息
        resultContainer.querySelector('.status-text').textContent = '成功';
        resultContainer.querySelector('.cookies-count').textContent = 
            Object.keys(data.cookies || {}).length;
        resultContainer.querySelector('.user-agent').textContent = 
            data.user_agent || '未提供';

        // 更新 Cookies 列表
        const cookiesList = resultContainer.querySelector('.cookies-list');
        cookiesList.innerHTML = '';
        
        if (data.cookies && Object.keys(data.cookies).length > 0) {
            Object.entries(data.cookies).forEach(([name, value]) => {
                const cookieItem = document.createElement('div');
                cookieItem.className = 'cookie-item';
                cookieItem.innerHTML = `
                    <span class="cookie-name">${name}</span>: 
                    <span class="cookie-value">${value}</span>
                `;
                cookiesList.appendChild(cookieItem);
            });
        } else {
            cookiesList.innerHTML = '<div class="no-cookies">沒有可用的 Cookies</div>';
        }

        // 顯示結果容器
        resultContainer.style.display = 'block';
    },

    // 初始化事件監聽
    init: function() {
        const bypassButton = document.getElementById('cloudflareBypassButton');
        if (!bypassButton) {
            console.error('找不到 Cloudflare 繞過按鈕');
            return;
        }

        bypassButton.addEventListener('click', async () => {
            const userId = bypassButton.dataset.userId;
            const targetId = bypassButton.dataset.targetId;

            if (!userId || !targetId) {
                console.error('缺少必要的用戶ID或目標ID');
                this.updateStatus('配置錯誤：缺少必要參數', true);
                return;
            }

            // 禁用按鈕
            bypassButton.disabled = true;
            this.updateStatus('正在檢查 FlareSolverr 服務...', false, 'checking');

            try {
                // 檢查並確保 FlareSolverr 服務運行
                if (!await this.checkFlareSolverr()) {
                    this.updateStatus('正在啟動 FlareSolverr 服務...', false, 'checking');
                    if (!await this.startFlareSolverr()) {
                        throw new Error('無法啟動 FlareSolverr 服務');
                    }
                    if (!await this.waitForFlareSolverr()) {
                        throw new Error('FlareSolverr 服務啟動超時');
                    }
                }

                this.updateStatus('正在檢查 Cloudflare 保護...', false, 'checking');

                // 檢查是否有 Cloudflare 保護
                const checkResult = await this.checkProtection(userId, targetId);
                
                if (!checkResult.success) {
                    throw new Error(checkResult.message);
                }

                if (!checkResult.hasProtection) {
                    this.updateStatus('未檢測到 Cloudflare 保護', false, 'success');
                    document.querySelector('.cloudflare-details').style.display = 'none';
                    return;
                }

                // 嘗試繞過保護
                this.updateStatus('正在繞過 Cloudflare 保護...', false, 'bypassing');
                const bypassResult = await this.bypass(userId, targetId);

                if (!bypassResult.success) {
                    throw new Error(bypassResult.message);
                }

                this.updateStatus('成功繞過 Cloudflare 保護', false, 'success');
                this.displayResult(bypassResult.data);
                
                // 觸發成功事件
                const event = new CustomEvent('cloudflareBypassSuccess', {
                    detail: bypassResult.data
                });
                document.dispatchEvent(event);

            } catch (error) {
                console.error('Cloudflare 繞過過程中發生錯誤:', error);
                this.updateStatus(error.message, true);
                document.querySelector('.cloudflare-details').style.display = 'none';
            } finally {
                // 重新啟用按鈕
                bypassButton.disabled = false;
            }
        });
    }
};

// 當 DOM 加載完成後初始化
document.addEventListener('DOMContentLoaded', () => {
    cloudflareBypass.init();
});

// 添加樣式
const style = document.createElement('style');
style.textContent = `
    .cloudflare-status {
        margin-top: 10px;
        padding: 8px;
        border-radius: 4px;
        font-size: 14px;
    }
    
    .cloudflare-status.success {
        background-color: #e8f5e9;
        color: #2e7d32;
        border: 1px solid #a5d6a7;
    }
    
    .cloudflare-status.error {
        background-color: #ffebee;
        color: #c62828;
        border: 1px solid #ef9a9a;
    }
    
    #cloudflareBypassButton {
        background-color: #1976d2;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: background-color 0.3s;
    }
    
    #cloudflareBypassButton:hover {
        background-color: #1565c0;
    }
    
    #cloudflareBypassButton:disabled {
        background-color: #90caf9;
        cursor: not-allowed;
    }
`;
document.head.appendChild(style); 