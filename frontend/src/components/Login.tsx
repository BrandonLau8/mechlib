import { GoogleLogin, type CredentialResponse } from '@react-oauth/google'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useState } from 'react'

export function Login() {
    const { login } = useAuth()
    const [error, setError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)

    const handleSuccess = async (credentialResponse: CredentialResponse) => {
        if (!credentialResponse.credential) {
            setError('No credential received from Google')
            return
        }

        setIsLoading(true)
        setError(null)

        try {
            await login(credentialResponse.credential)
            // AuthContext will update and App will re-render
        } catch (err) {
            setError('Failed to authenticate. Please try again.')
            console.error('Login failed:', err)
        } finally {
            setIsLoading(false)
        }
    }

    const handleError = () => {
        setError('Google Sign-In failed. Please try again.')
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="w-full max-w-md mx-4">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl">Welcome to MechLib</CardTitle>
                    <CardDescription>
                        Sign in with your Google account to upload and manage images
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {error && (
                        <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded">
                            {error}
                        </div>
                    )}

                    <div className="flex justify-center">
                        {isLoading ? (
                            <div className="text-muted-foreground">Signing in...</div>
                        ) : (
                            <GoogleLogin
                                onSuccess={handleSuccess}
                                onError={handleError}
                                useOneTap
                                theme="filled_blue"
                                size="large"
                                text="signin_with"
                            />
                        )}
                    </div>

                    <div className="text-xs text-muted-foreground text-center">
                        By signing in, you agree to use this application for authorized image management only.
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}