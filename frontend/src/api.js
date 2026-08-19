// Relative by default ("/api") so a same-origin deployment (Vercel Services
// routes "/api/*" to the backend) works with no env var set. Local dev sets
// VITE_API_BASE_URL to a separate origin, e.g. http://localhost:8001/api.
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE_URL + path, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
    }
  }

  let response
  try {
    response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error(`Cannot reach the API at ${BASE_URL}. Is the backend running?`)
  }

  if (response.status === 204) return null

  const text = await response.text()
  const payload = text ? JSON.parse(text) : null

  if (!response.ok) {
    throw new Error(detailToMessage(payload) || `Request failed (${response.status})`)
  }
  return payload
}

function detailToMessage(payload) {
  const detail = payload?.detail
  if (!detail) return null
  if (typeof detail === 'string') return detail
  // FastAPI validation errors arrive as a list of {loc, msg}.
  if (Array.isArray(detail)) {
    return detail.map((e) => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ')
  }
  return JSON.stringify(detail)
}

export const api = {
  statuses: () => request('/statuses'),
  stats: () => request('/stats'),
  monthlyStats: (month) => request('/stats/monthly', { params: { month } }),

  listDresses: ({ search, archived = false, supplier, notReceived = false } = {}) =>
    request('/dresses', {
      params: {
        search,
        archived: archived ? 'true' : undefined,
        supplier,
        not_received: notReceived ? 'true' : undefined,
      },
    }),
  nextDressCode: () => request('/dresses/next-code'),
  suppliers: () => request('/dresses/suppliers'),
  getDress: (id) => request(`/dresses/${id}`),
  createDress: (data) => request('/dresses', { method: 'POST', body: data }),
  updateDress: (id, data) => request(`/dresses/${id}`, { method: 'PUT', body: data }),
  archiveDress: (id) => request(`/dresses/${id}/archive`, { method: 'POST' }),
  restoreDress: (id) => request(`/dresses/${id}/restore`, { method: 'POST' }),
  deleteDress: (id) => request(`/dresses/${id}`, { method: 'DELETE' }),

  listOrders: (dressId) => request('/orders', { params: { dress_id: dressId } }),
  createOrder: (data) => request('/orders', { method: 'POST', body: data }),
  updateOrder: (id, data) => request(`/orders/${id}`, { method: 'PUT', body: data }),
  deleteOrder: (id) => request(`/orders/${id}`, { method: 'DELETE' }),

  listSales: (dressId) => request('/sales', { params: { dress_id: dressId } }),
  createSale: (data) => request('/sales', { method: 'POST', body: data }),
  deleteSale: (id) => request(`/sales/${id}`, { method: 'DELETE' }),
}

export default api
