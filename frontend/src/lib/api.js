import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 15000 });

export const wsLogsUrl = () => {
  const u = new URL(BACKEND_URL);
  const proto = u.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${u.host}/api/ws/logs`;
};

export const MODES = [
  { id: "monitor", label: "Monitor only" },
  { id: "cart", label: "Add to cart" },
  { id: "checkout", label: "Checkout (stop before place)" },
  { id: "auto", label: "Full auto" },
];

export const STATUS_COLORS = {
  IDLE: "bg-white/5 text-[#A1A1AA] border-white/10",
  WATCHING: "bg-white/5 text-[#A1A1AA] border-white/10",
  OOS: "bg-white/5 text-[#A1A1AA] border-white/10",
  IN_STOCK: "bg-[#00FF66]/10 text-[#00FF66] border-[#00FF66]/30",
  QUEUED: "bg-[#FFCC00]/10 text-[#FFCC00] border-[#FFCC00]/30",
  ERROR: "bg-[#FF3B30]/10 text-[#FF3B30] border-[#FF3B30]/30",
  PURCHASED: "bg-[#007AFF]/10 text-[#007AFF] border-[#007AFF]/30",
};

export const LOG_COLORS = {
  INFO: "text-[#A1A1AA]",
  SUCCESS: "text-[#00FF66]",
  WARN: "text-[#FFCC00]",
  ERROR: "text-[#FF3B30]",
  PING: "text-[#52525B]",
};
