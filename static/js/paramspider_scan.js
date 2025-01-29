// ParamSpider 掃描狀態
let isParamSpiderScanning = false;

// 确保扫描结果容器存在
function ensureScanResultsContainer() {
    let container = document.querySelector('.scan-results-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'scan-results-container';
        // 将容器添加到合适的位置，例如 paramSpiderButton 的父元素之后
        const button = document.querySelector('#paramSpiderButton');
        if (button && button.parentElement) {
            button.parentElement.appendChild(container);
        }
    }
    return container;
}

function ensureScanResultsArea() {
    console.log('Ensuring scan results area...'); // 添加调试日志
    
    const targetId = document.querySelector('#paramSpiderButton')?.dataset?.targetId;
    if (!targetId) {
        console.error('Target ID not found');
        return null;
    }
    
    let resultsArea = document.getElementById(`paramspider-result-${targetId}`);
    console.log('Existing results area:', resultsArea); // 添加调试日志
    
    if (!resultsArea) {
        console.log('Creating new results area...'); // 添加调试日志
        resultsArea = document.createElement('div');
        resultsArea.id = `paramspider-result-${targetId}`;
        resultsArea.className = 'scan-results paramspider-results';
        
        // 创建结果区域的各个部分
        const headerDiv = document.createElement('div');
        headerDiv.className = 'results-header';
        headerDiv.innerHTML = `
            <h3>ParamSpider 掃描結果</h3>
            <div class="results-controls">
                <button onclick="showLatestResult(${targetId})" class="control-button">
                    查看最新結果
                </button>
                <button onclick="showAllResults(${targetId})" class="control-button">
                    查看歷史結果
                </button>
            </div>
        `;
        
        const statusDiv = document.createElement('div');
        statusDiv.className = 'status-area';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'results-content';
        
        // 按顺序添加各个部分
        resultsArea.appendChild(headerDiv);
        resultsArea.appendChild(statusDiv);
        resultsArea.appendChild(contentDiv);
        
        // 确保容器存在并添加结果区域
        const scanResultsContainer = ensureScanResultsContainer();
        if (scanResultsContainer) {
            scanResultsContainer.appendChild(resultsArea);
            console.log('Results area added to container'); // 添加调试日志
        } else {
            console.error('Failed to find or create results container');
            return null;
        }
    } else {
        // 如果结果区域已存在，确保所有必要的子元素都存在
        if (!resultsArea.querySelector('.results-header')) {
            const headerDiv = document.createElement('div');
            headerDiv.className = 'results-header';
            headerDiv.innerHTML = `
                <h3>ParamSpider 掃描結果</h3>
                <div class="results-controls">
                    <button onclick="showLatestResult(${targetId})" class="control-button">
                        查看最新結果
                    </button>
                    <button onclick="showAllResults(${targetId})" class="control-button">
                        查看歷史結果
                    </button>
                </div>
            `;
            resultsArea.insertBefore(headerDiv, resultsArea.firstChild);
        }
        
        if (!resultsArea.querySelector('.status-area')) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'status-area';
            resultsArea.appendChild(statusDiv);
        }
        
        if (!resultsArea.querySelector('.results-content')) {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'results-content';
            resultsArea.appendChild(contentDiv);
        }
    }
    
    // 验证所有必要的区域是否存在
    const statusArea = resultsArea.querySelector('.status-area');
    const contentArea = resultsArea.querySelector('.results-content');
    console.log('Status area found:', statusArea); // 添加调试日志
    console.log('Content area found:', contentArea); // 添加调试日志
    
    return resultsArea;
}

function updateStatus(message, isError = false) {
    console.log('Updating status:', message, 'isError:', isError); // 添加调试日志
    
    const targetId = document.querySelector('#paramSpiderButton')?.dataset?.targetId;
    if (!targetId) {
        console.error('Target ID not found');
        return;
    }
    
    const resultsArea = ensureScanResultsArea();  // 先確保結果區域存在
    if (!resultsArea) {
        console.error('Failed to create or find results area');
        return;
    }
    
    let statusArea = resultsArea.querySelector('.status-area');
    if (!statusArea) {
        console.log('Status area not found, creating it...'); // 添加调试日志
        statusArea = document.createElement('div');
        statusArea.className = 'status-area';
        // 在 results-header 之后插入
        const header = resultsArea.querySelector('.results-header');
        if (header && header.nextSibling) {
            resultsArea.insertBefore(statusArea, header.nextSibling);
        } else {
            resultsArea.appendChild(statusArea);
        }
    }
    
    const statusHtml = `<div class="status-message ${isError ? 'error' : ''}">${message}</div>`;
    console.log('Setting status HTML:', statusHtml); // 添加调试日志
    statusArea.innerHTML = statusHtml;
    
    // 如果是错误消息，滚动到状态区域
    if (isError) {
        statusArea.scrollIntoView({ behavior: 'smooth' });
    }
}

