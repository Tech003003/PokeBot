import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function Settings() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);
  if (!s) return <div className="p-6 text-[#52525B]">Loading…</div>;

  const save = async (patch) => {
    try {
      const r = await api.patch("/settings", patch);
      setS(r.data);
      toast.success("Saved");
    } catch (e) { toast.error(String(e.message)); }
  };

  const field = "bg-[#09090b] border border-[#27272a] px-2 py-1.5 text-sm w-full focus:outline-none focus:border-[#007AFF] rounded-none";

  return (
    <div className="bg-[#121214] border border-[#27272a] rounded-none p-6 space-y-6">
      <div>
        <div className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA] mb-3" style={{fontFamily:"'Chivo', sans-serif"}}>Engine</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Poll Interval (ms)</div>
            <input type="number" min={100} step={50} className={field} value={s.poll_interval_ms} onChange={(e) => setS({ ...s, poll_interval_ms: Number(e.target.value) })} data-testid="poll-interval-input" />
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Jitter (ms)</div>
            <input type="number" min={0} className={field} value={s.jitter_ms} onChange={(e) => setS({ ...s, jitter_ms: Number(e.target.value) })} />
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Concurrent Workers</div>
            <input type="number" min={1} max={20} className={field} value={s.concurrent_workers} onChange={(e) => setS({ ...s, concurrent_workers: Number(e.target.value) })} />
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Brave CDP URL</div>
            <input className={field} value={s.cdp_url} onChange={(e) => setS({ ...s, cdp_url: e.target.value })} />
          </label>
        </div>
      </div>

      <div>
        <div className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA] mb-3" style={{fontFamily:"'Chivo', sans-serif"}}>Notifications</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <label className="md:col-span-3"><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Discord Webhook URL</div>
            <input className={field} placeholder="https://discord.com/api/webhooks/…" value={s.discord_webhook} onChange={(e) => setS({ ...s, discord_webhook: e.target.value })} data-testid="discord-webhook-input" />
          </label>
          <label className="flex items-center gap-2 text-xs text-[#A1A1AA]"><input type="checkbox" checked={s.sound_alerts} onChange={(e) => setS({ ...s, sound_alerts: e.target.checked })} /> Sound alerts</label>
          <label className="flex items-center gap-2 text-xs text-[#A1A1AA]"><input type="checkbox" checked={s.desktop_toasts} onChange={(e) => setS({ ...s, desktop_toasts: e.target.checked })} /> Desktop toasts</label>
        </div>
      </div>

      <div>
        <div className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA] mb-3" style={{fontFamily:"'Chivo', sans-serif"}}>Price Guard</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <label className="flex items-center gap-2 text-xs text-[#A1A1AA]" data-testid="enforce-max-price-toggle">
            <input type="checkbox" checked={s.enforce_max_price ?? true} onChange={(e) => setS({ ...s, enforce_max_price: e.target.checked })} />
            Enforce per-item <span className="font-mono text-[#FFCC00]">Max Price</span>
          </label>
          <label className="flex items-center gap-2 text-xs text-[#A1A1AA]">
            <input type="checkbox" checked={s.strict_price_guard ?? false} onChange={(e) => setS({ ...s, strict_price_guard: e.target.checked })} />
            Strict: skip if price can't be read
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Skip Cooldown (sec)</div>
            <input type="number" min={10} className={field} value={s.price_guard_cooldown_s ?? 300} onChange={(e) => setS({ ...s, price_guard_cooldown_s: Number(e.target.value) })} />
          </label>
        </div>
      </div>

      <div>
        <div className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA] mb-3" style={{fontFamily:"'Chivo', sans-serif"}}>Safety</div>
        <label className="flex items-center gap-2 text-xs text-[#A1A1AA]" data-testid="safety-toggle">
          <input type="checkbox" checked={s.stop_before_place_order} onChange={(e) => setS({ ...s, stop_before_place_order: e.target.checked })} />
          Global kill: stop before <span className="font-mono text-[#FFCC00]">Place Order</span> even in Full Auto mode
        </label>
      </div>

      <div className="flex justify-end">
        <button onClick={() => save(s)} data-testid="save-settings-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-4 py-1.5 font-bold uppercase text-xs tracking-wider">Save Settings</button>
      </div>
    </div>
  );
}
