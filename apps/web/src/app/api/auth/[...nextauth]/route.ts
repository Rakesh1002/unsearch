import NextAuth, { AuthOptions } from 'next-auth'
import GitHubProvider from 'next-auth/providers/github'
import CredentialsProvider from 'next-auth/providers/credentials'
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function oauthSync(profile: any, token: string) {
	try {
		await axios.post(
			`${API_BASE_URL}/api/v1/auth/oauth-sync`,
			{
				provider: 'github',
				oauth_id: String(profile.id),
				email: profile.email,
				full_name: profile.name,
				avatar_url: profile.avatar_url,
			},
			{ headers: { 'Content-Type': 'application/json' } }
		)
	} catch (e) {
		// Non-fatal; user can still use NextAuth session
	}
}

export const authOptions: AuthOptions = {
	providers: [
		GitHubProvider({
			clientId: process.env.GITHUB_CLIENT_ID || '',
			clientSecret: process.env.GITHUB_CLIENT_SECRET || '',
		}),
		CredentialsProvider({
			name: 'Credentials',
			credentials: {
				email: { label: 'Email', type: 'email' },
				password: { label: 'Password', type: 'password' },
			},
			async authorize(credentials) {
				if (!credentials?.email || !credentials.password) return null
				try {
					const { data } = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, {
						email: credentials.email,
						password: credentials.password,
					})
					return {
						id: String(data.user?.id || credentials.email),
						name: data.user?.full_name || credentials.email,
						email: credentials.email,
						accessToken: data.access_token,
						refreshToken: data.refresh_token,
					}
				} catch {
					return null
				}
			},
		}),
	],
	session: { strategy: 'jwt' },
	callbacks: {
		async jwt({ token, account, profile, user }) {
			if (account?.provider === 'github' && profile) {
				oauthSync(profile, token?.accessToken as string)
			}
			if ((user as any)?.accessToken) {
				token.accessToken = (user as any).accessToken
				token.refreshToken = (user as any).refreshToken
			}
			return token
		},
		async session({ session, token }) {
			;(session as any).accessToken = (token as any).accessToken
			;(session as any).refreshToken = (token as any).refreshToken
			return session
		},
	},
	pages: {
		signIn: '/auth/login',
	},
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
