import Link from "next/link";

export default function RegisterPage() {

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border-2 border-aqua bg-white p-10 shadow-lg text-center">
        <h1 className="mb-2 text-2xl font-bold text-dark-blue">💧 AquaSmart</h1>
        <p className="mb-6 text-sm text-steel">Account Registration</p>

        <div className="mb-6 rounded-xl bg-blue-50 px-6 py-5 text-sm text-dark-blue leading-relaxed">
          <p className="font-semibold mb-1">Register at the AquaSmart kiosk.</p>
          <p className="text-steel">
            Once registered, come back here and sign in with the same email and
            password you used at the kiosk.
          </p>
        </div>

        <Link
          href="/login"
          className="inline-block w-full rounded-lg bg-dark-blue py-3 text-sm font-bold text-white transition hover:bg-dark-blue/90"
        >
          Go to Sign In
        </Link>
      </div>
    </main>
  );
}
