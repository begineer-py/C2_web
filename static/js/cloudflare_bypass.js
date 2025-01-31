// FlareSolverr 服務管理模塊
const flaresolverrService = {
    // 啟動 FlareSolverr 服務
    startService: async function(userId, targetId) {
        try {
            console.log('正在啟動 FlareSolverr 服務...');
            const response = await fetch(`/user/${userId}/start_flaresolverr/${targetId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || '服務啟動失敗');
            }

            const result = await response.json();
            console.log('服務響應:', result);  // 添加日誌
            return result;
        } catch (error) {
            console.error('啟動 FlareSolverr 服務時發生錯誤:', error);
            throw error;
        }
    },

    // 更新狀態顯示
    updateStatus: function(message, isError = false, details = null) {
        console.log('更新狀態:', { message, isError, details });  // 添加日誌
        
        // 更新狀態消息
        const statusElement = document.getElementById('cloudflare-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = 'scan-status ' + (isError ? 'error' : 'success');
        }

        // 更新詳細信息顯示
        const detailsElement = document.querySelector('.cloudflare-details');
        if (detailsElement) {
            if (isError) {
                detailsElement.style.display = 'none';
            } else {
                detailsElement.style.display = 'block';
                
                // 更新狀態文本
                const statusText = detailsElement.querySelector('.status-text');
                if (statusText) {
                    statusText.textContent = '運行中';
                }

                // 如果有詳細信息，更新版本和運行時間
                if (details) {
                    const versionElement = detailsElement.querySelector('.version');
                    if (versionElement) {
                        versionElement.textContent = details.version || 'N/A';
                    }

                    const uptimeElement = detailsElement.querySelector('.uptime');
                    if (uptimeElement) {
                        uptimeElement.textContent = details.uptime || 'N/A';
                    }
                }
            }
        }
    },

    // 初始化事件監聽
    init: function() {
        const startButton = document.getElementById('cloudflareBypassButton');
        if (!startButton) {
            console.error('找不到 FlareSolverr 啟動按鈕');
            return;
        }

        startButton.addEventListener('click', async () => {
            const userId = startButton.getAttribute('data-user-id');
            const targetId = startButton.getAttribute('data-target-id');

            if (!userId || !targetId) {
                this.updateStatus('配置錯誤：缺少必要參數', true);
                return;
            }

            // 禁用按鈕並顯示加載狀態
            startButton.disabled = true;
            this.updateStatus('正在啟動服務...');

            try {
                const result = await this.startService(userId, targetId);
                console.log('服務結果:', result);  // 添加日誌

                if (result.success) {
                    this.updateStatus(
                        result.message,
                        false,
                        {
                            version: result.details?.version || 'N/A',
                            uptime: result.details?.uptime || 'N/A'
                        }
                    );
                    
                    // 更新 Cloudflare 檢測結果
                    if (result.is_cloudflare) {
                        this.updateStatus('檢測到 Cloudflare 保護，正在繞過...');
                    }
                } else {
                    throw new Error(result.message || '服務啟動失敗');
                }
            } catch (error) {
                console.error('服務啟動失敗:', error);
                this.updateStatus(error.message || '服務啟動失敗', true);
            } finally {
                // 重新啟用按鈕
                startButton.disabled = false;
            }
        });
    }
};

// 當 DOM 加載完成後初始化
document.addEventListener('DOMContentLoaded', () => {
    flaresolverrService.init();
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
    
    .cloudflare-details {
        margin-top: 15px;
        padding: 15px;
        background-color: #f5f5f5;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
    }
    
    .cloudflare-details h4 {
        margin: 0 0 10px 0;
        color: #1976d2;
    }
    
    .cloudflare-details .result-info p {
        margin: 5px 0;
        font-size: 14px;
    }
    
    .cloudflare-details .result-info strong {
        color: #333;
        margin-right: 8px;
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