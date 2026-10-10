/**
 * Placeholder OpenAPI types. Regenerate with:
 *   pnpm openapi:gen
 * after the API is running.
 */
export type paths = {
  '/api/v1/projects': {
    get: { responses: { 200: { content: { 'application/json': components['schemas']['ProjectOut'][] } } } }
    post: {
      requestBody: { content: { 'application/json': components['schemas']['ProjectCreate'] } }
      responses: { 200: { content: { 'application/json': components['schemas']['ProjectOut'] } } }
    }
  }
  '/api/v1/jobs': {
    get: { responses: { 200: { content: { 'application/json': components['schemas']['JobOut'][] } } } }
  }
  '/api/v1/capabilities': {
    get: {
      responses: {
        200: { content: { 'application/json': Record<string, components['schemas']['CapabilityOut']> } }
      }
    }
  }
}

export type components = {
  schemas: {
    ProjectCreate: { title: string; content_rating?: string }
    ProjectOut: {
      id: string
      title: string
      status: string
      content_rating: string
      created_at: string
      updated_at: string
    }
    JobOut: {
      id: string
      kind: string
      status: string
      payload: Record<string, unknown>
      progress: Record<string, unknown>
      attempts: number
      max_attempts: number
      lease_owner: string | null
      leased_until: string | null
      heartbeat_at: string | null
      idempotency_key: string | null
      external_job_ref: string | null
      error_message: string | null
      created_at: string
      updated_at: string
    }
    CapabilityOut: {
      configured: boolean
      runtime_available: boolean
      model_id: string | null
      detail: string
    }
  }
}