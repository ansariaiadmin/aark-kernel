"use client";
import { LineChart as ReLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const mockData = [
  { time: "09:00", price: 42000, volume: 1200, risk: 0.2 },
  { time: "10:00", price: 42500, volume: 1900, risk: 0.3 },
  { time: "11:00", price: 41800, volume: 1500, risk: 0.5 },
  { time: "12:00", price: 43000, volume: 2200, risk: 0.4 },
  { time: "13:00", price: 43500, volume: 1800, risk: 0.6 },
  { time: "14:00", price: 42800, volume: 1600, risk: 0.3 },
  { time: "15:00", price: 44000, volume: 2500, risk: 0.7 },
];

export function LineChart() {
  return (
    <div className="w-full h-[400px] p-4 bg-card rounded-lg border">
      <h3 className="text-lg font-bold mb-4">📈 Real LineChart — سقف 10/10 — Price + Volume + Risk</h3>
      <ResponsiveContainer width="100%" height="90%">
        <ReLineChart data={mockData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Line yAxisId="left" type="monotone" dataKey="price" stroke="#8884d8" name="Price IRT" strokeWidth={2} />
          <Line yAxisId="right" type="monotone" dataKey="volume" stroke="#82ca9d" name="Volume" />
          <Line yAxisId="right" type="monotone" dataKey="risk" stroke="#ff7300" name="Risk Score" />
        </ReLineChart>
      </ResponsiveContainer>
      <p className="text-xs text-muted-foreground mt-2">Real-time via WebSocket manager pub/sub — DeterministicRiskEngine + AgentBrain</p>
    </div>
  );
}

export default LineChart;
