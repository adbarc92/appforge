# DevTeam.AI Setup Instructions for Claude Code

## Overview
You are setting up a full-stack autonomous AI development team system with:
- **Backend**: Python FastAPI + LangGraph + Socket.IO + Redis
- **Frontend**: React + TypeScript + Vite + React Flow + Zustand + Tailwind
- **Infrastructure**: Docker Compose

## Project Structure to Create

```
devteam-ai/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── mock_agent.py
│   │   └── registry.py
│   ├── orchestrator/
│   ├── api/
│   ├── prompts/
│   │   └── v1/
│   ├── tools/
│   ├── tests/
│   ├── config.py
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── .env
├── ui/
│   ├── src/
│   │   ├── components/
│   │   │   ├── GraphCanvas.tsx
│   │   │   ├── AgentNode.tsx
│   │   │   └── ChatInterface.tsx
│   │   ├── stores/
│   │   │   └── projectStore.ts
│   │   ├── hooks/
│   │   │   └── useSocket.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── Dockerfile
├── docs/
├── tests/
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Step-by-Step Instructions

### 1. Initialize Project Root

Create the root directory and initialize git:

```bash
mkdir devteam-ai && cd devteam-ai
git init
```

Create `.gitignore`:
```
__pycache__/
*.py[cod]
venv/
.env
*.db
node_modules/
dist/
.DS_Store
.vscode/
.idea/
*.log
logs/
```

### 2. Backend Setup

#### 2.1 Create Backend Directory Structure
```bash
mkdir -p backend/{agents,orchestrator,api,prompts/v1,tools,tests}
cd backend
```

#### 2.2 Create `requirements.txt`
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-socketio==5.11.0
langgraph==0.0.20
langchain==0.1.0
langchain-openai==0.0.5
crewai==0.1.26
redis==5.0.1
pydantic==2.5.3
python-dotenv==1.0.0
pytest==7.4.4
pytest-asyncio==0.23.3
structlog==24.1.0
httpx==0.26.0
```

