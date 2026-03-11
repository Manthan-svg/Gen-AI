import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import LoginComponent from './components/LoginComponent.jsx'
import SignupComponent from './components/SignupComponent.jsx'

function RootRouter() {
  const user = JSON.parse(localStorage.getItem('user-info'))

  return (
    <BrowserRouter>
      <Routes>
        {/* Public route: Login */}
        <Route
          path="/"
          element={
            user ? <Navigate to="/app" replace /> : <LoginComponent />
          }
        />

        {/* Public route: Signup */}
        <Route
          path="/signup"
          element={
            user ? <Navigate to="/app" replace /> : <SignupComponent />
          }
        />

        {/* Protected route: Main App */}
        <Route
          path="/app"
          element={
            user ? <App /> : <Navigate to="/" replace />
          }
        />

        {/* Fallback: any unknown path redirects to root */}
        <Route
          path="*"
          element={<Navigate to={user ? "/app" : "/"} replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RootRouter />
  </StrictMode>,
)
