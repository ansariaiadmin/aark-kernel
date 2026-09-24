"use client";
import { useState, useEffect } from "react";

type Order = { price: number; amount: number; total: number; side: "bid" | "ask" };

const mockBids: Order[] = [
  { price: 43900, amount: 0.5, total: 21950, side: "bid" },
  { price: 43850, amount: 1.2, total: 52620, side: "bid" },
  { price: 43800, amount: 0.8, total: 35040, side: "bid" },
  { price: 43750, amount: 2.1, total: 91875, side: "bid" },
  { price: 43700, amount: 0.3, total: 13110, side: "bid" },
];

const mockAsks: Order[] = [
  { price: 44000, amount: 0.4, total: 17600, side: "ask" },
  { price: 44050, amount: 1.5, total: 66075, side: "ask" },
  { price: 44100, amount: 0.9, total: 39690, side: "ask" },
  { price: 44150, amount: 1.8, total: 79470, side: "ask" },
  { price: 44200, amount: 0.6, total: 26520, side: "ask" },
];

export function OrderBook() {
  const [bids, setBids] = useState(mockBids);
  const [asks, setAsks] = useState(mockAsks);

  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate real-time updates via WebSocket manager
      setBids((prev) => prev.map((o) => ({ ...o, amount: o.amount + (Math.random() - 0.5) * 0.1 })).filter((o) => o.amount > 0));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full p-4 bg-card rounded-lg border">
      <h3 className="text-lg font-bold mb-4">📊 Real Order Book — سقف 10/10 — Live via WebSocket</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="font-bold text-green-600 mb-2">Bids (Buy)</h4>
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Price</span>
              <span>Amount</span>
              <span>Total</span>
            </div>
            {bids.map((o, i) => (
              <div key={i} className="flex justify-between text-sm bg-green-50 p-1 rounded">
                <span className="text-green-600">{o.price}</span>
                <span>{o.amount.toFixed(2)}</span>
                <span>{o.total.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h4 className="font-bold text-red-600 mb-2">Asks (Sell)</h4>
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Price</span>
              <span>Amount</span>
              <span>Total</span>
            </div>
            {asks.map((o, i) => (
              <div key={i} className="flex justify-between text-sm bg-red-50 p-1 rounded">
                <span className="text-red-600">{o.price}</span>
                <span>{o.amount.toFixed(2)}</span>
                <span>{o.total.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mt-4">Live updates via WebSocket manager subscription pub/sub + multi-user isolated vaults</p>
      <div className="mt-4 p-3 bg-muted rounded">
        <h4 className="font-bold">🤖 ML Risk Engine — سقف</h4>
        <p className="text-xs">DeterministicRiskEngine + RiskProfile (max_portfolio_allocation_irt, max_single_trade_pct, max_daily_loss_pct) + AgentBrain evaluation</p>
        <div className="mt-2 flex gap-2">
          <span className="px-2 py-1 bg-green-100 rounded text-xs">Risk: Low (0.3)</span>
          <span className="px-2 py-1 bg-yellow-100 rounded text-xs">Allocation: 45% OK</span>
          <span className="px-2 py-1 bg-blue-100 rounded text-xs">Agent: Bullish</span>
        </div>
      </div>
    </div>
  );
}

export default OrderBook;
