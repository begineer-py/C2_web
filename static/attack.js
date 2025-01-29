document.addEventListener('DOMContentLoaded', function() {
    const scanButton = document.getElementById('scanButton');
    const crtshButton = document.getElementById('crtshButton');
    const webtechButton = document.getElementById('webtechButton');
    const curlButton = document.getElementById('curlButton');
    const scanStatus = document.getElementById('scanStatus');
    const resultContainer = document.getElementById('scanResult');
    const loading = resultContainer.querySelector('.loading');
    const resultContent = resultContainer.querySelector('.result-content');

    function performScan(url, button) {
        // 禁用所有按钮
        scanButton.disabled = true;
        crtshButton.disabled = true;
        webtechButton.disabled = true;
        curlButton.disabled = true;
        button.classList.add('disabled');
        loading.style.display = 'block';
        resultContent.innerHTML = '';
        scanStatus.innerHTML = '<div class="status-message">正在進行掃描，請稍候...</div>';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            return response.json().then(data => {
                if (!response.ok) {
                    throw new Error(data.message || '未知錯誤');
                }
                return data;
            });
        })
        .then(data => {
            loading.style.display = 'none';
            // 启用所有按钮
            scanButton.disabled = false;
            crtshButton.disabled = false;
            webtechButton.disabled = false;
            curlButton.disabled = false;
            button.classList.remove('disabled');

            if (data.status === 'success') {
                scanStatus.innerHTML = '<div class="status-success">掃描完成！</div>';
                // 将扫描结果中的换行符转换为 HTML 换行
                const formattedResult = data.result.replace(/\n/g, '<br>');
                resultContent.innerHTML = `<div class="scan-result-text">${formattedResult}</div>`;
            } else {
                scanStatus.innerHTML = `<div class="status-error">掃描失敗: ${data.message}</div>`;
            }
        })
        .catch(error => {
            loading.style.display = 'none';
            // 启用所有按钮
            scanButton.disabled = false;
            crtshButton.disabled = false;
            webtechButton.disabled = false;
            curlButton.disabled = false;
            button.classList.remove('disabled');
            scanStatus.innerHTML = `<div class="status-error">錯誤: ${error.message}</div>`;
            console.error('Error:', error);
        });
    }

    scanButton.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target-id');
        const userId = this.getAttribute('data-user-id');
        performScan(`/user/${userId}/nmap/${targetId}`, this);
    });

    crtshButton.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target-id');
        const userId = this.getAttribute('data-user-id');
        performScan(`/user/${userId}/crtsh/${targetId}`, this);
    });

    webtechButton.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target-id');
        const userId = this.getAttribute('data-user-id');
        performScan(`/user/${userId}/webtech/${targetId}`, this);
    });

    curlButton.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target-id');
        const userId = this.getAttribute('data-user-id');
        performScan(`/user/${userId}/curl/${targetId}`, this);
    });

    function formatCurlResults(data) {
        if (!data || !data.result) return '無掃描結果';
        
        const result = data.result;
        let html = '<div class="scan-results-container">';
        
        // 顯示爬蟲結果
        if (result.crawler_results) {
            html += '<div class="crawler-results">';
            html += '<h4>爬蟲結果</h4>';
            
            const crawlerData = result.crawler_results.data;
            if (crawlerData) {
                // 顯示統計信息
                html += '<div class="crawler-stats">';
                html += `<p>總共爬取頁面數: ${crawlerData.total_pages}</p>`;
                html += `<p>發現表單數量: ${crawlerData.total_forms}</p>`;
                html += `<p>發現鏈接數量: ${crawlerData.total_links}</p>`;
                html += `<p>發現資源數量: ${crawlerData.total_resources}</p>`;
                html += '</div>';

                // 顯示表單詳細信息
                if (crawlerData.forms && crawlerData.forms.length > 0) {
                    html += '<div class="forms-section">';
                    html += '<h5>發現的表單</h5>';
                    crawlerData.forms.forEach((form, index) => {
                        html += `<div class="form-item">`;
                        html += `<h6>表單 ${index + 1}</h6>`;
                        html += `<p>URL: ${form.url}</p>`;
                        html += `<p>方法: ${form.method}</p>`;
                        html += `<p>提交地址: ${form.action}</p>`;
                        
                        if (form.inputs && form.inputs.length > 0) {
                            html += '<div class="form-inputs">';
                            html += '<p>輸入欄位:</p>';
                            html += '<ul>';
                            form.inputs.forEach(input => {
                                html += `<li>類型: ${input.type}, 名稱: ${input.name}, 必填: ${input.required ? '是' : '否'}</li>`;
                            });
                            html += '</ul>';
                            html += '</div>';
                        }
                        html += '</div>';
                    });
                    html += '</div>';
                }

                // 顯示鏈接信息
                if (crawlerData.links && crawlerData.links.length > 0) {
                    html += '<div class="links-section">';
                    html += '<h5>發現的鏈接</h5>';
                    html += '<ul>';
                    crawlerData.links.forEach(link => {
                        html += `<li><a href="${link}" target="_blank">${link}</a></li>`;
                    });
                    html += '</ul>';
                    html += '</div>';
                }

                // 顯示資源信息
                if (crawlerData.resources && crawlerData.resources.length > 0) {
                    html += '<div class="resources-section">';
                    html += '<h5>發現的資源</h5>';
                    html += '<ul>';
                    crawlerData.resources.forEach(resource => {
                        html += `<li>類型: ${resource.type}, URL: ${resource.url}</li>`;
                    });
                    html += '</ul>';
                    html += '</div>';
                }
            }
            
            html += '</div>';
        }

        // 顯示安全檢查結果
        if (result.security_results && result.security_results.length > 0) {
            html += '<div class="security-results">';
            html += '<h4>安全檢查結果</h4>';
            html += '<ul class="security-issues">';
            result.security_results.forEach(issue => {
                html += `<li class="security-issue">${issue}</li>`;
            });
            html += '</ul>';
            html += '</div>';
        }

        // 顯示響應頭信息
        if (result.headers) {
            html += '<div class="headers-info">';
            html += '<h4>響應頭信息</h4>';
            html += '<table class="headers-table">';
            html += '<tr><th>Header</th><th>Value</th></tr>';
            Object.entries(result.headers).forEach(([key, value]) => {
                html += `<tr><td>${key}</td><td>${value}</td></tr>`;
            });
            html += '</table>';
            html += '</div>';
        }

        html += '</div>';
        return html;
    }
});