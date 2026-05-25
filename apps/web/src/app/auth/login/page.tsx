import { Suspense } from 'react';
import { LoginForm } from '@/components/auth/login-form';
import { signIn } from 'next-auth/react'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">UnSearch</h1>
          <p className="text-muted-foreground mt-2">
            Privacy-respecting search API
          </p>
        </div>
        <button
          onClick={() => signIn('github')}
          className="w-full mb-4 inline-flex items-center justify-center rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
        >
          Continue with GitHub
        </button>
        <Suspense fallback={<div>Loading...</div>}>
          <LoginForm />
        </Suspense>
        <p className="text-center text-sm text-muted-foreground mt-4">
          No account? <a href="/auth/register" className="underline">Sign up</a>
        </p>
      </div>
    </div>
  );
}
