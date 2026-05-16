import type { Env, TaskMessage } from "./env.js"

const MAX_WEBHOOK_ATTEMPTS = 5

export async function handleQueueBatch(
  batch: MessageBatch<TaskMessage>,
  env: Env,
): Promise<void> {
  for (const message of batch.messages) {
    try {
      await handleMessage(message.body, env)
      message.ack()
    } catch (err) {
      console.error("queue handler error", err, message.body)
      message.retry()
    }
  }
}

async function handleMessage(msg: TaskMessage, env: Env): Promise<void> {
  switch (msg.type) {
    case "scrape":
      await env.CONTAINER.fetch(
        new Request("https://container.internal/internal/scrape", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ jobId: msg.jobId, urls: msg.urls, config: msg.config }),
        }),
      )
      return

    case "research":
      // Research kicked via DO; this is a fan-out hook for retries
      return

    case "embed":
      await env.CONTAINER.fetch(
        new Request("https://container.internal/internal/embed", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ documents: msg.documents }),
        }),
      )
      return

    case "monitor.check": {
      const id = env.TOPIC_MONITOR.idFromName(msg.monitorId)
      const stub = env.TOPIC_MONITOR.get(id)
      await stub.fetch("https://do.internal/check", { method: "POST" })
      return
    }

    case "webhook.deliver": {
      const resp = await fetch(msg.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "User-Agent": "UnSearch-Webhook/1.0" },
        body: JSON.stringify(msg.payload),
      })
      if (!resp.ok && msg.attempt < MAX_WEBHOOK_ATTEMPTS) {
        const delaySec = Math.min(3600, 2 ** msg.attempt * 30)
        await env.TASK_QUEUE.send({ ...msg, attempt: msg.attempt + 1 }, { delaySeconds: delaySec })
      }
      return
    }
  }
}
