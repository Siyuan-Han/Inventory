const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001').replace(/\/$/, '')

async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(BASE_URL + path)
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

  listDresses: (search) => request('/dresses', { params: { search } }),
  getDress: (id) => request(`/dresses/${id}`),
  createDress: (data) => request('/dresses', { method: 'POST', body: data }),
  updateDress: (id, data) => request(`/dresses/${id}`, { method: 'PUT', body: data }),
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
