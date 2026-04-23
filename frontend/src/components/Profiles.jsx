import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

export default function Profiles({ onChange }) {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);
  const load = async () => { const r = await api.get("/profiles"); setItems(r.data); };
  useEffect(() => { load(); }, []);
  const del = async (id) => { if (!window.confirm("Delete profile?")) return; await api.delete(`/profiles/${id}`); load(); onChange?.(); };

  return (
    <div className="bg-[#121214] border border-[#27272a] rounded-none">
      <div className="flex items-center justify-between p-4 border-b border-[#27272a]">
        <h3 className="text-xs font-black tracking-[0.2em] uppercase text-[#A1A1AA]" style={{fontFamily:"'Chivo', sans-serif"}}>Profiles · {items.length}</h3>
        <button onClick={() => setEditing({})} data-testid="add-profile-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-3 py-1.5 font-bold text-xs flex items-center gap-2"><Plus size={14}/> Add</button>
      </div>
      <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {items.length === 0 && <div className="col-span-full text-[#52525B] text-sm p-4">No profiles. Create one to enable autofill for checkout/auto modes.</div>}
        {items.map((p) => (
          <div key={p.id} className="border border-[#27272a] bg-[#09090b] p-3" data-testid={`profile-${p.id}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="font-bold text-white">{p.label}</div>
              <div className="flex gap-1">
                <button onClick={() => setEditing(p)} className="text-[10px] text-[#A1A1AA] border border-[#27272a] px-2 py-0.5 hover:bg-white/5">EDIT</button>
                <button onClick={() => del(p.id)} className="text-[#FF3B30] p-1 hover:bg-[#FF3B30]/10"><Trash2 size={12}/></button>
              </div>
            </div>
            <div className="text-xs text-[#A1A1AA] space-y-0.5 font-mono">
              <div>{p.first_name} {p.last_name}</div>
              <div>{p.email}</div>
              <div>{p.address1}{p.address2 ? `, ${p.address2}` : ""}</div>
              <div>{p.city}, {p.state} {p.zip}</div>
              <div className="text-[#52525B]">{p.card_number || "no card"}</div>
            </div>
          </div>
        ))}
      </div>
      {editing && <ProfileModal item={editing} onClose={() => { setEditing(null); load(); onChange?.(); }} />}
    </div>
  );
}

function ProfileModal({ item, onClose }) {
  const [f, setF] = useState({
    label: item.label || "", first_name: item.first_name || "", last_name: item.last_name || "",
    email: item.email || "", phone: item.phone || "",
    address1: item.address1 || "", address2: item.address2 || "",
    city: item.city || "", state: item.state || "", zip: item.zip || "", country: item.country || "US",
    card_name: item.card_name || "", card_number: "", card_exp_month: item.card_exp_month || "",
    card_exp_year: item.card_exp_year || "", card_cvv: "",
  });
  const save = async () => {
    try {
      if (item.id) await api.patch(`/profiles/${item.id}`, f);
      else await api.post(`/profiles`, f);
      toast.success("Saved"); onClose();
    } catch (e) { toast.error(String(e.message)); }
  };
  const field = "bg-[#09090b] border border-[#27272a] px-2 py-1.5 text-sm w-full focus:outline-none focus:border-[#007AFF] rounded-none";
  const Lb = ({ name, label, span = 1, type = "text" }) => (
    <label className={`col-span-${span}`}>
      <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider mb-1">{label}</div>
      <input type={type} className={field} value={f[name]} onChange={(e) => setF({ ...f, [name]: e.target.value })} />
    </label>
  );
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <div className="bg-[#121214] border border-[#27272a] w-full max-w-2xl p-6 my-8" onClick={(e) => e.stopPropagation()} data-testid="profile-modal">
        <h3 className="text-lg font-black uppercase mb-4" style={{fontFamily:"'Chivo', sans-serif"}}>{item.id ? "Edit Profile" : "New Profile"}</h3>
        <div className="grid grid-cols-4 gap-3">
          <Lb name="label" label="Label" span={4} />
          <Lb name="first_name" label="First Name" span={2} />
          <Lb name="last_name" label="Last Name" span={2} />
          <Lb name="email" label="Email" span={2} />
          <Lb name="phone" label="Phone" span={2} />
          <Lb name="address1" label="Address 1" span={4} />
          <Lb name="address2" label="Address 2" span={4} />
          <Lb name="city" label="City" span={2} />
          <Lb name="state" label="State" span={1} />
          <Lb name="zip" label="ZIP" span={1} />
          <div className="col-span-4 text-[10px] tracking-[0.2em] uppercase text-[#52525B] border-t border-[#27272a] pt-3 mt-2">Payment (stored locally on your PC)</div>
          <Lb name="card_name" label="Name on Card" span={4} />
          <Lb name="card_number" label={item.id ? "New Card # (leave blank to keep)" : "Card #"} span={2} />
          <Lb name="card_exp_month" label="MM" span={1} />
          <Lb name="card_exp_year" label="YY" span={1} />
          <Lb name="card_cvv" label={item.id ? "New CVV" : "CVV"} span={1} />
        </div>
        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-3 py-1.5 text-xs border border-[#27272a] text-[#A1A1AA] hover:bg-white/5">Cancel</button>
          <button onClick={save} data-testid="save-profile-btn" className="bg-[#007AFF] text-white hover:bg-[#3395FF] px-4 py-1.5 font-bold uppercase text-xs tracking-wider">Save</button>
        </div>
      </div>
    </div>
  );
}
