import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

const MODES = [
  { id: "monitor", label: "Monitor" },
  { id: "cart", label: "Add to cart" },
  { id: "checkout", label: "Checkout" },
  { id: "auto", label: "Full auto" },
];

export default function Settings() {
  const [s, setS] = useState(null);
  const [dcStatus, setDcStatus] = useState({ connected: false, running: false });
  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);
  useEffect(() => {
    const t = setInterval(() => api.get("/discord/status").then((r) => setDcStatus(r.data)).catch(()=>{}), 3000);
    return () => clearInterval(t);
  }, []);
  if (!s) return <div className="p-6 text-[#52525B]">Loading…</div>;

  const save = async (patch) => {
    try {
      const r = await api.patch("/settings", patch);
      setS(r.data);
      toast.success("Saved");
    } catch (e) { toast.error(String(e.message)); }
  };

  const rules = s.discord_channel_rules || {};
  const setRules = (next) => setS({ ...s, discord_channel_rules: next });
  const addRule = () => {
    const cid = prompt("Channel ID to watch (right-click the channel in Discord → Copy Channel ID):");
    if (!cid || !/^\d{10,25}$/.test(cid.trim())) { toast.error("Not a valid Discord channel ID"); return; }
    if (rules[cid.trim()]) { toast.info("Already added"); return; }
    setRules({ ...rules, [cid.trim()]: { action: "monitor", priority: 5, max_price: "", profile_id: "", auto_start: true } });
  };
  const updateRule = (cid, patch) => setRules({ ...rules, [cid]: { ...rules[cid], ...patch } });
  const deleteRule = (cid) => { const n = { ...rules }; delete n[cid]; setRules(n); };

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
          <label title="Do a soft reload every N polls (instead of full navigation every poll). Higher = faster polling, lower = fresher state."><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Reload Every (polls)</div>
            <input type="number" min={1} max={200} className={field} value={s.reload_every_n_polls ?? 10} onChange={(e) => setS({ ...s, reload_every_n_polls: Number(e.target.value) })} data-testid="reload-every-input" />
          </label>
          <label title="Max times to retry the Add-to-Cart click before giving up. 0 = never give up."><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">ATC Retry Cap (0 = inf)</div>
            <input type="number" min={0} className={field} value={s.atc_max_retries ?? 0} onChange={(e) => setS({ ...s, atc_max_retries: Number(e.target.value) })} data-testid="atc-retries-input" />
          </label>
        </div>
      </div>

      <div>
        <div className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA] mb-3" style={{fontFamily:"'Chivo', sans-serif"}}>Notifications</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <label className="md:col-span-3"><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Discord Webhook URL (for alerts)</div>
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
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA]" style={{fontFamily:"'Chivo', sans-serif"}}>Discord Auto-Import</div>
          <div className="flex items-center gap-2 text-[10px] font-mono">
            <span className={`w-2 h-2 rounded-full ${dcStatus.connected ? "bg-[#00FF66] animate-pulse" : "bg-[#52525B]"}`} />
            <span className={dcStatus.connected ? "text-[#00FF66]" : "text-[#52525B]"}>
              {dcStatus.connected ? "BOT ONLINE" : dcStatus.running ? "CONNECTING…" : "OFFLINE"}
            </span>
          </div>
        </div>
        <div className="text-[11px] text-[#52525B] mb-3 leading-relaxed">
          Auto-add items to the Watchlist when a Discord bot posts a drop alert in a channel you're watching.
          <br/>⚠ You cannot add this bot to servers you don't own (e.g. PokePings). Instead: create your own
          Discord server, invite this bot, and use Discord's <span className="text-[#FFCC00]">"Follow"</span> feature
          on the source's announcement channels to mirror their alerts into yours.
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
          <label className="md:col-span-2"><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Bot Token</div>
            <input type="password" placeholder="MTIzNDU2Nzg5MA.…" className={field} value={s.discord_bot_token || ""} onChange={(e) => setS({ ...s, discord_bot_token: e.target.value })} data-testid="discord-token-input" />
          </label>
          <label className="flex items-center gap-2 text-xs text-[#A1A1AA] mt-6">
            <input type="checkbox" checked={!!s.discord_enabled} onChange={(e) => setS({ ...s, discord_enabled: e.target.checked })} data-testid="discord-enable-toggle" />
            Enable Discord listener
          </label>
        </div>

        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider">Channel Rules · {Object.keys(rules).length}</div>
            <button onClick={addRule} data-testid="add-channel-rule-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-2 py-1 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1"><Plus size={12}/> Add channel</button>
          </div>
          {Object.keys(rules).length === 0 && <div className="text-[11px] text-[#52525B] border border-dashed border-[#27272a] p-3">No channels configured. Add your own server's channel IDs where mirrored drop-alerts land.</div>}
          <div className="space-y-2">
            {Object.entries(rules).map(([cid, rule]) => (
              <div key={cid} className="border border-[#27272a] bg-[#09090b] p-2 grid grid-cols-12 gap-2 items-center" data-testid={`rule-${cid}`}>
                <div className="col-span-3 font-mono text-[11px] text-[#A1A1AA] truncate" title={cid}>{cid}</div>
                <select className={`${field} col-span-2`} value={rule.action} onChange={(e) => updateRule(cid, { action: e.target.value })}>
                  {MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
                <input type="number" min={1} max={10} className={`${field} col-span-1`} placeholder="Pri" value={rule.priority ?? 5} onChange={(e) => updateRule(cid, { priority: Number(e.target.value) })} />
                <input type="number" step="0.01" className={`${field} col-span-2`} placeholder="Max $" value={rule.max_price ?? ""} onChange={(e) => updateRule(cid, { max_price: e.target.value === "" ? null : Number(e.target.value) })} />
                <label className="col-span-3 flex items-center gap-1 text-[11px] text-[#A1A1AA]">
                  <input type="checkbox" checked={rule.auto_start ?? true} onChange={(e) => updateRule(cid, { auto_start: e.target.checked })} /> auto-start
                </label>
                <button onClick={() => deleteRule(cid)} className="col-span-1 text-[#FF3B30] p-1 hover:bg-[#FF3B30]/10 flex justify-center"><Trash2 size={13}/></button>
              </div>
            ))}
          </div>
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
