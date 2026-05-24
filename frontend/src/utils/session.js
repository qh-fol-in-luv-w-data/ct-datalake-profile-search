/**
 * CT Group — Vue Session Composable (AI ATS)
 * ============================================
 * Quan ly auth state bang Vue reactive.
 *
 * Export:
 *   useSession()   -> { authState, currentUser, currentFullName, csrfToken, sessionId }
 *   initSession()  -> goi khi app mount
 *   getCsrfToken() -> lay csrf cho axios/fetch
 *   getSessionId() -> lay session_id cho X-App-Session-Id header
 */

import { ref } from 'vue'

// Singleton reactive state — dung chung cho toan bo app
const authState = ref('loading')   // 'loading' | 'authorized' | 'denied'
const _csrf = ref('')
const _sessionId = ref('')
const _user = ref('Guest')
const _fullName = ref('Guest')
let _done = false

/**
 * Composable — dung trong <script setup>:
 *   const { authState, currentUser, currentFullName } = useSession()
 */
export function useSession() {
  return { authState, csrfToken: _csrf, sessionId: _sessionId, currentUser: _user, currentFullName: _fullName }
}

/**
 * Goi 1 lan trong onMounted() cua App.vue.
 * @param {string} contextUrl - '/api/method/ai_ats.api.get_context'
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
      removeSplash()
      return
    }

    // Frappe redirects to login if unauthenticated (allow_guest=False)
    if (res.status === 401 || res.status === 307 || res.redirected || res.url.includes('/login')) {
      removeSplash()
      window.location.href = '/login'
      return
    }

    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const json = await res.json()
    if (json.exc || json.exc_type) {
      throw new Error(json.exc_type || 'Frappe Server Exception')
    }

    const data = json.message ?? json
    if (data?.csrf_token) _csrf.value = data.csrf_token
    if (data?.session_id) _sessionId.value = data.session_id
    if (data?.user) _user.value = data.user
    if (data?.full_name) _fullName.value = data.full_name

    _done = true
    authState.value = 'authorized'
    console.debug('[CT Session] OK', { sessionId: _sessionId.value, user: _user.value })

    removeSplash()

  } catch (err) {
    // FAIL-CLOSED: Khong cho phep fail-open trong context xac thuc
    _done = true
    authState.value = 'denied'
    removeSplash()
    console.error('[CT Session] initSession error (fail-closed):', err)
  }
}

function removeSplash() {
  const splash = document.getElementById('ct-splash')
  if (splash) splash.remove()
  // Show app after auth resolves
  const app = document.getElementById('app')
  if (app) app.style.display = 'block'
}

/** Lay CSRF token hien tai (dung cho X-Frappe-CSRF-Token header) */
export function getCsrfToken() { return _csrf.value }

/** Lay session_id hien tai (dung cho X-App-Session-Id header) */
export function getSessionId() { return _sessionId.value }

/** Reset — dung khi logout hoac test */
export function resetSession() {
  _csrf.value = ''; _sessionId.value = ''; _user.value = 'Guest'; _fullName.value = 'Guest'; _done = false
  authState.value = 'loading'
}
