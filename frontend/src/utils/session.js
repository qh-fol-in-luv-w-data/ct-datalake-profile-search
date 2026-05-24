/**
 * CT Group — Vue Session Composable
 * ====================================
 * Quan ly auth state bang Vue reactive.
 * KHONG inject raw HTML — dung CTSplashScreen.vue + CTAccessDenied.vue.
 *
 * Export:
 *   useSession()   -> { authState, csrfToken, sessionId }
 *   initSession()  -> goi khi app mount
 *   getCsrfToken() -> lay csrf cho axios/fetch
 *   getSessionId() -> lay session_id cho X-App-Session-Id header
 */

import { ref } from 'vue'

// Singleton reactive state — dung chung cho toan bo app
const authState  = ref('loading')   // 'loading' | 'authorized' | 'denied'
const _csrf      = ref('')
const _sessionId = ref('')
let   _done      = false

/**
 * Composable — dung trong <script setup>:
 *   const { authState } = useSession()
 */
export function useSession() {
  return { authState, csrfToken: _csrf, sessionId: _sessionId }
}

/**
 * Goi 1 lan trong onMounted() cua App.vue.
 * @param {string} contextUrl - VD: '/api/method/ct_datalake.api.get_context'
 */
export async function initSession(contextUrl) {
  if (_done) return
  authState.value = 'loading'

  // Xoa URL params khoi thanh dia chi (bao mat)
  if (window.location.search) {
    window.history.replaceState({}, '', window.location.pathname)
  }

  try {
    const res = await fetch(contextUrl, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })

    if (res.status === 403) {
      authState.value = 'denied'
      return
    }

    // Frappe redirects to login if unauthenticated (allow_guest=False)
    if (res.status === 401 || res.status === 307 || res.redirected || res.url.includes('/login')) {
      window.location.href = '/login'
      return
    }

    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const json = await res.json()
    if (json.exc || json.exc_type) {
      throw new Error(json.exc_type || 'Frappe Server Exception')
    }
    
    const data  = json.message ?? json
    if (data?.csrf_token) _csrf.value      = data.csrf_token
    if (data?.session_id) _sessionId.value = data.session_id

    _done = true
    authState.value = 'authorized'
    console.debug('[CT Session] OK', { sessionId: _sessionId.value })

  } catch (err) {
    // FAIL-CLOSED: Khong cho phep fail-open trong context xac thuc
    _done = true
    authState.value = 'denied'
    console.error('[CT Session] initSession error (fail-closed):', err)
  }
}

/** Lay CSRF token hien tai (dung cho X-Frappe-CSRF-Token header) */
export function getCsrfToken()  { return _csrf.value }

/** Lay session_id hien tai (dung cho X-App-Session-Id header) */
export function getSessionId()  { return _sessionId.value }

/** Reset — dung khi logout hoac test */
export function resetSession()  {
  _csrf.value = ''; _sessionId.value = ''; _done = false
  authState.value = 'loading'
}