#### 2.3 Create `config.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ENV = os.getenv('ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    MOCK_AGENTS = os.getenv('MOCK_AGENTS', 'true').lower() == 'true'
    SLOW_MODE = os.getenv('SLOW_MODE', 'false').lower() == 'true'
    FORCE_ERRORS = os.getenv('FORCE_ERRORS', 'false').lower() == 'true'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    BUDGET_LIMIT = float(os.getenv('BUDGET_LIMIT', '200.0'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

config = Config()
```

#### 2.4 Create Agent Files

**`agents/__init__.py`:**
```python
from .base_agent import InstrumentedAgent
from .mock_agent import MockAgent
from .registry import AGENT_REGISTRY, create_agent

__all__ = ['InstrumentedAgent', 'MockAgent', 'AGENT_REGISTRY', 'create_agent']
```

**`agents/base_agent.py`:**
```python
from typing import Callable, Any, Dict
import structlog

logger = structlog.get_logger()

class InstrumentedAgent:
    """Base agent with event emission for UI updates"""

    def __init__(self, name: str, emit_callback: Callable):
        self.name = name
        self.emit = emit_callback
        self.logger = logger.bind(agent=name)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses"""
        raise NotImplementedError

    async def _emit_status(self, status: str, **kwargs):
        """Helper to emit status updates"""
        await self.emit('agent_status', {
            'agent': self.name,
            'status': status,
            **kwargs
        })
```

**`agents/mock_agent.py`:**
```python
import asyncio
import random
from typing import Dict, Any
from .base_agent import InstrumentedAgent

class MockAgent(InstrumentedAgent):
    """Configurable mock agent for testing"""

    def __init__(self, name: str, emit_callback, config: Dict[str, Any] = None):
        super().__init__(name, emit_callback)
        self.config = config or {
            'delay': 2.0,
            'success_rate': 1.0,
            'output': {'status': 'success', 'artifact': 'mock_data'}
        }

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("agent.started", task=task)

        await self._emit_status('running', task=task)
        await asyncio.sleep(self.config['delay'])

        if random.random() > self.config['success_rate']:
            self.logger.error("agent.failed")
            await self._emit_status('error', error='Simulated failure')
            return {'status': 'error', 'error': 'Simulated failure'}

        self.logger.info("agent.completed")
        await self._emit_status('complete')
        return self.config['output']
```

**`agents/registry.py`:**
```python
from typing import Dict, Any, Callable
from .mock_agent import MockAgent
from config import config

AGENT_CONFIGS = {
    'clarifying_pm': {'delay': 3.0, 'success_rate': 1.0},
    'product_owner': {'delay': 2.0, 'success_rate': 1.0},
    'solution_architect': {'delay': 5.0, 'success_rate': 0.95},
    'tech_lead': {'delay': 4.0, 'success_rate': 1.0},
    'frontend': {'delay': 6.0, 'success_rate': 0.9},
    'backend': {'delay': 6.0, 'success_rate': 0.9},
    'database': {'delay': 4.0, 'success_rate': 0.95},
    'ai_ml': {'delay': 7.0, 'success_rate': 0.85},
    'devops': {'delay': 5.0, 'success_rate': 0.9},
    'security': {'delay': 4.0, 'success_rate': 1.0},
    'uiux_designer': {'delay': 5.0, 'success_rate': 1.0},
    'qa': {'delay': 4.0, 'success_rate': 1.0},
    'technical_writer': {'delay': 3.0, 'success_rate': 1.0},
    'orchestrator': {'delay': 1.0, 'success_rate': 1.0},
    'delivery_summarizer': {'delay': 2.0, 'success_rate': 1.0},
}

AGENT_REGISTRY = {
    name: {'class': MockAgent, 'config': cfg}
    for name, cfg in AGENT_CONFIGS.items()
}

def create_agent(name: str, emit_callback: Callable) -> Any:
    """Factory function to create agents"""
    if name not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent: {name}")

    agent_info = AGENT_REGISTRY[name]
    AgentClass = agent_info['class']
    agent_config = agent_info['config']

    return AgentClass(name, emit_callback, agent_config)
```

#### 2.5 Create `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import asyncio
from config import config
from agents import create_agent
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

app = FastAPI(title="DevTeam.AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:6006"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['http://localhost:5173', 'http://localhost:6006'],
    logger=True,
    engineio_logger=True
)

socket_app = socketio.ASGIApp(sio, app)

projects = {}

@app.get("/")
async def root():
    return {"message": "DevTeam.AI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": "mock" if config.MOCK_AGENTS else "real",
        "agents": len(list(projects.keys()))
    }

@sio.event
async def connect(sid, environ):
    logger.info("client.connected", sid=sid)
    await sio.emit('connected', {'sid': sid}, room=sid)

@sio.event
async def disconnect(sid):
    logger.info("client.disconnected", sid=sid)

@sio.event
async def start_project(sid, data):
    """Start a new project workflow"""
    logger.info("project.start", sid=sid, data=data)
    project_id = data.get('project_id', f'project_{sid}')

    projects[project_id] = {
        'sid': sid,
        'phase': 0,
        'idea': data.get('idea', ''),
        'status': 'running'
    }

    async def emit_callback(event, data):
        await sio.emit(event, data, room=sid)

    asyncio.create_task(run_workflow(project_id, emit_callback))
    await sio.emit('project_started', {'project_id': project_id}, room=sid)

async def run_workflow(project_id: str, emit_callback):
    """Execute the agent workflow"""
    logger.info("workflow.start", project_id=project_id)

    await emit_callback('state_update', {
        'phase': 1,
        'message': 'Starting clarification phase...'
    })

    clarifying_pm = create_agent('clarifying_pm', emit_callback)
    result = await clarifying_pm.execute({
        'task': 'clarify',
        'idea': projects[project_id]['idea']
    })

    await emit_callback('approval_required', {
        'phase': 1,
        'agent': 'clarifying_pm',
        'content': 'Ready to proceed with project?'
    })

    logger.info("workflow.paused_for_approval", project_id=project_id)

@sio.event
async def approve_phase(sid, data):
    """Handle approval"""
    logger.info("approval.received", sid=sid, data=data)
    await sio.emit('approval_accepted', data, room=sid)
    await sio.emit('state_update', {
        'phase': 2,
        'message': 'Proceeding to next phase...'
    })

@sio.event
async def force_agent_run(sid, data):
    """Debug: Force an agent to run"""
    agent_id = data.get('agent_id')
    logger.info("debug.force_agent_run", sid=sid, agent_id=agent_id)

    async def emit_callback(event, data):
        await sio.emit(event, data, room=sid)

    agent = create_agent(agent_id, emit_callback)
    result = await agent.execute({'task': 'debug_run'})

    await sio.emit('agent_forced', {'agent_id': agent_id, 'result': result}, room=sid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000, log_level="info")
```

#### 2.6 Create Backend Docker Files

**`Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**`.env.example` and `.env`:**
```
ENV=development
DEBUG=true
REDIS_URL=redis://redis:6379
MOCK_AGENTS=true
SLOW_MODE=false
FORCE_ERRORS=false
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
BUDGET_LIMIT=200.0
LOG_LEVEL=DEBUG
```

### 3. Frontend Setup

#### 3.1 Create Frontend Directory Structure
```bash
cd ../
mkdir -p ui/src/{components,stores,hooks,types}
cd ui
```

#### 3.2 Create `package.json`
```json
{
  "name": "devteam-ai-ui",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@xyflow/react": "^12.0.0",
    "zustand": "^4.4.7",
    "socket.io-client": "^4.7.4",
    "react-markdown": "^9.0.1",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16"
  }
}
```

#### 3.3 Create Configuration Files

**`vite.config.ts`:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  }
})
```

**`tsconfig.json`:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**`tsconfig.node.json`:**
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

**`tailwind.config.js`:**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**`postcss.config.js`:**
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**`Dockerfile`:**
```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
```

#### 3.4 Create Source Files

**`index.html`:**
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DevTeam.AI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**`src/index.css`:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

**`src/types/index.ts`:**
```typescript
export type AgentStatus = 'idle' | 'running' | 'complete' | 'error'

export interface AgentNode {
  id: string
  name: string
  status: AgentStatus
  phase: number
}

export interface ChatMessage {
  id: string
  sender: 'user' | 'agent' | 'system'
  content: string
  timestamp: number
}

export interface ProjectState {
  id: string
  name: string
  phase: number
  nodes: AgentNode[]
  messages: ChatMessage[]
  pendingApproval: boolean
  budget: {
    spent: number
    limit: number
  }
}
```

**`src/stores/projectStore.ts`:**
```typescript
import { create } from 'zustand'
import type { AgentNode, ChatMessage, ProjectState } from '../types'

const initialNodes: AgentNode[] = [
  { id: 'clarifying_pm', name: 'Clarifying PM', status: 'idle', phase: 3 },
  { id: 'product_owner', name: 'Product Owner', status: 'idle', phase: 3 },
  { id: 'solution_architect', name: 'Solution Architect', status: 'idle', phase: 4 },
  { id: 'tech_lead', name: 'Tech Lead', status: 'idle', phase: 4 },
  { id: 'frontend', name: 'Frontend Engineer', status: 'idle', phase: 6 },
  { id: 'backend', name: 'Backend Engineer', status: 'idle', phase: 6 },
  { id: 'database', name: 'Database Engineer', status: 'idle', phase: 6 },
  { id: 'ai_ml', name: 'AI/ML Engineer', status: 'idle', phase: 6 },
  { id: 'devops', name: 'DevOps Engineer', status: 'idle', phase: 7 },
  { id: 'security', name: 'Security Engineer', status: 'idle', phase: 7 },
  { id: 'uiux_designer', name: 'UI/UX Designer', status: 'idle', phase: 5 },
  { id: 'qa', name: 'QA Engineer', status: 'idle', phase: 7 },
  { id: 'technical_writer', name: 'Technical Writer', status: 'idle', phase: 7 },
  { id: 'orchestrator', name: 'Orchestrator', status: 'idle', phase: 1 },
  { id: 'delivery_summarizer', name: 'Delivery Summarizer', status: 'idle', phase: 10 },
]

interface ProjectStore extends ProjectState {
  updateNodeStatus: (id: string, status: AgentNode['status']) => void
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  setPendingApproval: (pending: boolean) => void
  updateBudget: (spent: number) => void
  reset: () => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  id: 'default',
  name: 'New Project',
  phase: 0,
  nodes: initialNodes,
  messages: [],
  pendingApproval: false,
  budget: {
    spent: 0,
    limit: 200,
  },
  updateNodeStatus: (id, status) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.id === id ? { ...n, status } : n)),
    })),
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: `msg_${Date.now()}`,
          timestamp: Date.now(),
        },
      ],
    })),
  setPendingApproval: (pending) => set({ pendingApproval: pending }),
  updateBudget: (spent) =>
    set((state) => ({
      budget: { ...state.budget, spent },
    })),
  reset: () =>
    set({
      nodes: initialNodes,
      messages: [],
      pendingApproval: false,
      phase: 0,
      budget: { spent: 0, limit: 200 },
    }),
}))
```

**`src/hooks/useSocket.ts`:**
```typescript
import { useEffect, useRef } from 'react'
import { io, Socket } from 'socket.io-client'
import { useProjectStore } from '../stores/projectStore'

const SOCKET_URL = 'http://localhost:8000'

export function useSocket() {
  const socketRef = useRef<Socket | null>(null)
  const updateNodeStatus = useProjectStore((state) => state.updateNodeStatus)
  const addMessage = useProjectStore((state) => state.addMessage)
  const setPendingApproval = useProjectStore((state) => state.setPendingApproval)

  useEffect(() => {
    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket'],
    })

    const socket = socketRef.current

    socket.on('connect', () => {
      console.log('Connected to server')
      addMessage({ sender: 'system', content: 'Connected to DevTeam.AI' })
    })

    socket.on('agent_status', (data) => {
      console.log('Agent status update:', data)
      updateNodeStatus(data.agent, data.status)
      if (data.status === 'running') {
        addMessage({ sender: 'agent', content: `${data.agent} started working...` })
      } else if (data.status === 'complete') {
        addMessage({ sender: 'agent', content: `${data.agent} completed task` })
      }
    })

    socket.on('approval_required', (data) => {
      console.log('Approval required:', data)
      setPendingApproval(true)
      addMessage({
        sender: 'system',
        content: `Phase ${data.phase} approval required: ${data.content}`,
      })
    })

    socket.on('state_update', (data) => {
      console.log('State update:', data)
      if (data.message) {
        addMessage({ sender: 'system', content: data.message })
      }
    })

    return () => {
      socket.disconnect()
    }
  }, [updateNodeStatus, addMessage, setPendingApproval])

  return socketRef.current
}
```

**`src/components/AgentNode.tsx`:**
```typescript
import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { AgentStatus } from '../types'

const statusColors: Record<AgentStatus, string> = {
  idle: 'bg-gray-200 border-gray-400',
  running: 'bg-blue-500 border-blue-700 animate-pulse',
  complete: 'bg-green-500 border-green-700',
  error: 'bg-red-500 border-red-700',
}

interface AgentNodeProps {
  data: {
    name: string
    status: AgentStatus
  }
}

export const AgentNode = memo(({ data }: AgentNodeProps) => {
  return (
    <div
      className={`px-4 py-3 rounded-lg shadow-lg border-2 ${statusColors[data.status]} min-w-[150px]`}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      <div className="text-sm font-semibold text-gray-900">{data.name}</div>
      <div className="text-xs text-gray-700 mt-1 capitalize">{data.status}</div>
      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  )
})

AgentNode.displayName = 'AgentNode'
```

**`src/components/GraphCanvas.tsx`:**
```typescript
import { useCallback } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useProjectStore } from '../stores/projectStore'
import { AgentNode } from './AgentNode'

const nodeTypes = {
  agent: AgentNode,
}

export function GraphCanvas() {
  const projectNodes = useProjectStore((state) => state.nodes)

  const initialNodes: Node[] = projectNodes.map((node, index) => ({
    id: node.id,
    type: 'agent',
    position: {
      x: (index % 5) * 200 + 50,
      y: Math.floor(index / 5) * 150 + 50,
    },
    data: { name: node.name, status: node.status },
  }))

  const initialEdges: Edge[] = []

  const [nodes] = useNodesState(initialNodes)
  const [edges] = useEdgesState(initialEdges)

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}
```

**`src/components/ChatInterface.tsx`:**
```typescript
import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { useProjectStore } from '../stores/projectStore'
import { useSocket } from '../hooks/useSocket'

export function ChatInterface() {
  const [input, setInput] = useState('')
  const messages = useProjectStore((state) => state.messages)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const socket = useSocket()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || !socket) return

    useProjectStore.getState().addMessage({
      sender: 'user',
      content: input,
    })

    socket.emit('user_message', { message: input })
    setInput('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full bg-white border-t">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.sender === 'user'
                  ? 'bg-blue-500 text-white'
                  : msg.sender === 'agent'
                  ? 'bg-gray-200 text-gray-900'
                  : 'bg-yellow-100 text-gray-900'
              }`}
            >
              <div className="text-xs font-semibold mb-1 capitalize opacity-75">
                {msg.sender}
              </div>
