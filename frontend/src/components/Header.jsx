import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plug, Unplug, Power, PowerOff, Rocket } from "lucide-react";

function LogoMark() {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="w-8 h-8 bg-[#00FF66] flex items-center justify-center">
        <Rocket size={18} className="text-black" />
      </div>
    );
  }
  return (
    <img
      src="/logo.png"
      alt="TechBot"
      className="w-8 h-8 object-contain"
      onError={() => setFailed(true)}
      data-testid="app-logo"
    />
  );
}

export default function Header({ status, refresh }) {
  const [cdp, setCdp] = useState(status?.settings?.cdp_url || "http://127.0.0.1:9222");

  useEffect(() => {
    if (status?.settings?.cdp_url) setCdp(status.settings.cdp_url);
  }, [status?.settings?.cdp_url]);

  const connect = async () => {
    try {
      const r = await api.post("/brave/connect", { cdp_url: cdp });
      if (r.data.connected) toast.success("Brave connected");
      else toast.error(`Connect failed: ${r.data.message?.slice(0, 80)}`);
      refresh();
    } catch (e) { toast.error(String(e.message)); }
  };

  const disconnect = async () => {
    await api.post("/brave/disconnect");
    toast.info("Disconnected");
    refresh();
  };

  const startAll = async () => {
    const r = await api.post("/watch/start-all");
    toast.success(`Started ${r.data.started} watcher(s)`);
    refresh();
  };
  const stopAll = async () => {
    const r = await api.post("/watch/stop-all");
    toast.info(`Stopped ${r.data.stopped}`);
    refresh();
  };

  const connected = status?.connected;
  const running = status?.running;

  return (
    <header
      className="backdrop-blur-xl bg-[#09090b]/80 border-b border-[#27272a] sticky top-0 z-50 px-4 sm:px-8 py-3"
      data-testid="app-header"
    >
      <div className="max-w-[1600px] mx-auto flex items-center gap-6 flex-wrap">
        <div className="flex items-center gap-3">
          <LogoMark />
          <div>
            <div className="font-black tracking-[0.15em] text-sm uppercase" style={{fontFamily:"'Chivo', sans-serif"}}>
              TechBot
            </div>
            <div className="text-[10px] text-[#52525B] tracking-[0.2em] uppercase -mt-0.5">Command Center</div>
          </div>
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-2">
          <input
            value={cdp}
            onChange={(e) => setCdp(e.target.value)}
            data-testid="cdp-url-input"
            className="bg-[#121214] border border-[#27272a] text-xs font-mono px-2 py-1.5 w-56 focus:outline-none focus:border-[#FF6B00] rounded-none"
            placeholder="http://127.0.0.1:9222"
          />
          {connected ? (
            <button onClick={disconnect} data-testid="brave-disconnect-btn"
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold uppercase tracking-wider border border-[#FF6B00] bg-[#FF6B00]/10 text-[#FF6B00] hover:bg-[#FF6B00]/20 rounded-none">
              <Unplug size={14}/> Brave · Live
            </button>
          ) : (
            <button onClick={connect} data-testid="brave-connect-btn"
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-bold uppercase tracking-wider border border-[#FF6B00] text-[#FF6B00] hover:bg-[#FF6B00]/10 rounded-none">
              <Plug size={14}/> Connect Brave
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={startAll}
            data-testid="start-all-btn"
            className="bg-[#00FF66]/10 text-[#00FF66] border border-[#00FF66]/50 hover:bg-[#00FF66]/20 rounded-none px-4 py-1.5 font-bold uppercase text-xs tracking-wider flex items-center gap-2"
          >
            <Power size={14}/> Start All
          </button>
          <button
            onClick={stopAll}
            data-testid="stop-all-btn"
            className="bg-[#FF3B30] text-white hover:bg-[#FF3B30]/90 rounded-none px-4 py-1.5 font-bold uppercase text-xs tracking-wider flex items-center gap-2"
          >
            <PowerOff size={14}/> Stop All
          </button>
        </div>

        {running && (
          <div className="text-xs text-[#00FF66] font-mono flex items-center gap-2" data-testid="running-indicator">
            <span className="inline-block w-2 h-2 bg-[#00FF66] rounded-full animate-pulse" />
            ENGINE · LIVE
          </div>
        )}
      </div>
    </header>
  );
}
