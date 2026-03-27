import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const token = localStorage.getItem('token')

  if (!isAuthenticated && !token) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
