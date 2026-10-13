import { useHealth } from './api/health'

function ApiStatus() {
  const health = useHealth()

  if (health.isPending) {
    return <span className="text-slate-500">Checking API...</span>
  }
  if (health.isError) {
    return <span className="text-red-600">API unreachable</span>
  }
  return (
    <span className="text-emerald-700">
      API ok (v{health.data.version}, {health.data.env})
    </span>
  )
}

export default function App() {
  return (
    <main className="mx-auto flex min-h-svh max-w-2xl flex-col justify-center gap-4 px-6">
      <h1 className="text-4xl font-bold text-slate-900">DaleelAI</h1>
      <p className="text-lg text-slate-600">
        Tax and compliance answers for Pakistan, with sources from FBR and SECP.
      </p>
      <p className="text-sm">
        <ApiStatus />
      </p>
    </main>
  )
}
