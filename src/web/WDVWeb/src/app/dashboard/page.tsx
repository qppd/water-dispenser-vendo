"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function DashboardPage() {
  const { firebaseUser, userProfile, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !firebaseUser) {
      router.replace("/login");
    }
  }, [firebaseUser, loading, router]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-aqua border-t-transparent" />
      </main>
    );
  }

  if (!firebaseUser) return null;

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  /* ── No linked kiosk account ──────────────────────────────────────── */
  if (!userProfile) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-lg rounded-2xl border-2 border-warning bg-white p-8 text-center shadow-lg">
          <h2 className="mb-2 text-xl font-bold text-warning">
            No Kiosk Account Found
          </h2>
          <p className="mb-1 text-sm text-steel">Signed in as:</p>
          <p className="mb-4 text-sm font-medium">{firebaseUser.email}</p>
          <p className="mb-6 text-sm text-steel">
            Your email is not linked to any AquaSmart kiosk account yet.
            Please register at the kiosk first, then your balance will
            appear here automatically.
          </p>
          <button
            onClick={handleLogout}
            className="rounded-lg bg-steel px-6 py-2 text-sm font-bold text-white transition hover:bg-steel/80"
          >
            Sign Out
          </button>
        </div>
      </main>
    );
  }

  /* ── Dashboard with linked kiosk account ──────────────────────────── */
  return (
    <main className="flex min-h-screen flex-col items-center px-4 pt-10">
      {/* ── Top bar ─────────────────────────────────────────────────── */}
      <div className="mb-8 flex w-full max-w-2xl items-center justify-between">
        <h1 className="text-2xl font-bold text-dark-blue">
          💧 AquaSmart
        </h1>
        <button
          onClick={handleLogout}
          className="rounded-lg bg-steel px-4 py-2 text-xs font-bold text-white transition hover:bg-steel/80"
        >
          Sign Out
        </button>
      </div>

      {/* ── Credit card ─────────────────────────────────────────────── */}
      <div className="mb-6 w-full max-w-2xl rounded-2xl bg-gradient-to-br from-dark-blue to-sidebar-bg p-8 text-white shadow-xl">
        <p className="mb-1 text-sm opacity-80">Credit Balance</p>
        <p className="text-6xl font-bold tracking-tight">
          {userProfile.points}
          <span className="ml-2 text-2xl font-normal opacity-70">pts</span>
        </p>
        <p className="mt-3 text-xs opacity-60">
          Updated in real time from kiosk
        </p>
      </div>

      {/* ── Account details ─────────────────────────────────────────── */}
      <div className="w-full max-w-2xl rounded-2xl border-2 border-aqua bg-white p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-bold text-dark-blue">
          Account Details
        </h2>
        <div className="space-y-3 text-sm">
          <Row label="Username" value={userProfile.username} />
          <Row label="Email" value={userProfile.email} />
          <Row label="Phone" value={userProfile.phone} />
          <Row
            label="Account Type"
            value={userProfile.is_guest ? "Guest" : "Registered"}
          />
        </div>
      </div>

      {/* ── Pricing reference ───────────────────────────────────────── */}
      <div className="mt-6 w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-bold text-dark-blue">
          Pricing Reference
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <PricingTable
            title="Registered Users"
            rows={[
              ["100 ml", "1 pt"],
              ["250 ml", "2 pts"],
              ["500 ml", "4 pts"],
              ["1000 ml", "8 pts"],
            ]}
          />
          <PricingTable
            title="Guest Users"
            rows={[
              ["100 ml", "1 pt"],
              ["250 ml", "3 pts"],
              ["500 ml", "5 pts"],
              ["1000 ml", "10 pts"],
            ]}
          />
        </div>

        <h3 className="mb-2 mt-6 text-sm font-bold text-dark-blue">
          Top-Up Rates (Registered)
        </h3>
        <div className="flex flex-wrap gap-2 text-xs">
          {[
            ["₱1", "1 pt"],
            ["₱5", "6 pts"],
            ["₱10", "13 pts"],
            ["₱20", "25 pts"],
            ["₱50", "60 pts"],
            ["₱100", "115 pts"],
          ].map(([cash, pts]) => (
            <span
              key={cash}
              className="rounded-full bg-screen-bg px-3 py-1 text-dark-blue"
            >
              {cash} → {pts}
            </span>
          ))}
        </div>
      </div>

      <div className="pb-10" />
    </main>
  );
}

/* ── Helper components ──────────────────────────────────────────────── */

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-gray-100 pb-2">
      <span className="text-steel">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function PricingTable({
  title,
  rows,
}: {
  title: string;
  rows: [string, string][];
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-bold text-app-bg">{title}</h3>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b text-left text-steel">
            <th className="pb-1">Volume</th>
            <th className="pb-1 text-right">Cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([vol, cost]) => (
            <tr key={vol} className="border-b border-gray-50">
              <td className="py-1">{vol}</td>
              <td className="py-1 text-right font-medium">{cost}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
