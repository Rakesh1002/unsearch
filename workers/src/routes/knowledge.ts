import { Hono } from "hono"

import type { Env, Variables } from "../env.js"
import { proxyToContainer } from "../lib/container.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const knowledgeRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

knowledgeRoutes.use("*", requireAuth(), rateLimitMiddleware())

/**
 * Glean-parity endpoints. Entity extraction, knowledge graph, people search,
 * and connector-backed document search all need the Python NLP stack and
 * connector OAuth flows that live in the Container.
 */
knowledgeRoutes.all("*", async (c) => proxyToContainer(c.env, c.req.raw as unknown as Request))
