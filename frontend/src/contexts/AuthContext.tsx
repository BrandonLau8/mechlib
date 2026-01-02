import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface User {
    email: string
    name: string
    picture: string
}

interface AuthContextType {
    user: User | null
    isAuthenticated: boolean
    login: (googleToken: string) => Promise<void>
    logout: () => void
    getAuthHeaders: () => Record<string, string>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [accessToken, setAccessToken] = useState<string | null>(null)

    // Load user from localStorage on mount
    useEffect(() => {
        const storedToken = localStorage.getItem('access_token')
        const storedUser = localStorage.getItem('user')

        if (storedToken && storedUser) {
            setAccessToken(storedToken)
            setUser(JSON.parse(storedUser))
        }
    }, [])

    const login = async (googleToken: string) => {
        try {
            // Send Google token to backend
            const response = await fetch(`${API_URL}/auth/google`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ id_token: googleToken }),
            })

            if (!response.ok) {
                throw new Error('Authentication failed')
            }

            const data = await response.json()

            // Store token and user info
            setAccessToken(data.access_token)
            setUser({
                email: data.email,
                name: data.name,
                picture: data.picture,
            })

            // Persist to localStorage
            localStorage.setItem('access_token', data.access_token)
            localStorage.setItem('user', JSON.stringify({
                email: data.email,
                name: data.name,
                picture: data.picture,
            }))

        } catch (error) {
            console.error('Login error:', error)
            throw error
        }
    }

    const logout = () => {
        setAccessToken(null)
        setUser(null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
    }

    const getAuthHeaders = () => {
        if (!accessToken) {
            return {}
        }
        return {
            'Authorization': `Bearer ${accessToken}`
        }
    }

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                login,
                logout,
                getAuthHeaders,
            }}
        >
            {children}
        </AuthContext.Provider>
    )
}

export default AuthProvider

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context
}