function displayResult(result) {
    console.log('Displaying result:', result);
    
    const targetId = document.querySelector('#paramSpiderButton')?.dataset?.targetId;
    if (!targetId) {
        console.error('Target ID not found');
        return;
    }
    
    const resultsArea = document.getElementById(`paramspider-result-${targetId}`);
    if (!resultsArea) {
        console.error('Results area not found');
        return;
    }
    
    const resultsContent = resultsArea.querySelector('.results-content');
    if (!resultsContent) {
        console.error('Results content area not found');
        return;
    }
    
    if (!result) {
        console.error('No result provided');
        resultsContent.innerHTML = '<div class="alert alert-warning">未找到有效的扫描结果</div>';
        return;
    }
    
    let resultHtml = `
        <div class="result-item">
            <div class="result-header">
                <span>掃描時間: ${result.created_at || '未知'}</span>
                <span>狀態: ${result.status || '未知'}</span>
            </div>
            <div class="result-stats">
                <span>總 URL 數: ${result.total_urls || 0}</span>
                <span>唯一參數數: ${result.unique_parameters || 0}</span>
            </div>`;
            
    if (result.result_text) {
        resultHtml += `
            <div class="result-text" id="result-text-${targetId}">
                <pre>${result.result_text}</pre>
            </div>
            <div class="result-actions">
                <button onclick="copyResultText('result-text-${targetId}')" class="copy-button">
                    複製結果
                </button>
                ${result.id ? `
                <button onclick="downloadParamSpiderResult('${targetId}', ${result.id})" class="download-button">
                    下載結果
                </button>
                ` : ''}
            </div>`;
    } else {
        resultHtml += `
            <div class="alert alert-info">
                沒有詳細的掃描結果文本
            </div>`;
    }
    
    resultHtml += `</div>`;
    
    resultsContent.innerHTML = resultHtml;
    
    if (result.error_message) {
        console.warn('Error message in result:', result.error_message);
        updateStatus(result.error_message, true);
    }
}

function displayAllResults(results) {
    const targetId = document.querySelector('#paramSpiderButton').dataset.targetId;
    const resultsArea = document.getElementById(`paramspider-result-${targetId}`);
    const resultsContent = resultsArea.querySelector('.results-content');
    
    let resultHtml = results.map(result => `
        <div class="result-item">
            <div class="result-header">
                <span>掃描時間: ${result.created_at}</span>
                <span>狀態: ${result.status}</span>
            </div>
            <div class="result-stats">
                <span>總 URL 數: ${result.total_urls}</span>
                <span>唯一參數數: ${result.unique_parameters}</span>
            </div>
            <div class="result-text">
                <pre>${result.result_text}</pre>
            </div>
            <button onclick="copyToClipboard(this.previousElementSibling.textContent)" class="copy-button">
                複製結果
            </button>
        </div>
    `).join('');
    
    resultsContent.innerHTML = resultHtml;
}

async function showLatestResult(targetId) {
    try {
        console.log('Fetching latest result for target:', targetId); // 添加调试日志
        const response = await fetch(`/api/paramspider/latest/${targetId}`);
        if (!response.ok) {
            throw new Error('獲取結果失敗');
        }
        const result = await response.json();
        console.log('Latest result:', result); // 添加调试日志
        
        if (result.status === 'success' && result.data) {
            displayResult(result.data);
        } else {
            console.error('Invalid result format:', result); // 添加调试日志
            updateStatus(result.message || '獲取結果失敗', true);
        }
    } catch (error) {
        console.error('Error fetching latest result:', error); // 添加调试日志
        updateStatus(error.message, true);
    }
}

async function showAllResults(targetId) {
    try {
        const response = await fetch(`/api/paramspider/all/${targetId}`);
        if (!response.ok) {
            throw new Error('獲取結果失敗');
        }
        const result = await response.json();
        if (result.status === 'success') {
            displayAllResults(result.data);
        } else {
            updateStatus(result.message || '獲取結果失敗', true);
        }
    } catch (error) {
        updateStatus(error.message, true);
    }
}

