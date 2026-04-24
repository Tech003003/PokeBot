import React, { useCallback, useEffect, useState } from "react";
import "@/App.css";
import { Toaster } from "sonner";
import { api, STATUS_COLORS } from "@/lib/api";
import Header from "@/components/Header";
import Watchlist from "@/components/Watchlist";
import Profiles from "@/components/Profiles";
import Drops from "@/components/Drops";
import Browsers from "@/components/Browsers";
import SettingsPanel from "@/components/Settings";
import History from "@/components/History";
import LogTerminal from "@/components/LogTerminal";
import { Activity, List, Clock, User, Settings as Cog, History as HistIcon, Chrome } from "lucide-react";

const TABS = [
  { id: "monitor", label: "Monitor", icon: Activity },
  { id: "watch", label: "Watchlist", icon: List },
  { id: "drops", label: "Drops", icon: Clock },
  { id: "browsers", label: "Browsers", icon: Chrome },
  { id: "profiles", label: "Profiles", icon: User },
  { id: "history", label: "History", icon: HistIcon },
  { id: "settings", label: "Settings", icon: Cog },
];

function App() {
  const [tab, setTab] = useState("monitor");
  const [status, setStatus] = useState(null);
  const [sites, setSites] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [watch, setWatch] = useState([]);
  const [browsers, setBrowsers] = useState([]);

  const refresh = useCallback(async () => {
    try {
      const [st, sm, pr, wl, bs] = await Promise.all([
        api.get("/status"), api.get("/meta/sites"), api.get("/profiles"), api.get("/watch"), api.get("/browsers"),
      ]);
      setStatus(st.data); setSites(sm.data); setProfiles(pr.data); setWatch(wl.data); setBrowsers(bs.data);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 2500); return () => clearInterval(t); }, [refresh]);

  const counts = {
    total: watch.length,
    active: watch.filter((w) => w.active).length,
    in_stock: watch.filter((w) => w.status === "IN_STOCK").length,
    queued: watch.filter((w) => w.status === "QUEUED").length,
    errors: watch.filter((w) => w.status === "ERROR").length,
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-white" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      <Toaster theme="dark" position="bottom-right" toastOptions={{ style: { background: "#121214", border: "1px solid #27272a", color: "white", borderRadius: 0 } }} />
      <Header status={status} refresh={refresh} />

      <div className="max-w-[1600px] mx-auto px-4 sm:px-8 py-6">
        <nav className="flex gap-1 mb-6 border-b border-[#27272a] overflow-x-auto">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                data-testid={`tab-${t.id}`}
                onClick={() => setTab(t.id)}
                className={`px-4 py-3 text-xs font-bold uppercase tracking-[0.15em] flex items-center gap-2 border-b-2 transition-colors ${active ? "border-[#00FF66] text-[#00FF66]" : "border-transparent text-[#A1A1AA] hover:text-white"}`}
              >
                <Icon size={14}/> {t.label}
              </button>
            );
          })}
        </nav>

        {tab === "monitor" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <Stat label="Watchers" value={counts.total}/>
                <Stat label="Active" value={counts.active} color="#00FF66"/>
                <Stat label="In Stock" value={counts.in_stock} color="#00FF66"/>
                <Stat label="Queued" value={counts.queued} color="#FFCC00"/>
                <Stat label="Errors" value={counts.errors} color="#FF3B30"/>
              </div>
              <LiveCards items={watch} sites={sites}/>
            </div>
            <div className="space-y-4">
              <div className="bg-[#121214] border border-[#27272a]">
                <div className="p-3 border-b border-[#27272a] text-[10px] font-black tracking-[0.2em] uppercase text-[#A1A1AA]" style={{fontFamily:"'Chivo', sans-serif"}}>Live Terminal</div>
                <LogTerminal/>
              </div>
              <div className="bg-[#121214] border border-[#27272a] p-4">
                <div className="text-[10px] font-black tracking-[0.2em] uppercase text-[#A1A1AA] mb-3" style={{fontFamily:"'Chivo', sans-serif"}}>Quick Links</div>
                <ol className="text-xs text-[#A1A1AA] space-y-2 list-decimal list-inside">
                  <li>Close all Brave windows</li>
                  <li>Run: <code className="bg-[#09090b] px-1.5 py-0.5 border border-[#27272a] font-mono text-[10px]">brave --remote-debugging-port=9222</code></li>
                  <li>Log into your retailer accounts inside Brave</li>
                  <li>Click <span className="text-[#FF6B00]">Connect Brave</span> above</li>
                  <li>Add watches, then <span className="text-[#00FF66]">Start All</span></li>
                </ol>
              </div>
            </div>
          </div>
        )}

        {tab === "watch" && <Watchlist sites={sites} profiles={profiles} browsers={browsers} onChange={refresh}/>}
        {tab === "drops" && <Drops sites={sites} profiles={profiles} browsers={browsers}/>}
        {tab === "browsers" && <Browsers onChange={refresh}/>}
        {tab === "profiles" && <Profiles onChange={refresh}/>}
        {tab === "history" && <History/>}
        {tab === "settings" && <SettingsPanel/>}
      </div>
    </div>
  );
}

function Stat({ label, value, color = "#FFFFFF" }) {
  return (
    <div className="bg-[#121214] border border-[#27272a] p-4" data-testid={`stat-${label.toLowerCase().replace(/\s/g,'-')}`}>
      <div className="text-[10px] font-black tracking-[0.2em] uppercase text-[#52525B]">{label}</div>
      <div className="text-3xl font-black mt-1" style={{ color, fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
    </div>
  );
}

function LiveCards({ items, sites }) {
  if (items.length === 0) return (
    <div className="bg-[#121214] border border-[#27272a] p-12 text-center">
      <div className="text-[#52525B] text-sm">No watchers yet. Head to <span className="text-[#00FF66]">Watchlist</span> to add products.</div>
    </div>
  );
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {items.map((it) => (
        <div key={it.id} className={`bg-[#121214] border p-3 ${it.status === "IN_STOCK" ? "border-[#00FF66] shadow-[0_0_20px_rgba(0,255,102,0.2)]" : "border-[#27272a]"}`} data-testid={`live-card-${it.id}`}>
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="font-bold text-white truncate">{it.name}</div>
            <span className="font-mono text-[10px] text-[#A1A1AA] bg-[#18181b] px-1.5 py-0.5 border border-[#27272a]">[ {sites?.labels?.[it.site] || it.site} ]</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider border ${STATUS_COLORS[it.status] || STATUS_COLORS.IDLE}`}>
              {it.status === "IN_STOCK" && <span className="w-1.5 h-1.5 rounded-full bg-[#00FF66] animate-pulse"/>}
              {it.status}
            </span>
            <span className="text-[10px] text-[#52525B] font-mono truncate">{it.last_message || "—"}</span>
          </div>
          <div className="text-[10px] text-[#52525B] font-mono mt-1">
            {it.last_checked ? `last: ${new Date(it.last_checked).toLocaleTimeString()}` : "not yet polled"}
          </div>
        </div>
      ))}
    </div>
  );
}

export default App;
