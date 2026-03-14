// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
import './index.css'
import AuthGuard from './components/carf/AuthGuard'
import Dashboard from './components/carf/DashboardLayout'

function App() {
  return (
    <AuthGuard>
      <Dashboard />
    </AuthGuard>
  )
}

export default App
