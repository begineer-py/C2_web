// Nmap 扫描状态
let isNmapScanning = false;

document.addEventListener('DOMContentLoaded', function() {
    // 移除所有已存在的事件监听器
    function removeAllEventListeners(element) {
        const clone = element.cloneNode(true);
        element.parentNode.replaceChild(clone, element);
        return clone;
    }

    // Nmap 扫描按钮事件处理
    const nmapButton = document.getElementById('nmapButton');
    if (nmapButton) {
        const newNmapButton = removeAllEventListeners(nmapButton);
        
        newNmapButton.addEventListener('click', async function(event) {
            event.preventDefault();
            
            const targetId = this.dataset.targetId;
            if (!targetId) {
                console.error('未找到目标ID');
                return;
            }

            const statusDiv = document.getElementById('nmap-status');
            const resultsDiv = document.getElementById(`nmap-result-${targetId}`);
            
            if (isNmapScanning) {
                alert('已有一个 Nmap 扫描正在进行中，请等待当前扫描完成。');
                return;
            }

            try {
                isNmapScanning = true;
                this.disabled = true;
                
                statusDiv.textContent = '扫描中，预计需要3-5分钟...';
                statusDiv.style.color = '#ff9800';

                const userId = this.dataset.userId;
                if (!userId) {
                    throw new Error('缺少用户ID');
                }

                const response = await fetch(`/user/${userId}/nmap/${targetId}`, {
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
                resultsDiv.innerHTML = formatNmapResults(data);
                
            } catch (error) {
                console.error('Nmap 扫描错误:', error);
                statusDiv.textContent = `扫描失败: ${error.message}`;
                statusDiv.style.color = '#f44336';

                resultsDiv.innerHTML = `
                    <div class="error-message">
                        <h4>扫描失败</h4>
                        <p>${error.message}</p>
                        <p>如果问题持续存在，请稍后重试或联系管理员</p>
                    </div>`;
            } finally {
                isNmapScanning = false;
                this.disabled = false;
            }
        });
    }
});

function formatNmapResults(data) {
    if (!data || !data.result) {
        return '<div class="alert alert-warning">未发现任何端口信息</div>';
    }

    const result = data.result;
    let html = `
        <div class="nmap-results">
            <div class="result-header">
                <h3>Nmap 扫描结果</h3>
                <div class="result-info">
                    <p><strong>目标主机:</strong> ${result.host || '未知'}</p>
                    <p><strong>主机名:</strong> ${result.hostname || '未知'}</p>
                    <p><strong>状态:</strong> ${result.state || '未知'}</p>
                    <p><strong>扫描时间:</strong> ${result.scan_time || '未知'}</p>
                </div>
            </div>
    `;

    if (result.ports && Object.keys(result.ports).length > 0) {
        const portStats = {
            open: 0,
            filtered: 0,
            closed: 0
        };

        Object.values(result.ports).forEach(port => {
            portStats[port.state]++;
        });

        html += `
            <div class="port-statistics">
                <h4>端口统计</h4>
                <ul>
                    <li>开放端口: ${portStats.open}</li>
                    <li>过滤端口: ${portStats.filtered}</li>
                    <li>关闭端口: ${portStats.closed}</li>
                </ul>
            </div>
            <div class="port-details">
                <h4>端口详情</h4>
                <table class="port-table">
                    <thead>
                        <tr>
                            <th>端口</th>
                            <th>状态</th>
                            <th>服务</th>
                            <th>产品</th>
                            <th>版本</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        const sortedPorts = Object.entries(result.ports)
            .sort((a, b) => parseInt(a[0]) - parseInt(b[0]));

        sortedPorts.forEach(([portNumber, portInfo]) => {
            const stateClass = portInfo.state;
            html += `
                <tr class="${stateClass}">
                    <td>${portNumber}</td>
                    <td>${portInfo.state}</td>
                    <td>${portInfo.name || '未知'}</td>
                    <td>${portInfo.product || '未知'}</td>
                    <td>${portInfo.version || '未知'}</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;
    } else {
        html += '<div class="no-ports">未发现开放的端口</div>';
    }

    html += '</div>';
    return html;
} 