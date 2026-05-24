<template>
  <div class="ct-denied">
    <div class="ct-orb ct-orb-1" />
    <div class="ct-orb ct-orb-2" />
    <div class="ct-card">
      <div class="ct-lock-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      </div>
      <p class="ct-code">Error 403</p>
      <h1 class="ct-title">Truy cập bị từ chối</h1>
      <p class="ct-desc">
        Bạn không có quyền truy cập vào ứng dụng này.<br>
        Vui lòng liên hệ quản trị viên nếu cần hỗ trợ.
      </p>
      <div class="ct-divider" />
      <a href="/" class="ct-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        Trở về Hub
      </a>
      <p class="ct-brand">CT Group &middot; AI Center</p>
    </div>
  </div>
</template>

<style scoped>
.ct-denied {
  position: fixed; inset: 0; z-index: 99999;
  background: radial-gradient(ellipse at 30% 20%, #0d1f3c 0%, #050d1a 50%, #0a0a0f 100%);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
}
.ct-denied::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(99,102,241,.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,.04) 1px, transparent 1px);
  background-size: 48px 48px;
}

.ct-orb {
  position: absolute; border-radius: 50%;
  filter: blur(80px); pointer-events: none;
  animation: ctOrbF 8s ease-in-out infinite;
}
.ct-orb-1 {
  width: 400px; height: 400px; top: -100px; left: -100px;
  background: radial-gradient(circle, rgba(239,68,68,.12) 0%, transparent 70%);
}
.ct-orb-2 {
  width: 300px; height: 300px; bottom: -80px; right: -80px;
  background: radial-gradient(circle, rgba(99,102,241,.1) 0%, transparent 70%);
  animation-delay: -4s;
}
@keyframes ctOrbF {
  0%,100% { transform: translateY(0) scale(1); }
  50%     { transform: translateY(-20px) scale(1.05); }
}

.ct-card {
  position: relative; z-index: 10;
  background: rgba(255,255,255,.04);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 24px;
  padding: 48px 56px;
  text-align: center;
  max-width: 440px; width: 90%;
  box-shadow:
    0 0 0 1px rgba(239,68,68,.1),
    0 32px 64px rgba(0,0,0,.4),
    0 0 120px rgba(239,68,68,.06);
  animation: ctCardIn .5s cubic-bezier(.34,1.56,.64,1) both;
}
@keyframes ctCardIn {
  from { opacity: 0; transform: scale(.88) translateY(20px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}

.ct-lock-wrap {
  width: 80px; height: 80px;
  background: radial-gradient(135deg, rgba(239,68,68,.2) 0%, rgba(239,68,68,.05) 100%);
  border: 1px solid rgba(239,68,68,.3);
  border-radius: 20px;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 24px;
  animation: ctPulse 3s ease-in-out infinite;
  box-shadow: 0 0 40px rgba(239,68,68,.15);
}
@keyframes ctPulse {
  0%,100% { box-shadow: 0 0 20px rgba(239,68,68,.15); }
  50%     { box-shadow: 0 0 40px rgba(239,68,68,.3); }
}
.ct-lock-wrap svg { width: 36px; height: 36px; color: #ef4444; }

.ct-code {
  font-size: 13px; font-weight: 600; letter-spacing: 3px;
  color: rgba(239,68,68,.6); text-transform: uppercase;
  margin: 0 0 12px;
}
.ct-title {
  font-size: 22px; font-weight: 700; color: #f1f5f9;
  margin: 0 0 12px; line-height: 1.3;
}
.ct-desc {
  font-size: 14px; color: rgba(148,163,184,.8);
  line-height: 1.6; margin: 0 0 32px;
}
.ct-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.08), transparent);
  margin-bottom: 24px;
}
.ct-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 12px 28px;
  background: linear-gradient(135deg, rgba(99,102,241,.15) 0%, rgba(139,92,246,.15) 100%);
  border: 1px solid rgba(99,102,241,.35);
  border-radius: 12px;
  color: #a5b4fc;
  font-family: inherit; font-size: 14px; font-weight: 500;
  text-decoration: none;
  transition: all .2s ease; cursor: pointer;
}
.ct-btn:hover {
  background: linear-gradient(135deg, rgba(99,102,241,.25) 0%, rgba(139,92,246,.25) 100%);
  border-color: rgba(99,102,241,.6); color: #c7d2fe;
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(99,102,241,.2);
}
.ct-brand {
  margin-top: 28px;
  font-size: 11px; font-weight: 500; letter-spacing: 1.5px;
  color: rgba(100,116,139,.6); text-transform: uppercase;
}
</style>
