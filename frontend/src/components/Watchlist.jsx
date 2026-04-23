import React, { useEffect, useState } from "react";
import { api, MODES, STATUS_COLORS } from "@/lib/api";
import { toast } from "sonner";
import { Play, Square, Trash2, Plus, Pencil } from "lucide-react";

export default function Watchlist({ sites, profiles, onChange }) {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    const r = await api.get("/watch");
    setItems(r.data);
  };
  useEffect(() => { load(); const t = setInterval(load, 2000); return () => clearInterval(t); }, []);

  const start = async (id) => { await api.post(`/watch/${id}/start`); toast.success("Started"); load(); onChange?.(); };
  const stop = async (id) => { await api.post(`/watch/${id}/stop`); toast.info("Stopped"); load(); onChange?.(); };
  const del = async (id) => { if (!window.confirm("Delete this watch?")) return; await api.delete(`/watch/${id}`); load(); onChange?.(); };

  return (
    <div className="bg-[#121214] border border-[#27272a] rounded-none">
      <div className="flex items-center justify-between p-4 border-b border-[#27272a]">
        <h3 className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA]" style={{fontFamily:"'Chivo', sans-serif"}}>
          Watchlist · {items.length}
        </h3>
        <button
          onClick={() => setEditing({})}
          data-testid="add-watch-btn"
          className="bg-[#007AFF] text-white hover:bg-[#3395FF] rounded-none px-3 py-1.5 font-bold tracking-wide text-xs flex items-center gap-2"
        >
          <Plus size={14}/> Add
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-black tracking-[0.1em] text-[#A1A1AA] uppercase border-b border-[#27272a] bg-[#09090b]/50">
              <th className="text-left p-3">Product</th>
              <th className="text-left p-3">Site</th>
              <th className="text-left p-3">Mode</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Last Message</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={6} className="p-8 text-center text-[#52525B] text-sm">No watchers yet — click + Add to start.</td></tr>
            )}
            {items.map((it) => (
              <tr key={it.id} className="border-b border-[#27272a]/50 hover:bg-[#18181b]" data-testid={`watch-row-${it.id}`}>
                <td className="p-3">
                  <div className="font-medium text-white">{it.name}</div>
                  <a href={it.url} target="_blank" rel="noreferrer" className="text-[10px] text-[#52525B] hover:text-[#A1A1AA] font-mono">
                    {it.url.slice(0, 50)}{it.url.length > 50 ? "…" : ""}
                  </a>
                </td>
                <td className="p-3">
                  <span className="font-mono text-xs text-[#A1A1AA] bg-[#18181b] px-1.5 py-0.5 border border-[#27272a]">
                    [ {sites?.labels?.[it.site] || it.site.toUpperCase()} ]
                  </span>
                </td>
                <td className="p-3 text-xs text-[#A1A1AA]">{MODES.find((m) => m.id === it.purchase_mode)?.label || it.purchase_mode}</td>
                <td className="p-3">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider border ${STATUS_COLORS[it.status] || STATUS_COLORS.IDLE}`}>
                    {it.status === "IN_STOCK" && <span className="w-1.5 h-1.5 rounded-full bg-[#00FF66] animate-pulse" />}
                    {it.status}
                  </span>
                </td>
                <td className="p-3 text-[11px] text-[#A1A1AA] font-mono max-w-xs truncate">{it.last_message || "—"}</td>
                <td className="p-3">
                  <div className="flex items-center gap-1 justify-end">
                    <button data-testid={`start-watch-${it.id}`} onClick={() => start(it.id)} className="p-1.5 text-[#00FF66] hover:bg-[#00FF66]/10 border border-transparent hover:border-[#00FF66]/30"><Play size={14}/></button>
                    <button data-testid={`stop-watch-${it.id}`} onClick={() => stop(it.id)} className="p-1.5 text-[#FFCC00] hover:bg-[#FFCC00]/10 border border-transparent hover:border-[#FFCC00]/30"><Square size={14}/></button>
                    <button data-testid={`edit-watch-${it.id}`} onClick={() => setEditing(it)} className="p-1.5 text-[#A1A1AA] hover:bg-white/5 border border-transparent hover:border-[#27272a]"><Pencil size={14}/></button>
                    <button data-testid={`delete-watch-${it.id}`} onClick={() => del(it.id)} className="p-1.5 text-[#FF3B30] hover:bg-[#FF3B30]/10 border border-transparent hover:border-[#FF3B30]/30"><Trash2 size={14}/></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && <WatchModal item={editing} sites={sites} profiles={profiles} onClose={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function WatchModal({ item, sites, profiles, onClose }) {
  const [f, setF] = useState({
    name: item.name || "",
    site: item.site || (sites?.sites?.[0] || "walmart"),
    url: item.url || "",
    purchase_mode: item.purchase_mode || "cart",
    priority: item.priority ?? 5,
    active: item.active ?? true,
    max_price: item.max_price ?? "",
    quantity: item.quantity ?? 1,
    profile_id: item.profile_id || "",
  });
  const save = async () => {
    try {
      const body = { ...f, max_price: f.max_price === "" ? null : Number(f.max_price), quantity: Number(f.quantity), priority: Number(f.priority), active: Boolean(f.active), profile_id: f.profile_id || null };
      if (item.id) await api.patch(`/watch/${item.id}`, body);
      else await api.post(`/watch`, body);
      toast.success("Saved");
      onClose();
    } catch (e) { toast.error(String(e.response?.data?.detail || e.message)); }
  };
  const field = "bg-[#09090b] border border-[#27272a] px-2 py-1.5 text-sm w-full focus:outline-none focus:border-[#007AFF] rounded-none";
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#121214] border border-[#27272a] w-full max-w-xl p-6" onClick={(e) => e.stopPropagation()} data-testid="watch-modal">
        <h3 className="text-lg font-black uppercase tracking-tight mb-4" style={{fontFamily:"'Chivo', sans-serif"}}>{item.id ? "Edit Watch" : "New Watch"}</h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2"><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Name</div><input data-testid="watch-name-input" className={field} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <label className="col-span-2"><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">URL</div><input data-testid="watch-url-input" className={field} value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} /></label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Site</div>
            <select data-testid="watch-site-select" className={field} value={f.site} onChange={(e) => setF({ ...f, site: e.target.value })}>
              {sites?.sites?.map((s) => <option key={s} value={s}>{sites.labels[s]} — {s}</option>)}
            </select>
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Mode</div>
            <select data-testid="watch-mode-select" className={field} value={f.purchase_mode} onChange={(e) => setF({ ...f, purchase_mode: e.target.value })}>
              {MODES.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
            </select>
          </label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Priority (1-10)</div><input className={field} type="number" min={1} max={10} value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })} /></label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Quantity</div><input className={field} type="number" min={1} value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Max Price ($)</div><input className={field} type="number" step="0.01" value={f.max_price} onChange={(e) => setF({ ...f, max_price: e.target.value })} /></label>
          <label><div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Profile</div>
            <select className={field} value={f.profile_id} onChange={(e) => setF({ ...f, profile_id: e.target.value })}>
              <option value="">— none —</option>
              {profiles?.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
          </label>
          <label className="col-span-2 flex items-center gap-2"><input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} /> <span className="text-xs text-[#A1A1AA]">Active (included in Start All)</span></label>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-3 py-1.5 text-xs border border-[#27272a] text-[#A1A1AA] hover:bg-white/5">Cancel</button>
          <button onClick={save} data-testid="save-watch-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-4 py-1.5 font-bold uppercase text-xs tracking-wider">Save</button>
        </div>
      </div>
    </div>
  );
}
