# CIT/CQT 模拟审讯系统

法律心理学 Murder Case Simulation 课程专用系统  
NYU Shanghai • Fall 2026 • Professor Pekka Santtila

## 系统概述

本系统为 Legal Psychology 课程提供在线 CIT（隐藏信息测试）和 CQT（比较问题测试）模拟审讯功能。控方可访谈嫌疑人并设计 CIT 问题组，辩方可使用 CQT 格式进行测试。系统集成 ElevenLabs 语音转文字和 DeepSeek AI 分析引擎，实时模拟皮电反应（GSR）波形。

## 功能

- **双系统登录**：控方（CIT）和辩方（CQT）各自密码进入
- **多角色访谈**：可分别审讯嫌疑人 A、嫌疑人 B、儿童目击者、成人目击者
- **语音录制**：浏览器内录音，真实提问
- **ElevenLabs 转录**：自动将语音转为文字
- **DeepSeek 分析**：根据文档定义的已泄露/机密信息库，分析问题并生成响应
- **实时 GSR 波形**：从右到左滚动的皮电反应图，含基线噪音和响应峰值
- **CIT 模式**：根据问题是否触及机密/泄露信息，模拟有罪/无辜嫌疑人的差异化反应
- **CQT 模式**：按照相关/比较/无关问题分类，计算 R/C 比值并判断欺骗信号
- **会话保存**：JSON/CSV 导出所有问题和 GSR 数据

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

设置环境变量或在 `config.py` 中直接填写：

```bash
# Windows PowerShell
$env:ELEVENLABS_API_KEY = "your_elevenlabs_key"
$env:DEEPSEEK_API_KEY = "your_deepseek_key"

# macOS / Linux
export ELEVENLABS_API_KEY="your_elevenlabs_key"
export DEEPSEEK_API_KEY="your_deepseek_key"
```

> **可选**：如果不配置 API 密钥，系统会使用基于关键词匹配的本地后备分析器运行。转录内容将显示占位文本。

### 3. 启动系统

```bash
python app.py
```

访问 http://localhost:5000

### 4. 默认登录密码

| 团队 | 密码 |
|------|------|
| 控方（Prosecution - CIT） | `cit2026` |
| 辩方（Defence - CQT） | `cqt2026` |

## 项目结构

```
CIT-CQT-System/
├── app.py                  # Flask 主应用
├── config.py               # 配置、密码、泄露/机密数据库
├── analysis_engine.py      # DeepSeek 集成 + GSR 波形生成
├── requirements.txt        # Python 依赖
├── static/
│   └── css/
│       └── style.css       # 暗色主题 UI 样式
├── templates/
│   ├── login.html          # 登录页面
│   ├── dashboard.html      # 角色选择页面
│   ├── interview.html      # 访谈 + GSR 波形主界面
│   └── results.html        # 提问记录和导出页面
└── data/
    └── sessions/           # 保存的会话数据（JSON）
```

## 已泄露 vs 机密信息（分析引擎基准）

| 类别 | 内容 | GSR 预期 |
|------|------|---------|
| **已泄露** | 武器类型（厨房刀）、建筑位置、受害者身份、大致死亡时间、性侵犯要素 | 中等反应（双方都可能） |
| **机密** | 具体伤口数量、确切体位、现场缺失物品、具体楼梯间位置、伤口形态 | 高反应（仅有罪嫌疑人） |

## 技术栈

- **后端**: Python Flask
- **前端**: HTML5 Canvas + Vanilla JS
- **语音**: ElevenLabs STT API
- **分析**: DeepSeek Chat API (OpenAI 兼容)
- **版本**: v1.0 • Fall 2026
