import React, { useEffect, useState } from "react";
import { api, MODES } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Zap } from "lucide-react";

function Countdown({ target }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(t); }, []);
  const diff = Math.max(0, new Date(target).getTime() - now);
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  return (
    <div className="font-mono text-[#FFCC00] animate-[pulse_1s_ease-in-out_infinite] tracking-wider">
      {d > 0 ? `${d}d ` : ""}{String(h).padStart(2, "0")}:{String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
    </div>
  );
}

export default function Drops({ sites, profiles }) {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const load = async () => { const r = await api.get("/drops"); setItems(r.data); };
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);
  const arm = async (id) => { await api.post(`/drops/${id}/arm`); toast.success("Armed"); load(); };
  const cancel = async (id) => { await api.post(`/drops/${id}/cancel`); toast.info("Cancelled"); load(); };
  const del = async (id) => { await api.delete(`/drops/${id}`); load(); };

  return (
    <div className="bg-[#121214] border border-[#27272a] rounded-none">
      <div className="flex items-center justify-between p-4 border-b border-[#27272a]">
        <h3 className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA]" style={{fontFamily:"'Chivo', sans-serif"}}>Drop Scheduler · {items.length}</h3>
        <button onClick={() => setEditing({})} data-testid="add-drop-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-3 py-1.5 font-bold text-xs flex items-center gap-2"><Plus size={14}/> Schedule</button>
      </div>
      <div className="p-4 space-y-3">
        {items.length === 0 && <div className="text-[#52525B] text-sm">No drops scheduled. Perfect for Walmart 9PM drops — schedule, arm, and let the bot blast URLs when it's time.</div>}
        {items.map((d) => (
          <div key={d.id} className="border border-[#27272a] bg-[#09090b] p-3" data-testid={`drop-${d.id}`}>
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <div className="font-bold text-white">{d.name}</div>
                <div className="text-[10px] text-[#52525B] font-mono">
                  [{sites?.labels?.[d.site] || d.site}] · {new Date(d.run_at).toLocaleString()} · {d.urls.length} URL(s) · {MODES.find((m) => m.id === d.purchase_mode)?.label}
                </div>
              </div>
              <Countdown target={d.run_at} />
              <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 border border-[#27272a] text-[#A1A1AA]">{d.status}</span>
              <div className="flex gap-1">
                <button onClick={() => arm(d.id)} data-testid={`arm-drop-${d.id}`} className="border border-[#00FF66]/50 text-[#00FF66] hover:bg-[#00FF66]/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1"><Zap size={11}/> Arm</button>
                <button onClick={() => cancel(d.id)} className="border border-[#27272a] text-[#A1A1AA] hover:bg-white/5 px-2 py-1 text-[10px] font-bold uppercase tracking-wider">Cancel</button>
                <button onClick={() => del(d.id)} className="text-[#FF3B30] p-1 hover:bg-[#FF3B30]/10"><Trash2 size={14}/></button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {editing && <DropModal item={editing} sites={sites} profiles={profiles} onClose={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function DropModal({ item, sites, profiles, onClose }) {
  const defaultRunAt = () => {
    const d = new Date(Date.now() + 5 * 60000);
    d.setSeconds(0, 0);
    const tzoff = d.getTimezoneOffset() * 60000;
    return new Date(d.getTime() - tzoff).toISOString().slice(0, 16);
  };
  const [f, setF] = useState({
    name: item.name || "", site: item.site || (sites?.sites?.[0] || "walmart"),
    run_at_local: item.run_at ? new Date(item.run_at).toISOString().slice(0, 16) : defaultRunAt(),
    urls_text: (item.urls || []).join("\n"),
    queue_handling: item.queue_handling ?? true,
    blast_mode: item.blast_mode ?? true,
    purchase_mode: item.purchase_mode || "cart",
    profile_id: item.profile_id || "",
  });
  const save = async () => {
    const urls = f.urls_text.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    if (!urls.length) { toast.error("Add at least one URL"); return; }
    const runAtISO = new Date(f.run_at_local).toISOString();
    try {
      await api.post("/drops", {
        name: f.name, site: f.site, run_at: runAtISO, urls,
        queue_handling: !!f.queue_handling, blast_mode: !!f.blast_mode,
        purchase_mode: f.purchase_mode, profile_id: f.profile_id || null,
      });
      toast.success("Drop scheduled"); onClose();
    } catch (e) { toast.error(String(e.response?.data?.detail || e.message)); }
  };
  const field = "bg-[#09090b] border border-[#27272a] px-2 py-1.5 text-sm w-full focus:outline-none focus:border-[#007AFF] rounded-none";
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#121214] border border-[#27272a] w-full max-w-xl p-6" onClick={(e) => e.stopPropagation()} data-testid="drop-modal">
        <h3 className="text-lg font-black uppercase mb-4" style={{fontFamily:"'Chivo', sans-serif"}}>Schedule Drop</h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2"><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Name</div><input data-testid="drop-name-input" className={field} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Site</div>
            <select data-testid="drop-site-select" className={field} value={f.site} onChange={(e) => setF({ ...f, site: e.target.value })}>
              {sites?.sites?.map((s) => <option key={s} value={s}>{sites.labels[s]}</option>)}
            </select>
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Run At (local)</div>
            <input data-testid="drop-runat-input" type="datetime-local" className={field} value={f.run_at_local} onChange={(e) => setF({ ...f, run_at_local: e.target.value })} />
          </label>
          <label className="col-span-2"><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">URLs (one per line)</div>
            <textarea data-testid="drop-urls-input" rows={5} className={field} value={f.urls_text} onChange={(e) => setF({ ...f, urls_text: e.target.value })} />
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Mode</div>
            <select className={field} value={f.purchase_mode} onChange={(e) => setF({ ...f, purchase_mode: e.target.value })}>
              {MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
            </select>
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase mb-1">Profile</div>
            <select className={field} value={f.profile_id} onChange={(e) => setF({ ...f, profile_id: e.target.value })}>
              <option value="">— none —</option>
              {profiles?.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2 col-span-1"><input type="checkbox" checked={f.queue_handling} onChange={(e) => setF({ ...f, queue_handling: e.target.checked })} /> <span className="text-xs text-[#A1A1AA]">Auto-advance queue</span></label>
          <label className="flex items-center gap-2 col-span-1"><input type="checkbox" checked={f.blast_mode} onChange={(e) => setF({ ...f, blast_mode: e.target.checked })} /> <span className="text-xs text-[#A1A1AA]">Blast all URLs in parallel</span></label>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-3 py-1.5 text-xs border border-[#27272a] text-[#A1A1AA] hover:bg-white/5">Cancel</button>
          <button onClick={save} data-testid="save-drop-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-4 py-1.5 font-bold uppercase text-xs tracking-wider">Schedule</button>
        </div>
      </div>
    </div>
  );
}
