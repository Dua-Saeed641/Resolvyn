/** project.md §75: minimal demo login, no production auth. */
export default function LoginPage() {
  return (
    <div className="flex h-screen items-center justify-center bg-bg-primary">
      <form className="w-full max-w-xs rounded border border-border bg-card p-6">
        <p className="text-sm font-semibold text-text-primary">RESOLVYN</p>
        <p className="mt-1 text-xs text-text-muted">Autonomous Support Operations</p>

        <label className="mt-6 block text-xs text-text-muted" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          className="mt-1 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
        />

        <label className="mt-4 block text-xs text-text-muted" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          className="mt-1 w-full rounded border border-border bg-bg-primary p-2 text-sm text-text-primary"
        />

        <button
          type="submit"
          className="mt-6 w-full rounded bg-text-primary py-2 text-sm font-medium text-bg-primary"
        >
          Sign in
        </button>
      </form>
    </div>
  );
}
