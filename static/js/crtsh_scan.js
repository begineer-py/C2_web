// CRT.sh 扫描状态
let isCrtshScanning = false;

document.addEventListener('DOMContentLoaded', function() {
    // 移除所有已存在的事件监听器
    function removeAllEventListeners(element) {
        const clone = element.cloneNode(true);
        element.parentNode.replaceChild(clone, element);
        return clone;
    }

    // 确保扫描结果区域存在
    function ensureScanResultsArea() {
        const targetId = document.querySelector('#crtshButton').dataset.targetId;
        let resultsArea = document.getElementById(`crtsh-result-${targetId}`);
        if (!resultsArea) {
            resultsArea = document.createElement('div');
            resultsArea.id = `crtsh-result-${targetId}`;
            resultsArea.className = 'result-container';
            document.querySelector('.scan-results').appendChild(resultsArea);
        }
        return resultsArea;
    }

    // 确保状态显示区域存在
    function ensureStatusArea() {
        let statusArea = document.getElementById('scanStatusArea');
        if (!statusArea) {
            statusArea = document.createElement('div');
            statusArea.id = 'scanStatusArea';
            statusArea.className = 'scan-status-area';
            const container = document.querySelector('.container');
            container.insertBefore(statusArea, container.firstChild);
        }
        return statusArea;
    }

    // 确保状态显示容器存在
    function ensureStatusDiv() {
        let statusDiv = document.getElementById('scanStatus');
        if (!statusDiv) {
            statusDiv = document.createElement('div');
            statusDiv.id = 'scanStatus';
            statusDiv.className = 'scan-status';
            const statusArea = ensureStatusArea();
            statusArea.appendChild(statusDiv);
        }
        return statusDiv;
    }

    // CRT.sh 扫描按钮事件处理
    const crtshButton = document.getElementById('crtshButton');
    if (crtshButton) {
        const newCrtshButton = removeAllEventListeners(crtshButton);
        
        newCrtshButton.addEventListener('click', async function(event) {
            event.preventDefault();
            
            const targetId = this.dataset.targetId;
            if (!targetId) {
                console.error('未找到目标ID');
                return;
            }

            const statusDiv = ensureStatusDiv();
            
            if (isCrtshScanning) {
                alert('已有一个 CRT.sh 扫描正在进行中，请等待当前扫描完成。');
                return;
            }

            try {
                isCrtshScanning = true;
                this.disabled = true;
                
                statusDiv.textContent = '扫描中，预计需要3-5分钟...';
                statusDiv.style.color = '#ff9800';

                const userId = this.dataset.userId;
                if (!userId) {
                    throw new Error('缺少用户ID');
                }

                const response = await fetch(`/user/${userId}/crtsh/${targetId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.message || '扫描失败');
                }

                statusDiv.textContent = '扫描完成';
                statusDiv.style.color = '#4caf50';
                
                // 显示扫描结果
                const resultsArea = ensureScanResultsArea();
                let crtshResultsDiv = document.getElementById(`crtsh-result-${targetId}`);
                if (!crtshResultsDiv) {
                    crtshResultsDiv = document.createElement('div');
                    crtshResultsDiv.id = `crtsh-result-${targetId}`;
                    crtshResultsDiv.className = 'crtsh-result-container';
                    resultsArea.appendChild(crtshResultsDiv);
                }

                crtshResultsDiv.innerHTML = formatCrtshResults(data);
                
                // 添加事件监听器
                setTimeout(addCrtshEventListeners, 100);
                
            } catch (error) {
                console.error('CRT.sh 扫描错误:', error);
                statusDiv.textContent = `扫描失败: ${error.message}`;
                statusDiv.style.color = '#f44336';

                const resultsArea = ensureScanResultsArea();
                let crtshResultsDiv = document.getElementById(`crtsh-result-${targetId}`);
                if (!crtshResultsDiv) {
                    crtshResultsDiv = document.createElement('div');
                    crtshResultsDiv.id = `crtsh-result-${targetId}`;
                    crtshResultsDiv.className = 'crtsh-result-container';
                    resultsArea.appendChild(crtshResultsDiv);
                }

                crtshResultsDiv.innerHTML = `
                    <div class="error-message">
                        <h4>扫描失败</h4>
                        <p>${error.message}</p>
                        <p>如果问题持续存在，请稍后重试或联系管理员</p>
                    </div>`;
            } finally {
                isCrtshScanning = false;
                this.disabled = false;
            }
        });
    }
});

function formatCrtshResults(data) {
    if (!data || !data.result) {
        return '<div class="alert alert-warning">未发现任何域名</div>';
    }

    const result = data.result;
    let html = `
        <div class="crtsh-results">
            <div class="result-header">
                <h3>CRT.sh 扫描结果</h3>
                <div class="result-info">
                    <p><strong>扫描时间:</strong> ${new Date(result.scan_time * 1000).toLocaleString()}</p>
                    <p><strong>发现域名数量:</strong> ${result.total || 0}</p>
                </div>
            </div>
    `;

    if (result.domains && result.domains.length > 0) {
        html += `
            <div class="domain-search">
                <input type="text" id="domainSearch" placeholder="搜索域名..." class="search-input">
            </div>
            <div class="domain-list">
                <table class="domain-table">
                    <thead>
                        <tr>
                            <th>域名</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        result.domains.forEach(domain => {
            html += `
                <tr>
                    <td class="domain-cell">${domain}</td>
                    <td>
                        <button class="copy-btn" data-domain="${domain}">复制</button>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;
    } else {
        html += '<div class="no-domains">未发现相关域名</div>';
    }

    html += '</div>';
    return html;
}

function addCrtshEventListeners() {
    // 添加搜索功能
    const searchInput = document.getElementById('domainSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('.domain-table tbody tr');
            
            rows.forEach(row => {
                const domain = row.querySelector('.domain-cell').textContent.toLowerCase();
                row.style.display = domain.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // 添加复制功能
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const domain = this.getAttribute('data-domain');
            navigator.clipboard.writeText(domain).then(() => {
                const originalText = this.textContent;
                this.textContent = '已复制';
                this.classList.add('copied');
                
                setTimeout(() => {
                    this.textContent = originalText;
                    this.classList.remove('copied');
                }, 2000);
            });
        });
    });
} 