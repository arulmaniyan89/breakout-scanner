import React, { useState } from "react";
import { Bell, Mail, Send, MessageCircle, Check } from "lucide-react";
import toast from "react-hot-toast";
import { subscribeAlerts } from "../utils/api";

const STRENGTH_OPTIONS = [
  { value: "STRONG", label: "🟢 Strong only", desc: "All 4 criteria met" },
  { value: "MODERATE", label: "🟡 Moderate & above", desc: "3+ criteria met" },
  { value: "WATCHLIST", label: "🔵 All breakouts", desc: "2+ criteria met" },
];

export default function Alerts() {
  const [form, setForm] = useState({
    email: "",
    telegram_chat_id: "",
    whatsapp_number: "",
    min_strength: "MODERATE",
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email && !form.telegram_chat_id && !form.whatsapp_number) {
      toast.error("Enter at least one contact method");
      return;
    }
    setLoading(true);
    try {
      await subscribeAlerts(form);
      setSubmitted(true);
      toast.success("Subscribed successfully!");
    } catch {
      // Demo mode
      setSubmitted(true);
      toast.success("Subscribed (demo mode)");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center">
        <div className="w-16 h-16 bg-emerald-900/30 border border-emerald-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <Check className="w-8 h-8 text-emerald-400" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">You're subscribed!</h2>
        <p className="text-gray-400 text-sm">
          You'll receive breakout alerts every weekday at 8:45 AM IST.
        </p>
        <button
          onClick={() => setSubmitted(false)}
          className="mt-6 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition"
        >
          Update Preferences
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Alert Setup</h1>
        <p className="text-gray-400 text-sm mt-0.5">
          Get notified at 8:45 AM IST every weekday when new breakouts are detected.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Email */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Mail className="w-4 h-4 text-blue-400" /> Email Digest
          </div>
          <input
            type="email"
            placeholder="your@email.com"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                       text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          />
          <p className="text-xs text-gray-500">
            Receive a morning digest with the top 10 breakout stocks and an HTML table.
          </p>
        </div>

        {/* Telegram */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Send className="w-4 h-4 text-sky-400" /> Telegram Bot
          </div>
          <input
            type="text"
            placeholder="Telegram Chat ID (e.g. 123456789)"
            value={form.telegram_chat_id}
            onChange={(e) => set("telegram_chat_id", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                       text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          />
          <div className="text-xs text-gray-500 space-y-1">
            <p>1. Start a chat with your bot on Telegram</p>
            <p>2. Send <code className="bg-gray-800 px-1 rounded">/start</code> to get your Chat ID</p>
            <p>3. Use <code className="bg-gray-800 px-1 rounded">/breakouts</code> anytime for instant results</p>
          </div>
        </div>

        {/* WhatsApp */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <MessageCircle className="w-4 h-4 text-green-400" /> WhatsApp (via Twilio)
          </div>
          <input
            type="tel"
            placeholder="+919876543210"
            value={form.whatsapp_number}
            onChange={(e) => set("whatsapp_number", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm
                       text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
          />
          <p className="text-xs text-gray-500">
            Requires Twilio credentials configured on the backend. Include country code.
          </p>
        </div>

        {/* Minimum strength */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Bell className="w-4 h-4 text-yellow-400" /> Minimum Breakout Strength
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {STRENGTH_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => set("min_strength", opt.value)}
                className={`p-3 rounded-lg border text-left transition
                  ${form.min_strength === opt.value
                    ? "border-blue-500 bg-blue-900/30 text-white"
                    : "border-gray-700 bg-gray-800 text-gray-400 hover:text-gray-200"}`}
              >
                <div className="text-sm font-medium">{opt.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold
                     rounded-xl transition text-sm"
        >
          {loading ? "Subscribing…" : "Subscribe to Alerts"}
        </button>
      </form>
    </div>
  );
}
