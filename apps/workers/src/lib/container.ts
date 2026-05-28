import type { Env } from "../env.js"

/**
 * Forward a request to the Python FastAPI container via service binding.
 * Returns a structured 503 if the binding isn't configured (initial deploy
 * before `wrangler containers deploy` runs).
 */
export async function proxyToContainer(env: Env, request: Request): Promise<Response> {
  if (!env.CONTAINER) {
    return Response.json(
      {
        error: "container_not_configured",
        message:
          "This endpoint requires the FastAPI container, which is not yet deployed. Edge-native endpoints (auth, neural, RAG, verify, billing, monitor) still work.",
      },
      { status: 503 },
    )
  }
  return env.CONTAINER.fetch(request)
}

export async function callContainer(
  env: Env,
  url: string,
  init: RequestInit = {},
): Promise<Response> {
  if (!env.CONTAINER) {
    return Response.json(
      { error: "container_not_configured", upstream: url },
      { status: 503 },
    )
  }
  return env.CONTAINER.fetch(new Request(url, init))
}
