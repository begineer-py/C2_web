// Web 技术扫描状态
let isWebtechScanning = false;

document.addEventListener('DOMContentLoaded', function() {
    // 移除所有已存在的事件监听器
    function removeAllEventListeners(element) {
        const clone = element.cloneNode(true);
        element.parentNode.replaceChild(clone, element);
        return clone;
    }

    // 确保扫描结果区域存在
    function ensureScanResultsArea() {
        const targetId = document.querySelector('#webtechButton').dataset.targetId;
        let resultsArea = document.getElementById(`webtech-result-${targetId}`);
        if (!resultsArea) {
            resultsArea = document.createElement('div');
            resultsArea.id = `webtech-result-${targetId}`;
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

    // Web 技术扫描按钮事件处理
    const webtechButton = document.getElementById('webtechButton');
    if (webtechButton) {
        const newWebtechButton = removeAllEventListeners(webtechButton);
        
        newWebtechButton.addEventListener('click', async function(event) {
            event.preventDefault();
            
            const targetId = this.dataset.targetId;
            if (!targetId) {
                console.error('未找到目标ID');
                return;
            }

            const statusDiv = ensureStatusDiv();
            
            if (isWebtechScanning) {
                alert('已有一个 Web 技术扫描正在进行中，请等待当前扫描完成。');
                return;
            }

            try {
                isWebtechScanning = true;
                this.disabled = true;
                
                statusDiv.textContent = '扫描中，预计需要3-5分钟...';
                statusDiv.style.color = '#ff9800';

                const userId = this.dataset.userId;
                if (!userId) {
                    throw new Error('缺少用户ID');
                }

                const response = await fetch(`/user/${userId}/webtech/${targetId}`, {
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
                resultsArea.innerHTML = formatWebtechResults(data);
                
            } catch (error) {
                console.error('Web 技术扫描错误:', error);
                statusDiv.textContent = `扫描失败: ${error.message}`;
                statusDiv.style.color = '#f44336';

                const resultsArea = ensureScanResultsArea();
                resultsArea.innerHTML = `
                    <div class="error-message">
                        <h4>扫描失败</h4>
                        <p>${error.message}</p>
                        <p>如果问题持续存在，请稍后重试或联系管理员</p>
                    </div>`;
            } finally {
                isWebtechScanning = false;
                this.disabled = false;
            }
        });
    }
});

function formatWebtechResults(data) {
    if (!data || !data.result || !data.result.technologies) {
        return '<div class="alert alert-warning">未发现任何技术信息</div>';
    }

    const result = data.result;
    let html = `
        <div class="webtech-results">
            <div class="result-header">
                <h3>Web 技术扫描结果</h3>
                <div class="result-info">
                    <p><strong>目标网站:</strong> ${result.target_url}</p>
                    <p><strong>扫描时间:</strong> ${result.scan_time}</p>
                </div>
            </div>
    `;

    // 按类别分组技术
    const techByCategory = {};
    result.technologies.forEach(tech => {
        tech.categories.forEach(category => {
            if (!techByCategory[category]) {
                techByCategory[category] = [];
            }
            techByCategory[category].push(tech);
        });
    });

    // 遍历每个类别
    for (const category in techByCategory) {
        html += `
            <div class="tech-category">
                <h4>${category}</h4>
                <table class="tech-table">
                    <thead>
                        <tr>
                            <th>技术名称</th>
                            <th>版本</th>
                            <th>置信度</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        // 添加该类别下的所有技术
        techByCategory[category].forEach(tech => {
            html += `
                <tr>
                    <td>${tech.name}</td>
                    <td>${tech.version || '未知'}</td>
                    <td>${tech.confidence}%</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;
    }

    html += '</div>';
    return html;
} 