/**
 * Lightweight client-side auth state (token in localStorage).
 * For production you'd swap this for Better Auth or NextAuth, but for
 * v1 the Worker issues JWTs and the dashboard just stores them.
 */
"use client"

import { useEffect, useState } from "react"

const TOKEN_KEY = "unsearch.token"
const PLAN_KEY = "unsearch.plan"

export interface Session {
  token: string
  plan: string
  userId?: number
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setStoredSession(session: { token: string; plan: string; userId?: number }): void {
  window.localStorage.setItem(TOKEN_KEY, session.token)
  window.localStorage.setItem(PLAN_KEY, session.plan)
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_KEY)
  window.localStorage.removeItem(PLAN_KEY)
}

export function useSession(): Session | null {
  const [session, setSession] = useState<Session | null>(null)
  useEffect(() => {
    const token = window.localStorage.getItem(TOKEN_KEY)
    const plan = window.localStorage.getItem(PLAN_KEY) ?? "FREE"
    if (token) setSession({ token, plan })
  }, [])
  return session
}
