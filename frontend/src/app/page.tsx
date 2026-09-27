'use client';
import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldCheck, Activity, Terminal, Play, Square, Cpu, 
  Wifi, WifiOff, Send, TrendingUp, AlertTriangle,
  Loader2, Wallet, Zap, Brain, Lock, LogOut
} from 'lucide-react';
import { apiUrl, wsUrl } from '@/lib/api';
import { authFetch, getToken, getUser, login, logout, type SessionUser } from '@/lib/auth';
import { LineChart } from '@/components/LineChart';
import { OrderBook } from '@/components/OrderBook';

interface MarketData {
  symbol: string;
  price: number;
  change24h: number;
  volume24h: number;
}

interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  type: string;
  quantity: number;
  price?: number;
  status: string;
  timestamp: string;
}

interface Position {
  symbol: string;
  side: string;
  quantity: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
}

interface RiskMetric {
  name: string;
  value: number;
  threshold: number;
  level: 'low' | 'medium' | 'high' | 'critical';
  description: string;
}

interface AgentMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

const toFa = (n: number) => n.toLocaleString('fa-IR');

type TabId = 'chat' | 'orders' | 'positions' | 'analytics';

export default function Dashboard() {
  // --- session -----------------------------------------------------------
  // `aark_token` used to be *read* here but never *written* anywhere in the
  // app, so the WebSocket never connected and every real-time panel stayed
  // empty forever. Login now owns that key.
  const [session, setSession] = useState<SessionUser | null>(null);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginBusy, setLoginBusy] = useState(false);

  const [activeTab, setActiveTab] = useState<TabId>('chat');

  const [logs, setLogs] = useState<string[]>([
    '[SYSTEM] AARK Engine initialized on Ubuntu 24.04.',
    '[ORCHESTRATOR] Node healthy. Snapshot fetched: BTC/IRT spread: 0.08%. Risk state: Clean.',
    '[INTEL_AGENT] YouTube transcript parsed: Macro trend bullish (Confidence: 74%).',
    '[RISK_ENGINE] Evaluating swing order: 1,500,000 IRT -> APPROVED by Deterministic Engine.',
    '[AGENT_STREAM] Awaiting next market trigger...'
  ]);
  
  const [walletBalance, setWalletBalance] = useState(10000000);
  const [maxOrderCap, setMaxOrderCap] = useState(2000000);
  const [vaultStatus, setVaultStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const [vaultEmail, setVaultEmail] = useState('');
  const [vaultLog, setVaultLog] = useState('در حال بررسی...');
  const [apiKey, setApiKey] = useState('');
  
  const [telemetry, setTelemetry] = useState({
    action: 'HOLD',
    confidence: 100,
    allocated: 0,
    reason: 'سیستم آماده دریافت درخواست...'
  });
  
  const [marketData, setMarketData] = useState<MarketData>({
    symbol: 'BTCUSDT',
    price: 0,
    change24h: 0,
    volume24h: 0
  });
  
  const [orders, setOrders] = useState<Order[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetric[]>([]);
  const [chatMessages, setChatMessages] = useState<AgentMessage[]>([
    { role: 'assistant', content: 'درود ممد جان. ساعت معاملاتی تهران و سشن‌های لندن، نیویورک و توکیو سنکرون شدند. چارت زنده BTCUSDT بدون قطعی متصل است. سناریو یا تحلیل مد نظرت را بفرست.', timestamp: new Date().toISOString() }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // ---------------------------------------------------------------------
  // WebSocket — real-time layer.
  //
  // Was hardcoded to `ws://localhost:8000` (breaks behind any proxy/preview
  // host and on https pages, where a mixed-content ws:// is blocked outright)
  // and gated on a token that was never stored. Now derived via wsUrl() and
  // re-run whenever the session changes, with bounded reconnect/backoff.
  // ---------------------------------------------------------------------
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setWsConnected(false);
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      socket = new WebSocket(wsUrl('/api/v1/ws/ws', { token }));
      wsRef.current = socket;

      socket.onopen = () => {
        retry = 0;
        setWsConnected(true);
        addLog('[WS] Real-time connection established');
        for (const topic of ['market.BTCUSDT', 'portfolio', 'risk']) {
          socket?.send(JSON.stringify({ type: 'subscribe', topic }));
        }
      };

      socket.onmessage = (event) => {
        try {
          handleWebSocketMessage(JSON.parse(event.data));
        } catch (err) {
          addLog('[WS] parse error: ' + String(err), 'error');
        }
      };

      socket.onclose = () => {
        setWsConnected(false);
        if (cancelled) return;
        retry += 1;
        const delay = Math.min(1000 * 2 ** retry, 30000);
        addLog(`[WS] Connection closed — retry ${retry} in ${Math.round(delay / 1000)}s`, 'warning');
        timer = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        addLog('[WS] Connection error', 'error');
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      socket?.close();
      wsRef.current = null;
    };
  }, [session]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'market_update':
        setMarketData(prev => ({ ...prev, ...data.data }));
        break;
      case 'order_update':
        setOrders(prev => {
          const idx = prev.findIndex(o => o.id === data.data.id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], ...data.data };
            return updated;
          }
          return [data.data, ...prev];
        });
        addLog(`[ORDER] ${data.data.side.toUpperCase()} ${data.data.symbol} ${data.data.status}`);
        break;
      case 'position_update':
        setPositions(prev => {
          const idx = prev.findIndex(p => p.symbol === data.data.symbol);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], ...data.data };
            return updated;
          }
          return [...prev, data.data];
        });
        break;
      case 'risk_alert':
        addLog(`[RISK ALERT] ${data.data.message}`, 'warning');
        break;
      case 'portfolio_update':
        if (data.data.total_value_irt) {
          setWalletBalance(data.data.total_value_irt);
          setMaxOrderCap(data.data.total_value_irt * 0.2);
        }
        break;
      case 'agent_message':
        setChatMessages(prev => [...prev, { role: 'assistant', content: data.data.content, timestamp: new Date().toISOString() }]);
        break;
      case 'notification':
        addLog(`[NOTIF] ${data.data.message}`);
        break;
    }
  };

  const addLog = (msg: string, type: 'info' | 'warning' | 'error' = 'info') => {
    const prefix = type === 'warning' ? '[WARN]' : type === 'error' ? '[ERROR]' : '[INFO]';
    setLogs(prev => [...prev.slice(-49), `${prefix} ${msg}`]);
  };

  // ---------------------------------------------------------------------
  // Session bootstrap: restore a stored JWT, then load portfolio data.
  // Previously `fetchInitialData()` ran unconditionally on mount against
  // endpoints that require a Bearer token, so it always failed with 401 and
  // the dashboard silently showed zeros.
  // ---------------------------------------------------------------------
  useEffect(() => {
    if (getToken()) {
      setSession(getUser() ?? ({ id: 0, email: '', full_name: null, role: '', is_active: true, is_superuser: false } as SessionUser));
    }
    setBootstrapped(true);
  }, []);

  useEffect(() => {
    if (!session) return;
    fetchInitialData();
    checkVault();
  }, [session]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginBusy(true);
    setLoginError('');
    try {
      const user = await login(loginEmail.trim(), loginPassword);
      setLoginPassword('');
      setSession(user);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'خطای نامشخص در ورود');
    } finally {
      setLoginBusy(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    wsRef.current?.close();
    wsRef.current = null;
    setSession(null);
    setWsConnected(false);
    setOrders([]);
    setPositions([]);
    setRiskMetrics([]);
    addLog('[AUTH] Session ended');
  };

  const fetchInitialData = async () => {
    try {
      const [balancesRes, positionsRes, ordersRes, riskRes] = await Promise.all([
        authFetch('/api/v1/trading/portfolio/balances').catch(() => null),
        authFetch('/api/v1/trading/portfolio/positions').catch(() => null),
        authFetch('/api/v1/trading/orders').catch(() => null),
        authFetch('/api/v1/risk/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ positions: {}, prices: {}, daily_pnl: 0, portfolio_value: walletBalance })
        }).catch(() => null)
      ]);

      if (balancesRes?.ok) {
        const balances = await balancesRes.json();
        const irtBalance = balances.find((b: any) => b.asset === 'IRT');
        if (irtBalance) {
          setWalletBalance(irtBalance.total);
          setMaxOrderCap(irtBalance.total * 0.2);
        }
      }
      if (positionsRes?.ok) setPositions(await positionsRes.json());
      if (ordersRes?.ok) setOrders(await ordersRes.json());
      if (riskRes?.ok) {
        const risk = await riskRes.json();
        setRiskMetrics(risk.metrics);
      }
    } catch (err) {
      addLog('Failed to fetch initial data: ' + String(err), 'error');
    }
  };

  const checkVault = async () => {
    try {
      const res = await fetch(apiUrl('/api/v1/nobitex/status'));
      const data = await res.json();
      if (data.connected) {
        setVaultStatus('connected');
        setVaultEmail(data.email);
        setVaultLog('اکانت: ' + data.email);
      } else {
        setVaultStatus('disconnected');
        setVaultLog(data.message);
      }
    } catch {
      setVaultStatus('disconnected');
      setVaultLog('خطای سرور');
    }
  };

  const saveKey = async () => {
    if (apiKey.length < 20) {
      alert('طول کلید وارد شده نامعتبر است.');
      return;
    }
    setVaultLog('در حال اعتبارسنجی و ایزوله‌سازی...');
    try {
      const res = await fetch(apiUrl('/api/v1/nobitex/save-key'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      });
      const data = await res.json();
      setApiKey('');
      setVaultLog(data.message);
      setTimeout(checkVault, 1000);
    } catch {
      setVaultLog('خطا در ذخیره کلید');
    }
  };

  const sendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isLoading) return;

    const userMessage = chatInput.trim();
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: new Date().toISOString() }]);
    setChatInput('');
    setIsLoading(true);

    try {
      const res = await fetch(apiUrl('/api/v1/agent/evaluate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_balance_irt: walletBalance,
          market_context: userMessage
        })
      });
      const data = await res.json();
      const dec = data.agent_decision || {};
      
      setChatMessages(prev => [...prev, { role: 'assistant', content: dec.reply_message || dec.reason, timestamp: new Date().toISOString() }]);
      
      const act = (data.execution?.action || 'HOLD').toUpperCase();
      setTelemetry({
        action: act,
        confidence: dec.confidence || 0,
        allocated: data.execution?.allocated_irt || 0,
        reason: dec.reason || '-'
      });
    } catch (err: any) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'خطا در پردازش: ' + err.message, timestamp: new Date().toISOString() }]);
    } finally {
      setIsLoading(false);
    }
  };

  const placeOrder = async (side: 'buy' | 'sell') => {
    try {
      const res = await authFetch('/api/v1/trading/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: 'BTCUSDT',
          side,
          order_type: 'market',
          quantity: 0.001,
        })
      });
      const data = await res.json();
      if (data.order_id) {
        addLog(`[ORDER] ${side.toUpperCase()} order placed: ${data.order_id}`);
        fetchInitialData();
      }
    } catch (err) {
      addLog('Order failed: ' + String(err), 'error');
    }
  };

  // Kill switch: cancel every open order, then drop the exchange credential so
  // nothing new can be submitted. Wired to the header button, which previously
  // had no onClick handler at all.
  const [killing, setKilling] = useState(false);
  const killSwitch = async () => {
    if (killing) return;
    if (!window.confirm('Kill Switch: تمام سفارش‌های باز لغو و کلید صرافی حذف می‌شود. ادامه؟')) return;

    setKilling(true);
    addLog('[KILL SWITCH] engaged', 'warning');
    try {
      const open = orders.filter(o => o.status === 'pending' || o.status === 'submitted' || o.status === 'partial');
      const results = await Promise.allSettled(
        open.map(o => authFetch(`/api/v1/trading/orders/${encodeURIComponent(o.id)}`, { method: 'DELETE' }))
      );
      const cancelled = results.filter(r => r.status === 'fulfilled' && r.value.ok).length;
      addLog(`[KILL SWITCH] ${cancelled}/${open.length} open order(s) cancelled`, cancelled === open.length ? 'info' : 'warning');

      const res = await fetch(apiUrl('/api/v1/nobitex/key'), { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      addLog(`[KILL SWITCH] vault: ${data.message ?? res.status}`, res.ok ? 'info' : 'error');

      setVaultStatus('disconnected');
      setVaultEmail('');
      setVaultLog('کلید صرافی حذف شد — Kill Switch فعال');
      await fetchInitialData();
    } catch (err) {
      addLog('[KILL SWITCH] failed: ' + String(err), 'error');
    } finally {
      setKilling(false);
    }
  };

  // Tehran clock
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const tehranTime = now.toLocaleTimeString('fa-IR', { timeZone: 'Asia/Tehran' });
      const tehranDate = now.toLocaleDateString('fa-IR', { 
        timeZone: 'Asia/Tehran', 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
      // Update clock elements if they exist
      const clockEl = document.getElementById('liveClock');
      const dateEl = document.getElementById('liveDate');
      if (clockEl) clockEl.innerText = tehranTime;
      if (dateEl) dateEl.innerText = tehranDate;
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // Market sessions
  useEffect(() => {
    const updateSessions = () => {
      const now = new Date();
      const tehranDate = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tehran' }));
      const hours = tehranDate.getHours() + tehranDate.getMinutes() / 60;

      const sessions = [
        { id: 'sessTokyo', active: hours >= 3.5 && hours < 12.5 },
        { id: 'sessLondon', active: hours >= 11.5 && hours < 20.5 },
        { id: 'sessNY', active: (hours >= 16.5 && hours <= 24) || (hours >= 0 && hours < 1.5) },
      ];

      sessions.forEach(s => {
        const el = document.getElementById(s.id);
        const dot = el?.querySelector('.pill-dot');
        if (el && dot) {
          if (s.active) {
            dot.classList.add('active');
            el.style.color = 'var(--emerald-ok)';
          } else {
            dot.classList.remove('active');
            el.style.color = 'var(--text-muted)';
          }
        }
      });
    };
    updateSessions();
    const interval = setInterval(updateSessions, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!bootstrapped) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center font-sans">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
      </main>
    );
  }

  if (!session) {
    // The trading/AI/risk surface is JWT-protected, so the dashboard has to
    // authenticate before it can show anything real.
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6 font-sans">
        <form
          onSubmit={handleLogin}
          className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 space-y-5"
        >
          <div className="flex items-center gap-3">
            <Cpu className="w-7 h-7 text-emerald-400" />
            <div>
              <h1 className="text-xl font-bold text-emerald-400 tracking-tight">AARK Kernel</h1>
              <p className="text-xs text-slate-400">Control Center — ورود اپراتور</p>
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="email" className="text-xs text-slate-400 block">ایمیل</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
              placeholder="admin@aark-kernel.dev"
              className="w-full bg-slate-950 border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:border-emerald-400 focus:outline-none"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="password" className="text-xs text-slate-400 block">رمز عبور</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full bg-slate-950 border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:border-emerald-400 focus:outline-none"
            />
          </div>

          {loginError && (
            <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-lg p-3 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-px" />
              <span>{loginError}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loginBusy || !loginEmail.trim() || !loginPassword}
            className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold py-2.5 rounded-lg text-sm transition"
          >
            {loginBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
            ورود به هسته
          </button>

          <p className="text-[11px] text-slate-500 leading-relaxed">
            حساب ادمین از <code className="text-slate-400">ADMIN_EMAIL</code> /{' '}
            <code className="text-slate-400">ADMIN_PASSWORD</code> در فایل <code className="text-slate-400">.env</code>{' '}
            هنگام اولین راه‌اندازی ساخته می‌شود.
          </p>
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      <header className="flex justify-between items-center pb-6 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-bold text-emerald-400 tracking-tight">AARK Kernel Control Center</h1>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className={wsConnected ? 'text-emerald-400' : 'text-rose-400'}>{wsConnected ? '● LIVE' : '○ OFFLINE'}</span>
            <span>| {session.email}</span>
            <span className="uppercase">| {session.role}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Both buttons were inert before — no onClick at all. */}
          <button
            type="button"
            onClick={fetchInitialData}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50"
            disabled={isLoading}
          >
            <Play className="w-4 h-4" /> Refresh Engine
          </button>
          <button
            type="button"
            onClick={killSwitch}
            className="flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
          >
            <Square className="w-4 h-4" /> Kill Switch
          </button>
          <button
            type="button"
            onClick={handleLogout}
            title="خروج از حساب"
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-lg text-sm font-medium transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-sm font-medium">سرمایه در گردش (IRT)</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-white">{toFa(walletBalance)}</div>
          <span className="text-xs text-emerald-400 font-mono mt-1 block">سقف سفارش (۲۰٪): {toFa(maxOrderCap)}</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-sm font-medium">وضعیت ریسک انجین</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">ACTIVE</div>
          <span className="text-xs text-slate-400 font-mono mt-1 block">Max Daily Loss: 1.5% | VaR: Enabled</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-sm font-medium">مدل هوش فعال</span>
            <Brain className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-white mt-1">Dynamic Router (Ollama + Cloud)</div>
          <span className="text-xs text-purple-400 font-mono mt-2 block">Tools: ON | Memory: ON | Streaming: ON</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-sm font-medium">والت نوبیتکس</span>
            {vaultStatus === 'connected' ? (
              <Wifi className="w-4 h-4 text-emerald-400" />
            ) : vaultStatus === 'checking' ? (
              <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            ) : (
              <WifiOff className="w-4 h-4 text-rose-400" />
            )}
          </div>
          <div className="text-xl font-bold text-white mt-1">
            {vaultStatus === 'connected' ? 'متصل' : vaultStatus === 'checking' ? 'بررسی...' : 'غیرفعال'}
          </div>
          <span className="text-xs text-slate-400 font-mono mt-2 block">{vaultEmail || vaultLog}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Left Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Vault & Risk Controls */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
              <Wallet className="w-5 h-5" /> والت امن نوبیتکس
            </h3>
            <div className="space-y-3">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="کلید API امن نوبیتکس..."
                className="w-full bg-slate-950 border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:border-cyan-400 focus:outline-none"
              />
              <button
                onClick={saveKey}
                className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold py-2 rounded-lg text-sm hover:from-cyan-400 hover:to-blue-500 transition"
              >
                ذخیره در هسته با مجوز ایزوله
              </button>
              <div className="text-xs text-slate-400">{vaultLog}</div>
            </div>
          </div>

          {/* Risk Controls */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5" /> کنترل ریسک و بودجه
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">موجودی تخصیص‌یافته (IRT)</label>
                <input
                  type="range"
                  min="1000000"
                  max="100000000"
                  step="1000000"
                  value={walletBalance}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value);
                    setWalletBalance(v);
                    setMaxOrderCap(v * 0.2);
                  }}
                  className="w-full accent-cyan-400"
                />
                <div className="flex justify-between text-xs mt-1">
                  <span className="text-slate-400">۱ میلیون</span>
                  <span className="text-emerald-400">{toFa(walletBalance)}</span>
                  <span className="text-slate-400">۱۰۰ میلیون</span>
                </div>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-700">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">حداکثر سقف مجاز (۲۰٪):</span>
                  <span className="text-cyan-400 font-bold">{toFa(maxOrderCap)} تومان</span>
                </div>
              </div>
            </div>
          </div>

          {/* Telemetry */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
              <Zap className="w-5 h-5" /> تلمتري تصمیم‌گیری
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-slate-400">تصمیم:</span>
                <span className={`badge-status px-2 py-1 rounded text-xs font-bold ${
                  telemetry.action === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' :
                  telemetry.action === 'SELL' ? 'bg-rose-500/20 text-rose-400' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {telemetry.action}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">ضریب اطمینان:</span>
                <span className="text-white font-bold">{telemetry.confidence}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">تخصیص تایید شده:</span>
                <span className="text-cyan-400 font-bold">{toFa(telemetry.allocated)} تومان</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-700">
                <div className="text-xs text-cyan-400 font-bold mb-1">تحلیل استراتژیک:</div>
                <p className="text-xs text-slate-400">{telemetry.reason}</p>
              </div>
            </div>
          </div>

          {/* Risk Metrics */}
          {riskMetrics.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" /> متریک‌های ریسک
              </h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {riskMetrics.map((m, i) => (
                  <div key={i} className="text-xs p-2 bg-slate-950 rounded border border-slate-700">
                    <div className="flex justify-between">
                      <span className="text-slate-300">{m.name}</span>
                      <span className={`font-bold ${
                        m.level === 'critical' ? 'text-rose-400' :
                        m.level === 'high' ? 'text-amber-400' :
                        m.level === 'medium' ? 'text-cyan-400' : 'text-emerald-400'
                      }`}>
                        {m.level.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-slate-500 mt-1">{m.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Chart & Chat */}
        <div className="lg:col-span-2 space-y-6">
          {/* TradingView Chart */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cyan-400" />
                چارت زنده BTCUSDT (TradingView)
              </h3>
              <div className="flex items-center gap-4 text-xs text-slate-400">
                <span>قیمت: {marketData.price > 0 ? '$' + marketData.price.toLocaleString() : '—'}</span>
                <span className={marketData.change24h >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                  {marketData.change24h >= 0 ? '+' : ''}{marketData.change24h.toFixed(2)}%
                </span>
                <span>حجم: {toFa(marketData.volume24h)}</span>
              </div>
            </div>
            <div className="chart-container" style={{ height: '420px', width: '100%' }}>
              <iframe
                className="tv-embed"
                src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_7623a&symbol=BINANCE%3ABTCUSDT&interval=15&hidesidetoolbar=0&symboledit=1&saveimage=0&toolbarbg=0b1220&studies=%5B%5D&theme=dark&style=1&timezone=Asia%2FTehran&locale=fa_IR"
                allowTransparency
                scrolling="no"
                allowFullScreen
                title="TradingView Chart"
              ></iframe>
            </div>
          </div>

          {/* Tabs — the buttons used to render but had no onClick and no
              active state, so 'orders' and 'positions' were unreachable and the
              fetched data was discarded into `_orders` / `_positions`. */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="flex border-b border-slate-800 bg-slate-950" role="tablist">
              {([
                { id: 'chat', label: 'Chat', Icon: Terminal },
                { id: 'orders', label: 'Orders', Icon: Activity },
                { id: 'positions', label: 'Positions', Icon: TrendingUp },
                { id: 'analytics', label: 'Analytics', Icon: Brain },
              ] as const).map(({ id, label, Icon }) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === id}
                  onClick={() => setActiveTab(id)}
                  className={`flex-1 py-3 px-4 text-sm font-medium text-center transition-colors border-b-2 ${
                    activeTab === id
                      ? 'text-cyan-400 border-cyan-400 bg-slate-900'
                      : 'text-slate-400 border-transparent hover:text-slate-200'
                  }`}
                >
                  <Icon className="w-4 h-4 inline ml-1" />
                  {label}
                  {id === 'orders' && orders.length > 0 && (
                    <span className="mr-1 text-[10px] bg-slate-800 text-slate-300 rounded-full px-1.5">{orders.length}</span>
                  )}
                  {id === 'positions' && positions.length > 0 && (
                    <span className="mr-1 text-[10px] bg-slate-800 text-slate-300 rounded-full px-1.5">{positions.length}</span>
                  )}
                </button>
              ))}
            </div>

            <div className="p-4">
              {activeTab === 'orders' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">سفارش سریع BTCUSDT — market 0.001</span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => placeOrder('buy')}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition"
                      >
                        BUY
                      </button>
                      <button
                        type="button"
                        onClick={() => placeOrder('sell')}
                        className="bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition"
                      >
                        SELL
                      </button>
                    </div>
                  </div>
                  <div className="overflow-x-auto bg-slate-950 rounded-lg border border-slate-800">
                    <table className="w-full text-xs">
                      <thead className="text-slate-400 border-b border-slate-800">
                        <tr>
                          {['Symbol', 'Side', 'Type', 'Qty', 'Price', 'Status', 'Time'].map(h => (
                            <th key={h} className="text-right px-3 py-2 font-medium whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {orders.length === 0 && (
                          <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">سفارشی ثبت نشده است</td></tr>
                        )}
                        {orders.map(o => (
                          <tr key={o.id} className="border-b border-slate-800/60 last:border-0">
                            <td className="px-3 py-2 font-mono text-slate-200">{o.symbol}</td>
                            <td className={`px-3 py-2 font-bold ${o.side === 'buy' ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {o.side.toUpperCase()}
                            </td>
                            <td className="px-3 py-2 text-slate-400">{o.type}</td>
                            <td className="px-3 py-2 font-mono">{o.quantity}</td>
                            <td className="px-3 py-2 font-mono">{o.price ? o.price.toLocaleString() : '—'}</td>
                            <td className="px-3 py-2">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                o.status === 'filled' ? 'bg-emerald-500/20 text-emerald-400'
                                : o.status === 'cancelled' || o.status === 'rejected' ? 'bg-rose-500/20 text-rose-400'
                                : 'bg-amber-500/20 text-amber-400'
                              }`}>{o.status}</span>
                            </td>
                            <td className="px-3 py-2 text-slate-500 whitespace-nowrap">
                              {new Date(o.timestamp).toLocaleTimeString('fa-IR')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {activeTab === 'positions' && (
                <div className="overflow-x-auto bg-slate-950 rounded-lg border border-slate-800">
                  <table className="w-full text-xs">
                    <thead className="text-slate-400 border-b border-slate-800">
                      <tr>
                        {['Symbol', 'Side', 'Qty', 'Entry', 'Mark', 'Unrealized PnL', 'Realized PnL'].map(h => (
                          <th key={h} className="text-right px-3 py-2 font-medium whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {positions.length === 0 && (
                        <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">پوزیشن بازی وجود ندارد</td></tr>
                      )}
                      {positions.map(pos => (
                        <tr key={pos.symbol} className="border-b border-slate-800/60 last:border-0">
                          <td className="px-3 py-2 font-mono text-slate-200">{pos.symbol}</td>
                          <td className="px-3 py-2 text-slate-400">{pos.side}</td>
                          <td className="px-3 py-2 font-mono">{pos.quantity}</td>
                          <td className="px-3 py-2 font-mono">{pos.entryPrice.toLocaleString()}</td>
                          <td className="px-3 py-2 font-mono">{pos.markPrice.toLocaleString()}</td>
                          <td className={`px-3 py-2 font-mono font-bold ${pos.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {pos.unrealizedPnl >= 0 ? '+' : ''}{pos.unrealizedPnl.toLocaleString()}
                          </td>
                          <td className={`px-3 py-2 font-mono ${pos.realizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {pos.realizedPnl.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {activeTab === 'analytics' && (
                <div className="space-y-4">
                  <LineChart />
                  <OrderBook />
                </div>
              )}

              {activeTab === 'chat' && (
              <div className="space-y-4">
                <div className="font-mono text-xs text-slate-300 space-y-2 bg-slate-950 p-4 rounded-lg h-64 overflow-y-auto">
                  {chatMessages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                      <div className={`max-w-[80%] px-3 py-2 rounded-lg text-xs leading-relaxed ${
                        msg.role === 'user' 
                          ? 'bg-blue-600 text-white rounded-br-none' 
                          : 'bg-slate-800 border border-slate-700 rounded-bl-none'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                
                <form onSubmit={sendChat} className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="پیام، سناریو بازار یا فرمان خرید/فروش..."
                    className="flex-1 bg-slate-950 border border-slate-700 text-white px-3 py-2 rounded-lg text-sm focus:border-cyan-400 focus:outline-none"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !chatInput.trim()}
                    className="bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-bold px-4 py-2 rounded-lg text-sm hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50"
                  >
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </button>
                </form>
              </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Live Logs */}
      <div className="mt-6 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4 text-slate-400 border-b border-slate-800 pb-3">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-mono font-medium">لایو لاگ‌های سیستم (AARK Core Stream)</span>
          <span className="ml-auto text-xs text-slate-500">{logs.length} entries</span>
        </div>
        <div className="font-mono text-xs text-slate-300 space-y-1 bg-slate-950 p-4 rounded-lg h-48 overflow-y-auto">
          {logs.map((log, idx) => (
            <div key={idx} className={log.includes('WARN') ? 'text-amber-400' : log.includes('ERROR') ? 'text-rose-400' : 'text-emerald-400'}>
              {log}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}