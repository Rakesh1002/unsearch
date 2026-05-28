import type { Env } from "./env.js"
import { d1All, nowIso } from "./lib/d1.js"

export async function handleScheduled(controller: ScheduledController, env: Env): Promise<void> {
  const cron = controller.cron

  if (cron === "0 */6 * * *") {
    // Every 6 hours: nudge active topic monitors that missed their alarm
    const monitors = await d1All<{ monitor_id: string }>(
      env.DB,
      `SELECT request_id AS monitor_id FROM scraping_jobs WHERE status = 'pending' LIMIT 100`,
    )
    for (const m of monitors) {
      await env.TASK_QUEUE.send({ type: "monitor.check", monitorId: m.monitor_id })
    }
    return
  }

  if (cron === "0 3 * * *") {
    // Daily: snapshot D1 to R2 for backup
    const tables = [
      "users",
      "user_api_keys",
      "api_keys",
      "subscriptions",
      "usage_records",
      "invoices",
      "webhook_events",
      "search_requests",
      "scrape_requests",
    ]
    const snapshot: Record<string, unknown[]> = {}
    for (const t of tables) {
      snapshot[t] = await d1All(env.DB, `SELECT * FROM ${t}`)
    }
    const key = `backups/d1/${new Date().toISOString().slice(0, 10)}.json`
    await env.STORAGE.put(key, JSON.stringify(snapshot), {
      httpMetadata: { contentType: "application/json" },
    })
    return
  }

  if (cron === "0 0 * * *") {
    // Daily: rollover usage_records (close yesterday's window, open today's)
    const today = nowIso().slice(0, 10)
    await env.DB.prepare(
      `INSERT OR IGNORE INTO usage_records (user_id, period_start, period_end)
       SELECT id, ?1, ?2 FROM users WHERE is_active = 1`,
    )
      .bind(`${today}T00:00:00Z`, `${today}T23:59:59Z`)
      .run()
    return
  }
}
