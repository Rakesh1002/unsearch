'use client';

import { withAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth-context';
import Link from 'next/link';

function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-muted/50">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">UnSearch Dashboard</h1>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-muted-foreground">
              Welcome, {user?.full_name || user?.email}
            </span>
            <Button variant="outline" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* User Info Card */}
          <Card>
            <CardHeader>
              <CardTitle>Account Information</CardTitle>
              <CardDescription>Your account details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div>
                <span className="font-medium">Email:</span> {user?.email}
              </div>
              {user?.full_name && (
                <div>
                  <span className="font-medium">Name:</span> {user.full_name}
                </div>
              )}
              {user?.company && (
                <div>
                  <span className="font-medium">Company:</span> {user.company}
                </div>
              )}
              <div>
                <span className="font-medium">Plan:</span> {user?.plan || 'Free'}
              </div>
              <div>
                <span className="font-medium">Status:</span> 
                <span className={user?.is_verified ? 'text-green-600' : 'text-yellow-600'}>
                  {user?.is_verified ? ' Verified' : ' Unverified'}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Common tasks</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full" variant="outline" asChild>
                <Link href="/dashboard/api-keys">Manage API Keys</Link>
              </Button>
              <Button className="w-full" variant="outline" asChild>
                <Link href="/dashboard/usage">View Usage</Link>
              </Button>
              <Button className="w-full" variant="outline" asChild>
                <Link href="/dashboard/billing">Billing Settings</Link>
              </Button>
              <Button className="w-full" variant="outline" asChild>
                <Link href="/docs">Documentation</Link>
              </Button>
            </CardContent>
          </Card>

          {/* Stats Placeholder */}
          <Card>
            <CardHeader>
              <CardTitle>Usage This Month</CardTitle>
              <CardDescription>Your current usage statistics</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span>Searches:</span>
                <span>0 / 1,000</span>
              </div>
              <div className="flex justify-between">
                <span>Scrapes:</span>
                <span>0 / 10,000</span>
              </div>
              <div className="flex justify-between">
                <span>API Calls:</span>
                <span>0</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Welcome Message */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Welcome to UnSearch! 🎉</CardTitle>
            <CardDescription>
              Your account has been created successfully. Here&apos;s what you can do next:
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">1. Create API Keys</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  Generate API keys to start making requests to the UnSearch API.
                </p>
                <Button size="sm" asChild>
                  <Link href="/dashboard/api-keys">Create Your First API Key</Link>
                </Button>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">2. Read Documentation</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  Learn how to integrate UnSearch into your applications.
                </p>
                <Button size="sm" variant="outline">View Docs</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

export default withAuth(DashboardPage);
