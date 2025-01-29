# C2 系统设计文档

## 系统架构

### 1. 爬虫模块 (Parmaspider)
- 基于现有的 `crawler` 模型扩展
- 集成 FlareSolverr 用于绕过 Cloudflare 保护
- 使用异步处理提高性能

### 2. FlareSolverr 集成
- 部署 FlareSolverr 服务
- 默认端口：8191
- 提供 RESTful API 接口

### 3. 数据处理流程

#### 3.1 URL 爬取流程
1. Parmaspider 爬取目标网站 URL
2. 将爬取的 URL 存入数据库 (crawler_link 表)
3. 对每个 URL 进行安全扫描

#### 3.2 Cloudflare 绕过流程
1. 检测目标是否有 Cloudflare 保护
2. 如有保护，通过 FlareSolverr 代理请求：
   ```python
   POST http://localhost:8191/v1
   {
       "cmd": "request.get",
       "url": "目标URL",
       "maxTimeout": 60000
   }
   ```
3. 解析返回的 HTML 内容

#### 3.3 数据分析流程
1. 使用 Beautiful Soup 解析页面内容
2. 提取关键信息：
   - 表单数据
   - 图片资源
   - 外部链接
   - 其他资源
3. 将分析结果存入对应数据表

### 4. 数据模型关系
- crawler -> crawler_link: 一对多
- crawler -> crawler_form: 一对多
- crawler -> crawler_image: 一对多
- crawler -> crawler_resource: 一对多

### 5. 安全考虑
- 请求限速防止 IP 被封
- 代理池轮换
- 错误重试机制
- 数据验证和清洗

### 6. 性能优化
- 使用异步请求
- 实现请求队列
- 缓存机制
- 分布式处理支持

## 后续开发计划
1. 实现 FlareSolverr 服务管理接口
2. 开发代理池管理系统
3. 添加结果分析和报告生成功能
4. 优化爬虫性能和稳定性 