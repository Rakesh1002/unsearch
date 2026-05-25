'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function PricingPage() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-bold tracking-tight">Simple, predictable pricing</h1>
        <p className="mt-3 text-muted-foreground">Start free, scale when you need. No surprise token fees.</p>
      </div>

      <div className="mx-auto mt-10 grid max-w-5xl gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Developer</CardTitle>
            <CardDescription>Free forever</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>1,000 unified calls / month</li>
              <li>Basic rate limits</li>
              <li>Community support</li>
            </ul>
            <Button className="mt-6" asChild>
              <a href="/auth/register">Start free</a>
            </Button>
          </CardContent>
        </Card>

        <Card className="border-primary/40">
          <CardHeader>
            <CardTitle>Pro / Startup</CardTitle>
            <CardDescription>$79 / month</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>50,000 unified calls / month</li>
              <li>Higher rate limits</li>
              <li> Email support</li>
            </ul>
            <Button className="mt-6" asChild>
              <a href="/auth/register">Upgrade</a>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Enterprise</CardTitle>
            <CardDescription>Custom</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>Dedicated infra & SLAs</li>
              <li>Compliance & PII tooling</li>
              <li>Indemnification option</li>
            </ul>
            <Button className="mt-6" variant="outline" asChild>
              <a href="/auth/register">Contact sales</a>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}


