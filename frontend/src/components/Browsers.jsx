import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Chrome, Plug, Unplug, Plus, Trash2, Rocket, Pencil, Star } from "lucide-react";

// Browsers tab: manage N Brave instances. Each row maps 1:1 to a Brave process
// you launch on your PC (different port + user-data-dir = different sign-in).
// Watchlist items and Drops can then be pinned to a specific browser.
export default function Browsers({ onChange }) {
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    try {
      const r = await api.get("/browsers");
      setRows(r.data);
    } catch (e) {
      console.error(e);
    }
  };
  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const launch = async (id) => {
    try {
      const r = await api.post(`/browsers/${id}/launch`);
      toast.success(`Brave launched on port ${r.data.port}. Sign in, then Connect.`);
      // Auto-connect a few seconds later so CDP has time to come up.
      setTimeout(async () => {
        try {
          const c = await api.post(`/browsers/${id}/connect`);
          if (c.data.connected) {
            toast.success("Connected");
            load();
            onChange?.();
          }
        } catch {}
      }, 3500);
    } catch (e) {
      toast.error(String(e.response?.data?.detail || e.message));
    }
  };

  const connect = async (id) => {
    const r = await api.post(`/browsers/${id}/connect`);
    if (r.data.connected) toast.success("Connected");
    else toast.error(`Connect failed: ${(r.data.message || "").slice(0, 80)}`);
    load();
    onChange?.();
  };

  const disconnect = async (id) => {
    await api.post(`/browsers/${id}/disconnect`);
    toast.info("Disconnected");
    load();
    onChange?.();
  };

  const del = async (row) => {
    if (!window.confirm(`Delete browser "${row.name}"? Items pinned to it will fall back to the default.`))
      return;
    await api.delete(`/browsers/${row.id}`);
    load();
    onChange?.();
  };

  return (
    <div className="bg-[#121214] border border-[#27272a] rounded-none" data-testid="browsers-panel">
      <div className="flex items-center justify-between p-4 border-b border-[#27272a]">
        <h3
          className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA]"
          style={{ fontFamily: "'Chivo', sans-serif" }}
        >
          Browsers · {rows.length}
        </h3>
        <button
          onClick={() => setEditing({})}
          data-testid="add-browser-btn"
          className="bg-[#007AFF] text-white hover:bg-[#3395FF] rounded-none px-3 py-1.5 font-bold tracking-wide text-xs flex items-center gap-2"
        >
          <Plus size={14} /> Add Proxy Browser
        </button>
      </div>

      <div className="p-4 text-[11px] text-[#A1A1AA] bg-[#0f0f11] border-b border-[#27272a] leading-relaxed">
        Each row is a separate Brave instance with its own sign-ins / cookies. Pick a unique
        <span className="text-white font-mono px-1">CDP port</span> and
        <span className="text-white font-mono px-1">user-data-dir</span> per row, click
        <span className="text-[#FF6B00] font-bold px-1">Launch</span> to open it, then
        <span className="text-[#00FF66] font-bold px-1">Connect</span> to attach. Watchlist items and
        Drops can target a specific browser (or stay on Default).
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-black tracking-[0.1em] text-[#A1A1AA] uppercase border-b border-[#27272a] bg-[#09090b]/50">
              <th className="text-left p-3">Name</th>
              <th className="text-left p-3">CDP URL</th>
              <th className="text-left p-3">Profile Dir</th>
              <th className="text-left p-3">Proxy</th>
              <th className="text-left p-3">Workers</th>
              <th className="text-left p-3">Status</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-[#52525B] text-sm">
                  No browsers yet — click + Add Proxy Browser to start.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr
                key={r.id}
                className="border-b border-[#27272a]/50 hover:bg-[#18181b]"
                data-testid={`browser-row-${r.id}`}
              >
                <td className="p-3">
                  <div className="font-medium text-white flex items-center gap-2">
                    {r.name}
                    {r.is_default ? (
                      <span
                        title="Default browser (used when an item doesn't pin one)"
                        className="text-[9px] text-[#FFCC00] border border-[#FFCC00]/40 px-1"
                      >
                        <Star size={10} className="inline -mt-0.5 mr-0.5" /> DEFAULT
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="p-3 font-mono text-[11px] text-[#A1A1AA]">{r.cdp_url}</td>
                <td className="p-3 font-mono text-[11px] text-[#A1A1AA] max-w-[220px] truncate">
                  {r.user_data_dir || <span className="text-[#52525B]">auto</span>}
                </td>
                <td className="p-3 font-mono text-[11px] text-[#A1A1AA] max-w-[160px] truncate">
                  {r.proxy || <span className="text-[#52525B]">—</span>}
                </td>
                <td className="p-3 text-xs text-[#A1A1AA]">
                  {r.max_workers === 0 ? (
                    <span className="text-[#52525B]">global</span>
                  ) : (
                    <span className="font-mono text-white">{r.max_workers}</span>
                  )}
                </td>
                <td className="p-3">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider border ${
                      r.connected
                        ? "text-[#00FF66] border-[#00FF66]/40 bg-[#00FF66]/10"
                        : "text-[#52525B] border-[#27272a]"
                    }`}
                  >
                    {r.connected && <span className="w-1.5 h-1.5 rounded-full bg-[#00FF66] animate-pulse" />}
                    {r.connected ? "LIVE" : "OFFLINE"}
                  </span>
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-1 justify-end">
                    <button
                      data-testid={`launch-browser-${r.id}`}
                      title="Launch Brave with this port + profile dir"
                      onClick={() => launch(r.id)}
                      className="p-1.5 text-[#FF6B00] hover:bg-[#FF6B00]/10 border border-transparent hover:border-[#FF6B00]/30"
                    >
                      <Rocket size={14} />
                    </button>
                    {r.connected ? (
                      <button
                        data-testid={`disconnect-browser-${r.id}`}
                        onClick={() => disconnect(r.id)}
                        className="p-1.5 text-[#FF3B30] hover:bg-[#FF3B30]/10 border border-transparent hover:border-[#FF3B30]/30"
                      >
                        <Unplug size={14} />
                      </button>
                    ) : (
                      <button
                        data-testid={`connect-browser-${r.id}`}
                        onClick={() => connect(r.id)}
                        className="p-1.5 text-[#00FF66] hover:bg-[#00FF66]/10 border border-transparent hover:border-[#00FF66]/30"
                      >
                        <Plug size={14} />
                      </button>
                    )}
                    <button
                      data-testid={`edit-browser-${r.id}`}
                      onClick={() => setEditing(r)}
                      className="p-1.5 text-[#A1A1AA] hover:bg-white/5 border border-transparent hover:border-[#27272a]"
                    >
                      <Pencil size={14} />
                    </button>
                    {!r.is_default && (
                      <button
                        data-testid={`delete-browser-${r.id}`}
                        onClick={() => del(r)}
                        className="p-1.5 text-[#FF3B30] hover:bg-[#FF3B30]/10 border border-transparent hover:border-[#FF3B30]/30"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <BrowserModal
          row={editing}
          existing={rows}
          onClose={() => {
            setEditing(null);
            load();
            onChange?.();
          }}
        />
      )}
    </div>
  );
}

function BrowserModal({ row, existing, onClose }) {
  // Suggest a free port when creating a new row: highest used + 1 (start at 9222).
  const nextPort = () => {
    const used = existing
      .map((r) => {
        const m = (r.cdp_url || "").match(/:(\d+)/);
        return m ? parseInt(m[1], 10) : 0;
      })
      .filter(Boolean);
    const max = used.length ? Math.max(...used) : 9221;
    return max + 1;
  };
  const defaultCdp = row.id ? row.cdp_url : `http://127.0.0.1:${nextPort()}`;
  const [f, setF] = useState({
    name: row.name || "",
    cdp_url: defaultCdp,
    user_data_dir: row.user_data_dir || "",
    proxy: row.proxy || "",
    max_workers: row.max_workers ?? 0,
    is_default: !!row.is_default,
  });
  const save = async () => {
    try {
      const body = {
        ...f,
        max_workers: Number(f.max_workers) || 0,
      };
      if (row.id) await api.patch(`/browsers/${row.id}`, body);
      else await api.post(`/browsers`, body);
      toast.success("Saved");
      onClose();
    } catch (e) {
      toast.error(String(e.response?.data?.detail || e.message));
    }
  };
  const field =
    "bg-[#09090b] border border-[#27272a] px-2 py-1.5 text-sm w-full focus:outline-none focus:border-[#007AFF] rounded-none";
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-[#121214] border border-[#27272a] w-full max-w-xl p-6"
        onClick={(e) => e.stopPropagation()}
        data-testid="browser-modal"
      >
        <h3
          className="text-lg font-black uppercase tracking-tight mb-4 flex items-center gap-2"
          style={{ fontFamily: "'Chivo', sans-serif" }}
        >
          <Chrome size={18} /> {row.id ? "Edit Browser" : "New Proxy Browser"}
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2">
            <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">Name</div>
            <input
              data-testid="browser-name-input"
              className={field}
              value={f.name}
              onChange={(e) => setF({ ...f, name: e.target.value })}
              placeholder="Account A"
            />
          </label>
          <label className="col-span-2">
            <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">CDP URL (must use a unique port per browser)</div>
            <input
              data-testid="browser-cdp-input"
              className={field}
              value={f.cdp_url}
              onChange={(e) => setF({ ...f, cdp_url: e.target.value })}
            />
          </label>
          <label className="col-span-2">
            <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">
              User-data-dir (Windows path, leave blank for auto)
            </div>
            <input
              data-testid="browser-profile-input"
              className={field}
              value={f.user_data_dir}
              onChange={(e) => setF({ ...f, user_data_dir: e.target.value })}
              placeholder="C:\\Users\\You\\TechBotBrave_A"
            />
          </label>
          <label className="col-span-2">
            <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">
              Proxy (optional — passed to Brave as --proxy-server)
            </div>
            <input
              data-testid="browser-proxy-input"
              className={field}
              value={f.proxy}
              onChange={(e) => setF({ ...f, proxy: e.target.value })}
              placeholder="http://user:pass@host:port  or  socks5://host:port"
            />
          </label>
          <label>
            <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">
              Max workers (0 = use global)
            </div>
            <input
              data-testid="browser-maxworkers-input"
              type="number"
              min={0}
              max={50}
              className={field}
              value={f.max_workers}
              onChange={(e) => setF({ ...f, max_workers: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-2 mt-5">
            <input
              type="checkbox"
              data-testid="browser-default-checkbox"
              checked={f.is_default}
              onChange={(e) => setF({ ...f, is_default: e.target.checked })}
            />
            <span className="text-xs text-[#A1A1AA]">Default browser (fallback for items without a pin)</span>
          </label>
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-3 py-1.5 text-xs border border-[#27272a] text-[#A1A1AA] hover:bg-white/5">
            Cancel
          </button>
          <button
            onClick={save}
            data-testid="save-browser-btn"
            className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-4 py-1.5 font-bold uppercase text-xs tracking-wider"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
