import React, { createContext, useContext, useEffect, useState } from 'react'
import { api } from '@/lib/api'

interface AuthContextType {
  isAuthenticated: boolean
  login: (apiKey: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkAuth = async () => {
      if (api.isAuthenticated()) {
        try {
          const connected = await api.testConnection()
          setIsAuthenticated(connected)
        } catch {
          setIsAuthenticated(false)
          api.clearAuth()
        }
      }
      setLoading(false)
    }

    checkAuth()
  }, [])

  const login = async (apiKey: string) => {
    await api.login(apiKey)
    setIsAuthenticated(true)
  }

  const logout = () => {
    api.clearAuth()
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}