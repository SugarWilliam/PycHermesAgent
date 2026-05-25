import React from 'react';

const quickActions = [
  {
    title: '正式分析',
    desc: '使用MetaHarness进行结构化推理',
    text: '请帮我进行正式分析',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="M7 16l4-8 4 4 4-6" />
      </svg>
    ),
  },
  {
    title: '知识检索',
    desc: '从本地知识库查找相关信息',
    text: '请从知识库中检索相关信息',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.35-4.35" />
        <path d="M8 8h6M8 11h4" />
      </svg>
    ),
  },
  {
    title: '写作助手',
    desc: '报告撰写、摘要、翻译',
    text: '请帮我进行写作',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
      </svg>
    ),
  },
  {
    title: '代码审查',
    desc: '逻辑验证、Bug分析、架构评审',
    text: '请帮我进行代码审查',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
        <line x1="14" y1="4" x2="10" y2="20" />
      </svg>
    ),
  },
];

const badges = ['多模型支持', '本地RAG', 'MetaHarness', '8项内置技能'];

export default function WelcomeScreen({ onQuickAction }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12 select-none">
      {/* Logo + branding */}
      <div className="flex flex-col items-center mb-8">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
          <defs>
            <linearGradient id="hermes-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22d3ee" />
              <stop offset="100%" stopColor="#a855f7" />
            </linearGradient>
          </defs>
          <polygon
            points="32,4 56,18 56,46 32,60 8,46 8,18"
            stroke="url(#hermes-grad)"
            strokeWidth="2.5"
            fill="none"
          />
          <circle cx="32" cy="32" r="8" fill="url(#hermes-grad)" opacity="0.8" />
          <line x1="32" y1="24" x2="32" y2="12" stroke="url(#hermes-grad)" strokeWidth="1.5" />
          <line x1="39" y1="28" x2="48" y2="20" stroke="url(#hermes-grad)" strokeWidth="1.5" />
          <line x1="39" y1="36" x2="48" y2="44" stroke="url(#hermes-grad)" strokeWidth="1.5" />
          <line x1="32" y1="40" x2="32" y2="52" stroke="url(#hermes-grad)" strokeWidth="1.5" />
          <line x1="25" y1="36" x2="16" y2="44" stroke="url(#hermes-grad)" strokeWidth="1.5" />
          <line x1="25" y1="28" x2="16" y2="20" stroke="url(#hermes-grad)" strokeWidth="1.5" />
        </svg>

        <h1 className="mt-4 text-2xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
          PycHermesAgent
        </h1>
        <span className="mt-1 text-xs text-gray-500">v0.4.0</span>
        <span className="mt-1 text-sm text-gray-400">本地优先的智能分析引擎</span>
      </div>

      {/* Main prompt */}
      <h2 className="text-2xl font-bold text-gray-100 mb-8">有什么可以帮您的?</h2>

      {/* Quick action grid */}
      <div className="grid grid-cols-2 gap-3 max-w-lg w-full mb-10">
        {quickActions.map((action) => (
          <button
            key={action.title}
            type="button"
            onClick={() => onQuickAction?.(action.text)}
            className="flex flex-col items-start bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 text-left transition hover:border-cyan-500/40 hover:bg-gray-800 group"
          >
            <span className="text-gray-400 group-hover:text-cyan-400 transition mb-2">
              {action.icon}
            </span>
            <span className="text-sm font-medium text-gray-200">{action.title}</span>
            <span className="text-xs text-gray-500 mt-1">{action.desc}</span>
          </button>
        ))}
      </div>

      {/* Capability badges */}
      <div className="flex flex-wrap justify-center gap-2">
        {badges.map((badge) => (
          <span
            key={badge}
            className="px-2.5 py-1 text-xs text-gray-400 border border-gray-700 rounded-full"
          >
            {badge}
          </span>
        ))}
      </div>
    </div>
  );
}
