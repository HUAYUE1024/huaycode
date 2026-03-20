<div align="center">

# HUAYCODE

### Python 代码执行可视化引擎

![Python](https://img.shields.io/badge/Python-3.12+-3776ab?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0+-000000?logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**逐行追踪代码执行 / 可视化内存变化 / 动态演示算法过程**

[功能特性](#功能特性) · [快速开始](#快速开始) · [安全架构](#安全架构) · [部署指南](#部署指南) · [API 文档](#api-文档) · [项目结构](#项目结构)

---

</div>

## 简介

HUAYCODE 是一款 Python 代码执行可视化工具，通过逐行追踪技术，让每一行代码的执行过程都清晰可见。适用于算法学习、代码调试和性能分析。

### 核心亮点

- **逐行执行追踪** - 实时记录每一步的变量状态、内存消耗、调用栈
- **内存分析** - 基于 `tracemalloc` 的精确内存追踪，定位热点代码
- **算法可视化** - 动态柱状图演示排序/搜索算法的执行过程
- **沙箱隔离** - 用户代码在子进程中执行，主进程不受影响
- **一键部署** - Docker + Nginx 生产级部署方案

---

## 功能特性

### 控制台 (`/`)

主仪表盘，提供代码执行的全局视图：

| 功能 | 描述 |
|------|------|
| 代码面板 | 语法高亮、行号显示、当前行高亮、自动滚动 |
| 时间轴 | 拖动滑块跳转到任意执行步骤 |
| 播放控制 | 播放/暂停、单步前进/后退、首尾跳转 |
| 步骤解析 | 智能识别语句类型（赋值、循环、条件等），实时解释 |
| 变量上下文 | 显示所有局部变量，数组类型可视化展示 |
| 调用栈 | 实时显示函数调用层级 |
| 执行统计 | 执行时间、行耗时、当前内存、峰值内存 |
| 断点系统 | 点击行号设置断点，按 B 进入断点模式，N 跳转到下一断点 |

**快捷键：**
```
← / →     单步后退/前进
Space     播放/暂停
Home      跳转到开始
End       跳转到结尾
B         切换断点模式
N         跳转到下一断点
```

### 代码编辑器 (`/editor`)

基于 Ace Editor 的专业代码编辑环境：

- **Python 语法高亮** - One Dark 主题
- **智能补全** - 基础补全、实时补全、代码片段
- **算法库** - 10+ 种内置经典算法，一键加载
- **代码持久化** - 自动保存到 localStorage
- **状态栏** - 光标位置、编码格式、语言模式

**快捷键：**
```
Ctrl + Enter    运行并追踪
Ctrl + Z        撤销
Ctrl + Y        重做
Shift + Alt + F 格式化代码
```

**内置算法：**

| 类别 | 算法 |
|------|------|
| 排序 | 冒泡排序、快速排序、归并排序、选择排序、插入排序、堆排序、希尔排序 |
| 搜索 | 二分查找、线性查找 |
| 递归 | 斐波那契序列 |

### 算法可视化 (`/visualizer`)

将抽象的算法执行过程转化为直观的动态演示：

- **动态柱状图** - 数组元素实时高度变化
- **智能指针** - 索引变量自动映射为彩色指针（i=红、j=琥珀、k=翡翠、mid=紫罗兰）
- **操作推断** - 启发式算法自动识别比较、交换、更新操作
- **热力图模式** - 基于访问频率的蓝→红渐变着色
- **音效反馈** - 不同操作类型触发不同音色（正弦波/方波/三角波）
- **DOM 差量更新** - 高效渲染，复用 DOM 节点
- **实时统计** - 比较次数、交换次数、访问次数

### 内存分析 (`/memory`)

深度分析代码执行过程中的内存消耗：

- **趋势图表** - Chart.js 绘制内存变化曲线
- **采样精度** - 可选 100/500/1000/全部数据点
- **内存热点** - Top 5 内存分配最高的代码行
- **时间热点** - Top 5 执行时间最长的代码行
- **泄漏检测** - 智能判断是否存在潜在内存泄漏

### 执行对比 (`/compare`)

对比两次代码执行的差异：

- **执行历史** - 最近 20 次执行记录
- **差异分析**：
  - 变量终态对比
  - 代码覆盖率对比（独有/公共执行行）
  - 执行路径分析（分叉点、公共前缀）
  - 内存消耗趋势对比

### 源码概览 (`/source`)

全局代码执行覆盖视图：

- **执行次数热力图** - 行号显示执行次数，颜色深度表示频率
- **代码小地图** - Canvas 绘制的文件结构概览
- **一键复制** - 快速复制源代码

### 系统设置 (`/settings`)

- 执行延迟调节（50ms - 3000ms）
- 自动滚动开关
- 动画效果开关
- 最大追踪步数（1K / 5K / 10K / 50K）
- 快捷键速查表
- 一键重置所有设置

---

## 安全架构

所有用户代码都在独立子进程中执行，主进程不受影响。防御分三层：

```
用户请求
  │
  ▼
[L1] 主进程 AST 检查 ── validate_code_safety()
  │  拦截: 危险 import、eval/exec/open 等调用、
  │       __subclasses__ 等 dunder 属性、
  │       字典下标 __builtins__ 访问、
  │       type() 动态类构造
  │
  ▼
[L2] 子进程 validate_code_safety() ── 二次校验
  │
[L3] 子进程 restricted globals ── create_restricted_globals()
  │  仅暴露安全 builtins，阻断 os/sys/subprocess 等
  │
[L4] 子进程 resource limits ── _apply_resource_limits()
     虚拟内存 256MB / CPU 30s / 文件描述符 64
```

**关键设计：**
- `spawn` 子进程：完全独立的解释器，不继承主进程状态
- `sys.settrace` 隔离：追踪钩子只在子进程内生效
- 双重 AST 校验：主进程 + 子进程各校验一次
- OS 级资源限制：`resource.setrlimit` 限制内存和 CPU（Linux/Mac）

---

## 快速开始

### 环境要求

- Python 3.12+
- Flask 3.0+

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd huaycode

# 安装依赖
pip install -r requirements.txt
```

### 使用方式

#### 方式一：装饰器模式

```python
from chronotrace import trace

@trace
def bubble_sort():
    data = [64, 34, 25, 12, 22, 11, 90]
    n = len(data)
    for i in range(n):
        for j in range(0, n-i-1):
            if data[j] > data[j+1]:
                data[j], data[j+1] = data[j+1], data[j]
    return data

bubble_sort()
```

#### 方式二：Web 编辑器

```python
from chronotrace.web.app import start_server
start_server()  # 启动服务，访问 http://127.0.0.1:5000
```

#### 方式三：API 调用

```python
from chronotrace.core import trace_code

code = """
data = [3, 1, 4, 1, 5, 9]
for i in range(len(data)):
    for j in range(len(data) - 1):
        if data[j] > data[j + 1]:
            data[j], data[j + 1] = data[j + 1], data[j]
"""

result = trace_code(code)
# result: { success, steps, source, trace, output, hotspots, ... }
```

---

## 部署指南

### 一键部署（推荐）

#### Linux / Mac

```bash
chmod +x deploy.sh
./deploy.sh
```

#### Windows

```cmd
deploy.bat
```

部署脚本会自动：
1. 检查并安装 Docker、Docker Compose
2. 询问服务器 IP、SSH 端口、用户名
3. 上传项目文件到服务器
4. 构建 Docker 镜像并启动服务
5. 可选配置 SSL/HTTPS

### 手动 Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 部署架构

```
用户浏览器 ──> Nginx (反向代理) ──> HUAYCODE (Flask)
              :80/443              :5000
```

**Nginx 特性：**
- Gzip 压缩
- 静态资源缓存（24h）
- 安全响应头
- 代码执行超时 120s
- 健康检查

---

## API 文档

### 系统接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/status` | GET | 系统状态（版本、环境、分支） |
| `/api/v1/trace` | GET | 当前追踪数据 |
| `/api/v1/history` | GET | 执行历史列表（最多 20 条） |
| `/api/v1/history/<id>` | GET | 指定历史记录详情 |

### 执行接口

#### `POST /api/v1/run`

执行 Python 代码并返回追踪数据。代码在沙箱子进程中执行。

**请求体：**
```json
{
  "code": "print('Hello, HUAYCODE!')"
}
```

**限制：** 代码长度最大 50,000 字符，执行超时 30 秒

**响应：**
```json
{
  "success": true,
  "steps": 42,
  "source": ["line1", "line2", "..."],
  "start_line": 1,
  "trace": [
    {
      "timestamp": 1710000000.123,
      "line_no": 3,
      "locals": {"data": [3, 1, 4], "i": 0},
      "memory": 102400,
      "memory_delta": 1024,
      "peak_memory": 204800,
      "event": "line",
      "stmt_type": "For",
      "stmt_source": "for i in range(len(data)):",
      "call_stack": ["<module>"],
      "exec_time_delta": 0.000012,
      "elapsed_time": 0.001234
    }
  ],
  "output": [{"timestamp": 0.001, "content": "Hello"}],
  "hotspots": [[15, 800000], [23, 400000]],
  "time_hotspots": [[8, 0.05], [12, 0.03]],
  "total_exec_time": 0.123
}
```

#### `POST /api/v1/compare`

对比两次执行结果。

**请求体：**
```json
{
  "id_a": 1,
  "id_b": 2
}
```

**响应：**
```json
{
  "source_changed": false,
  "diff": {
    "steps_diff": 5,
    "memory_diff": {
      "peak_a": 102400,
      "peak_b": 153600,
      "peak_delta": 51200
    },
    "line_coverage": {
      "only_in_a": [5, 8],
      "only_in_b": [12],
      "common": [1, 2, 3, 4, 6, 7, 9, 10, 11]
    },
    "variable_changes": [
      {
        "name": "result",
        "value_a": [1, 2, 3],
        "value_b": [3, 2, 1]
      }
    ],
    "execution_path_diff": {
      "common_prefix_len": 15,
      "divergence_points": [{"step": 16, "line_a": 8, "line_b": 10}],
      "unique_lines_a": [8, 9],
      "unique_lines_b": [10, 11, 12]
    }
  }
}
```

### 响应头

所有 API 响应包含安全头：
```
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 项目结构

```
HUAYCODE/
├── chronotrace/                    # 核心 Python 包
│   ├── __init__.py                 # 包初始化，导出 trace 装饰器
│   ├── core.py                     # 追踪引擎（sys.settrace + tracemalloc）
│   ├── sandbox.py                  # 沙箱隔离、安全校验、子进程执行
│   ├── examples/
│   │   └── bubble_sort.py          # 冒泡排序示例
│   └── web/                        # Web 应用
│       ├── app.py                  # Flask 服务器 + API 路由
│       ├── static/
│       │   ├── css/
│       │   ├── lib/
│       │   ├── fonts/
│       │   ├── script.js
│       │   ├── onboarding.js
│       │   ├── style.css
│       │   └── favicon.svg
│       └── templates/
│           ├── index.html
│           ├── editor.html
│           ├── visualizer.html
│           ├── source.html
│           ├── memory.html
│           ├── compare.html
│           └── settings.html
├── examples/
│   └── demo.py                     # QuickSort 演示
├── tests/
│   └── test_core.py                # 单元测试
├── nginx/                          # Nginx 配置
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
├── deploy.bat
├── requirements.txt
├── test_run.py
└── test_script.py
```

---

## 配置说明

### 客户端配置（localStorage）

| 配置项 | Key | 默认值 | 范围 |
|--------|-----|--------|------|
| 执行延迟 | `huay_speed` | 1000ms | 50 - 3000ms |
| 自动滚动 | `huay_autoscroll` | true | true/false |
| 动画效果 | `huay_anim` | true | true/false |
| 最大步数 | `huay_maxsteps` | 5000 | 1000/5000/10000/50000 |

### 服务端配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 调试模式 | `FLASK_DEBUG` | false | 启用 Flask 调试 |
| 服务端口 | - | 5000 | Flask 监听端口 |
| 代码长度 | - | 50000 | 最大代码字符数 |
| 历史记录 | - | 20 | 最大执行历史数 |
| 序列化深度 | - | 2 | 对象序列化层级 |
| 列表截断 | - | 50 | 序列化最大元素数 |
| 执行超时 | - | 30s | 子进程最大执行时间 |
| 内存限制 | - | 256MB | 子进程虚拟内存上限 |

### Docker 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NGINX_PORT` | 80 | Nginx 对外端口 |
| `NGINX_SSL_PORT` | 443 | SSL 端口 |
| `FLASK_ENV` | production | Flask 运行环境 |
| `TZ` | Asia/Shanghai | 时区设置 |

---

## 技术实现

### 后端架构

```
Flask Server
  路由层 (views) -> API层 (api) -> 追踪层 (trace) -> 存储层 (memory)
                                      |
                         sys.settrace + tracemalloc
                                      |
                            子进程沙箱隔离 (spawn)
```

**核心技术：**
- `sys.settrace` - Python 解释器级逐行追踪
- `tracemalloc` - 内存分配追踪
- `ast` - 抽象语法树分析，识别语句类型
- `gc` - 垃圾回收统计
- `multiprocessing` - 子进程隔离执行
- `resource` - OS 级资源限制

### 前端架构

```
Browser
  DOM层 (HTML) <- 状态层 (State) -> 渲染层 (Canvas) -> 音频层 (Audio)
       |              |                  |
  Ace Editor    DOM Diffing       Web Audio API
```

**核心技术：**
- DOM 差量更新 - 高效渲染，避免全量重建
- Web Audio API - 实时音效合成
- localStorage - 客户端状态持久化
- CSS3 硬件加速 - GPU 加速动画

---

## 测试

```bash
# 运行单元测试
python -m pytest tests/

# 运行 API 测试（需先启动服务器）
python test_run.py

# 运行装饰器测试
python test_script.py
```

---

## 已知限制

| 限制 | 说明 |
|------|------|
| 仅支持 Python | 无法追踪其他语言代码 |
| 序列化深度 | 对象序列化最大 2 层嵌套 |
| 列表长度 | 序列化时超过 50 个元素会被截断 |
| 递归追踪 | 深度递归可能导致追踪数据过大 |
| 子进程超时 | 代码执行超过 30 秒会被终止 |
| Windows 资源限制 | `resource.setrlimit` 仅在 Linux/Mac 生效 |

---

## 贡献

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件
