# AI 面试模拟 Agent

基于 ReAct 范式的智能面试官，上传简历和 JD 即可开始一场逼真的多轮模拟面试，自动适配技术岗和非技术岗。

## 功能

- **ReAct 自适应面试** — AI 面试官根据每轮回答表现动态调整后续题目方向和深度，不是题库抽题
- **角色自适应** — 自动识别技术岗/非技术岗（产品、设计、运营等），切换完全不同的题型策略和知识领域
- **四类题型切换** — 项目深挖、领域基础、代码手撕（技术岗）/ 案例分析（非技术岗），模拟真实面试节奏
- **严格限一题手撕** — 技术岗整场恰好一道 LeetCode 算法题，选题来自内置的 12 个经典题型池；非技术岗以案例分析替代
- **深度分层** — 基础摸底 → 深入追问 → 压力测试，连续答好自动升深度，连续答不上自动降
- **量化复盘报告** — 面试结束生成完整报告：综合评分、能力维度雷达图、逐题差距分析、思维框架建议、理想回答示例、推荐学习资源
- **改进计划** — 按优先级给出具体行动项，包含时间框架估计
- **面经搜索** — 自动搜索目标企业/岗位的过往面经作为出题参考（DuckDuckGo，免费免 API Key），搜索失败静默降级不影响面试
- **语音输入** — 点击麦克风开始录音，再次点击停止并识别为文字（浏览器 SpeechRecognition）
- **语音输出** — 面试官问题自动朗读，支持静音和语速调节（浏览器 SpeechSynthesis）
- **双配色主题** — 暗黑 / 粉白一键切换，偏好记忆
- **历史记录** — 所有面试自动保存，随时回看复盘报告，支持删除
- **PDF 简历上传** — 支持 PDF / TXT / MD 格式
- **SSE 流式推送** — 评分、出题、报告生成分阶段实时推送，前端显示"正在评分…""正在出题…"等中间状态
- **输入持久化** — 简历和 JD 内容自动保存到 localStorage，刷新不丢失

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI + SSE |
| LLM | DeepSeek API（兼容 OpenAI SDK） |
| 前端 | React + TypeScript + TailwindCSS |
| 图表 | Recharts（雷达图） |
| 语音 | Web Speech API（浏览器原生，零服务端依赖） |
| 存储 | JSON 文件（data/ 目录） |

## 项目结构

```
project4/
├── backend/
│   ├── main.py              # FastAPI 入口 + CLI 模式
│   ├── agent_loop.py        # ReAct 调度引擎 + 状态管理
│   ├── tools.py             # 简历解析 / JD分析 / 出题 / 评分 / 报告生成
│   ├── prompt_templates.py  # 全套面试 Prompt 模板
│   ├── llm_client.py        # DeepSeek API 封装（重试 + JSON 提取）
│   ├── session_store.py     # JSON 文件存储
│   ├── web_search.py        # 面经搜索（DuckDuckGo）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── main.tsx                    # 入口
│       ├── App.tsx                      # 三阶段状态机（配置→面试→报告）
│       ├── ThemeContext.tsx             # 主题 Context + Provider
│       ├── useTheme.ts                 # useTheme hook
│       ├── theme.css                    # CSS 变量（暗黑/粉白双主题）
│       ├── components/
│       │   ├── ConfigPanel.tsx          # 简历/JD输入、PDF上传、历史列表
│       │   ├── InterviewChat.tsx        # 对话流 + SSE 流式推送 + 语音
│       │   ├── ScorePanel.tsx           # 实时评分面板
│       │   ├── ReportView.tsx           # 复盘报告（指标卡 + 雷达图 + 逐题分析）
│       │   ├── HistoryPanel.tsx         # 历史记录列表
│       │   ├── VoiceInput.tsx           # 语音输入按钮
│       │   └── AudioOutput.tsx          # 语音播报控制
│       ├── hooks/
│       │   ├── useSSE.ts               # SSE 流式订阅
│       │   ├── useSpeechRecognition.ts  # 浏览器 STT
│       │   └── useSpeechSynthesis.ts    # 浏览器 TTS
│       └── types.ts
└── data/                              # 面试记录（运行时自动生成）
```

## SSE 流式推送

前端通过 `useSSE` hook 连接 `GET /api/interview/chat`，后端使用 `asyncio.to_thread` 将 LLM 调用放入线程池，同时通过线程安全的 `queue.Queue` 向 SSE 消费者推送事件。前端逐事件更新 UI：

```
POST /answer → 线程池处理:
  evaluating   → 前端显示 "正在评分…"
  evaluated    → 前端显示分数/反馈
  analyzing    → 前端显示 "正在详细分析…"
  generating_question → 前端显示 "正在出题…"
  question     → 前端显示下一题
  generating_report   → 前端显示 "正在生成报告…"
  completed    → 前端跳转报告页
```

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# 或 .venv\Scripts\activate     # Windows CMD

pip install -r backend/requirements.txt

# 前端
cd frontend
npm install
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key
```

### 3. 启动

**终端 1 — 后端：**

```bash
cd backend
python main.py
# 服务运行在 http://localhost:8000
```

**终端 2 — 前端：**

```bash
cd frontend
npm run dev
# 开发服务器运行在 http://localhost:5173
```

### 4. 使用

1. 浏览器打开 `http://localhost:5173`
2. 粘贴简历内容（或上传 PDF），粘贴岗位 JD
3. 设置面试轮数（默认 8 轮）
4. 点击「开始面试」进入面试对话
5. 面试结束自动生成复盘报告
6. 历史记录可在首页底部查看和回看

### CLI 模式

```bash
cd backend
python main.py --cli
```

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/interview/start` | 初始化面试，返回首题 |
| POST | `/api/interview/answer` | 提交回答，返回评分 + 下一题 |
| POST | `/api/interview/end` | 提前结束，返回部分报告 |
| GET | `/api/interview/chat` | SSE 流式推送 |
| GET | `/api/interview/report/{id}` | 获取复盘报告 |
| POST | `/api/parse-resume` | 上传 PDF 简历解析 |
| GET | `/api/history` | 列出所有历史面试 |
| DELETE | `/api/history/{id}` | 删除历史记录 |

## 语音交互

基于浏览器原生 Web Speech API，零额外依赖。

- **语音输入**：使用 Chrome/Edge，点击麦克风按钮开始录音，再次点击停止并自动识别。不支持时自动隐藏按钮，纯键盘输入。
- **语音输出**：面试官问题自动朗读。底部控制栏可开关静音、调节语速（0.75x / 1x / 1.25x）。不支持时静默，仅文本显示。

## License

MIT
