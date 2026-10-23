import axios from 'axios'

/**
 * Axios instance for the AgriConnect API.
 *
 * Auth design: the backend stores the JWT in an HttpOnly cookie (not readable by JS, so
 * not exposed to XSS token theft). State-changing requests must echo the value of the
 * readable `csrf_access_token` cookie in an X-CSRF-TOKEN header (double-submit CSRF
 * protection). Nothing sensitive is kept in localStorage.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  withCredentials: true,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

export function readCookie(name) {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : null
}

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (!['get', 'head', 'options'].includes(method)) {
    const csrf = readCookie('csrf_access_token')
    if (csrf) config.headers['X-CSRF-TOKEN'] = csrf
  }
  return config
})

let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

/** Normalised error: { status, code, message, details } */
export class ApiError extends Error {
  constructor({ status, code, message, details }) {
    super(message)
    this.status = status
    this.code = code
    this.details = details || {}
  }
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isCancel(error)) return Promise.reject(error)
    const status = error.response?.status ?? 0
    const body = error.response?.data?.error
    const apiError = new ApiError({
      status,
      code: body?.code || (status ? 'http_error' : 'network_error'),
      message:
        body?.message ||
        (status
          ? `The server returned an error (${status}).`
          : 'Cannot reach the AgriConnect server. Check your connection and that the backend is running.'),
      details: body?.details,
    })
    const url = error.config?.url || ''
    if (status === 401 && onUnauthorized && !url.startsWith('/auth/')) onUnauthorized(apiError)
    return Promise.reject(apiError)
  },
)

const get = (url, params, config) => api.get(url, { params, ...config }).then((r) => r.data)
const post = (url, data) => api.post(url, data).then((r) => r.data)
const patch = (url, data) => api.patch(url, data).then((r) => r.data)

export const endpoints = {
  // auth
  register: (data) => post('/auth/register', data),
  login: (data) => post('/auth/login', data),
  logout: () => post('/auth/logout'),
  me: () => get('/auth/me'),
  // user
  profile: () => get('/users/me'),
  updateProfile: (data) => patch('/users/me', data),
  // catalog
  summary: (cfg) => get('/stats/summary', undefined, cfg),
  crops: (params, cfg) => get('/crops', params, cfg),
  crop: (id, cfg) => get(`/crops/${id}`, undefined, cfg),
  markets: (params, cfg) => get('/markets', params, cfg),
  prices: (params, cfg) => get('/prices', params, cfg),
  price: (id, cfg) => get(`/prices/${id}`, undefined, cfg),
  priceHistory: (params, cfg) => get('/prices/history', params, cfg),
  // predictions
  modelInfo: (cfg) => get('/predictions/model', undefined, cfg),
  createPrediction: (data) => post('/predictions', data),
  predictions: (params, cfg) => get('/predictions', params, cfg),
  prediction: (id, cfg) => get(`/predictions/${id}`, undefined, cfg),
  // misc
  contact: (data) => post('/contact', data),
  health: () => get('/health'),
}
