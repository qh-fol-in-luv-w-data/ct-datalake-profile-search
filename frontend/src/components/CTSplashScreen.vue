<template>
  <div class="ct-splash">
    <div class="ct-orb ct-orb-1" />
    <div class="ct-orb ct-orb-2" />
    <div class="ct-inner">
      <div class="ct-ring">
        <div class="ct-ring-bg" />
        <div class="ct-ring-spin" />
        <div class="ct-ring-rev" />
        <div class="ct-ring-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
      </div>
      <div class="ct-text">
        <p class="ct-title">Đang xác thực quyền truy cập</p>
        <p class="ct-sub">CT Group &middot; AI Center</p>
      </div>
      <div class="ct-dots">
        <span /><span /><span />
      </div>
    </div>
  </div>
</template>

<style scoped>
.ct-splash {
  position: fixed; inset: 0; z-index: 99999;
  background: radial-gradient(ellipse at 30% 20%, #0d1f3c 0%, #050d1a 50%, #0a0a0f 100%);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
}
.ct-splash::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(14,165,233,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(14,165,233,.05) 1px, transparent 1px);
  background-size: 48px 48px;
  animation: ctGF 4s ease-in-out infinite alternate;
}
@keyframes ctGF { from { opacity: .5 } to { opacity: 1 } }

.ct-orb {
  position: absolute; border-radius: 50%;
  filter: blur(80px); pointer-events: none;
  animation: ctFloat 10s ease-in-out infinite;
}
.ct-orb-1 {
  width: 500px; height: 500px; top: -120px; left: -120px;
  background: radial-gradient(circle, rgba(14,165,233,.12) 0%, transparent 70%);
}
.ct-orb-2 {
  width: 400px; height: 400px; bottom: -100px; right: -80px;
  background: radial-gradient(circle, rgba(99,102,241,.10) 0%, transparent 70%);
  animation-delay: -5s; animation-duration: 12s;
}
@keyframes ctFloat {
  0%,100% { transform: translate(0,0); }
  33%     { transform: translate(20px,-15px); }
  66%     { transform: translate(-10px,20px); }
}

.ct-inner {
  position: relative; z-index: 1;
  display: flex; flex-direction: column;
  align-items: center; gap: 20px;
  animation: ctFI .6s ease both;
}
@keyframes ctFI {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.ct-ring { position: relative; width: 72px; height: 72px; }
.ct-ring-bg {
  position: absolute; inset: 0; border-radius: 50%;
  border: 2px solid rgba(14,165,233,.15);
  background: rgba(14,165,233,.06);
}
.ct-ring-spin {
  position: absolute; inset: 0; border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: #0ea5e9;
  border-right-color: rgba(14,165,233,.3);
  animation: ctSpin 1s linear infinite;
}
.ct-ring-rev {
  position: absolute; inset: 6px; border-radius: 50%;
  border: 1px solid transparent;
  border-bottom-color: rgba(99,102,241,.6);
  animation: ctSpin 2s linear infinite reverse;
}
@keyframes ctSpin { to { transform: rotate(360deg); } }
.ct-ring-icon {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: rgba(14,165,233,.7);
}

.ct-text { text-align: center; }
.ct-title {
  font-size: 14px; font-weight: 500;
  color: rgba(226,232,240,.9); margin-bottom: 4px;
}
.ct-sub { font-size: 12px; color: rgba(100,116,139,.7); }

.ct-dots { display: flex; gap: 6px; }
.ct-dots span {
  width: 5px; height: 5px; border-radius: 50%;
  background: #0ea5e9;
  animation: ctBounce 1.2s ease-in-out infinite;
}
.ct-dots span:nth-child(2) { animation-delay: .2s; background: rgba(14,165,233,.7); }
.ct-dots span:nth-child(3) { animation-delay: .4s; background: rgba(14,165,233,.4); }
@keyframes ctBounce {
  0%,80%,100% { transform: scale(1); opacity: .5; }
  40%         { transform: scale(1.4); opacity: 1; }
}
</style>
