import type { ServiceMetrics, Alert, AIInsight } from '../types'
import { SERVICES, INITIAL_ALERTS, AI_INSIGHTS } from './mockData'

const BASE_URL = '/api'

async function fetchWithFallback<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(BASE_URL + url, { signal: AbortSignal.timeout(2000) })
    if (!res.ok) throw new Error('Network error')
    return await res.json()
  } catch {
    return fallback
  }
}

export async function getServices(): Promise<ServiceMetrics[]> {
  return fetchWithFallback('/services', SERVICES)
}

export async function getAlerts(): Promise<Alert[]> {
  return fetchWithFallback('/alerts', INITIAL_ALERTS)
}

export async function getAIInsights(): Promise<AIInsight[]> {
  return fetchWithFallback('/insights', AI_INSIGHTS)
}

export async function triggerSimulation(serviceId: string): Promise<{ success: boolean }> {
  try {
    const res = await fetch(`${BASE_URL}/simulate/${serviceId}`, {
      method: 'POST',
      signal: AbortSignal.timeout(2000),
    })
    return await res.json()
  } catch {
    return { success: true } // simulate success even offline
  }
}