function copyResultText(elementId) {
    const resultElement = document.getElementById(elementId);
    if (!resultElement) {
        console.error('Result text element not found');
        return;
    }
    
    const textToCopy = resultElement.textContent;
    if (!textToCopy) {
        console.error('No text to copy');
        return;
    }
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        // 显示成功消息
        const notification = document.createElement('div');
        notification.className = 'copy-notification';
        notification.textContent = '已複製到剪貼板';
        document.body.appendChild(notification);
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text:', err);
        updateStatus('複製失敗', true);
    });
}

// 添加事件監聽器
document.addEventListener('DOMContentLoaded', function() {
    const paramSpiderButton = document.querySelector('#paramSpiderButton');
    if (paramSpiderButton) {
        // 确保初始状态下结果区域存在
        ensureScanResultsArea();
        
        paramSpiderButton.addEventListener('click', async function() {
            if (isParamSpiderScanning) {
                return;
            }
            
            const targetId = this.dataset.targetId;
            const userId = this.dataset.userId;
            
            isParamSpiderScanning = true;
            updateStatus('正在執行 ParamSpider 掃描...', false);  // 显示正在扫描的状态
            console.log('Starting scan for target:', targetId); // 添加调试日志
            
            try {
                const response = await fetch(`/user/${userId}/paramspider/${targetId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        exclude: '',
                        threads: 50
                    })
                });
                
                if (!response.ok) {
                    throw new Error('掃描請求失敗');
                }
                
                const result = await response.json();
                console.log('Scan result:', result); // 添加调试日志
                
                if (result.status === 'success') {
                    updateStatus('掃描完成', false);
                    // 直接显示扫描结果
                    const displayData = {
                        result_text: result.result ? result.result.result_text : '未找到結果文本',
                        total_urls: result.result ? result.result.total_urls : 0,
                        unique_parameters: result.result ? result.result.unique_parameters : 0,
                        status: 'completed',
                        created_at: new Date().toLocaleString()
                    };
                    console.log('Display data:', displayData); // 添加调试日志
                    displayResult(displayData);
                    
                    // 延迟一秒后获取最新结果
                    setTimeout(() => {
                        showLatestResult(targetId);
                    }, 1000);
                } else {
                    throw new Error(result.message || '掃描失敗');
                }
            } catch (error) {
                console.error('Scan error:', error); // 添加调试日志
                updateStatus(error.message, true);
            } finally {
                isParamSpiderScanning = false;
            }
        });
    } else {
        console.error('ParamSpider button not found'); // 添加调试日志
    }
});

function formatParamSpiderResults(result) {
    if (!result || !result.total_urls === 0) {
        return '<div class="alert alert-warning">未發現任何參數</div>';
    }

    const { result_text, total_urls, unique_parameters } = result;

    let html = `
        <div class="paramspider-results">
            <div class="result-header">
                <h3>ParamSpider 掃描結果</h3>
                <div class="result-info">
                    <p><strong>總 URL 數:</strong> ${total_urls}</p>
                    <p><strong>唯一參數數:</strong> ${unique_parameters}</p>
                </div>
            </div>
            <div class="result-content">
                <pre class="result-text">${result_text}</pre>
            </div>
            <div class="result-actions">
                <button onclick="copyToClipboard(this.parentElement.previousElementSibling.textContent)" class="copy-button">
                    複製結果
                </button>
            </div>
        </div>
    `;

    return html;
}

function filterParameters(searchText) {
    const items = document.querySelectorAll('.parameter-item');
    const searchLower = searchText.toLowerCase();
    
    items.forEach(item => {
        const url = item.dataset.url.toLowerCase();
        const shouldShow = url.includes(searchLower);
        item.style.display = shouldShow ? 'block' : 'none';
    });
}

// 修改下载功能
async function downloadParamSpiderResult(targetId, crawlerId) {
    try {
        console.log('Downloading result for crawler:', crawlerId);
        const userId = document.querySelector('#paramSpiderButton')?.dataset?.userId;
        if (!userId) {
            throw new Error('找不到用戶ID');
        }
        
        const response = await fetch(`/user/${userId}/paramspider/${targetId}/download/${crawlerId}`);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || '下載失敗');
        }
        
        // 获取文件名
        const contentDisposition = response.headers.get('content-disposition');
        let filename = `paramspider_result_${crawlerId}.txt`;
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        // 创建下载链接
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // 显示成功消息
        const notification = document.createElement('div');
        notification.className = 'copy-notification';
        notification.textContent = '下載成功';
        document.body.appendChild(notification);
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 2000);
        
    } catch (error) {
        console.error('Download error:', error);
        updateStatus(error.message, true);
    }
} 

