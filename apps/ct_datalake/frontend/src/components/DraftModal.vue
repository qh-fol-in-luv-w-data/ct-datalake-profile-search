<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import { X, FileText, Copy, Check, Loader2, ChevronDown } from 'lucide-vue-next'

const props = defineProps({
  candidate: Object,
  mode: String,
  visible: Boolean,
})

const emit = defineEmits(['close'])

const DRAFT_TYPES = [
  { value: 'invite_collab',   label: '📩 Thư mời hợp tác nghiên cứu' },
  { value: 'invite_expert',   label: '🎓 Thư mời tham gia hội đồng chuyên gia' },
  { value: 'invite_project',  label: '🔬 Thư mời tham gia dự án' },
  { value: 'invite_lecture',  label: '🏫 Thư mời giảng dạy / báo cáo chuyên đề' },
  { value: 'consult_request', label: '💼 Công văn đề nghị tư vấn' },
  { value: 'partnership',     label: '🤝 Thư đề xuất hợp tác chiến lược' },
]

const selectedType = ref('invite_collab')
const orgName = ref('Cục Thống kê')
const senderName = ref('')
const extraNote = ref('')

const loading = ref(false)
const draftText = ref('')
const copied = ref(false)
const error = ref('')

watch(() => props.visible, (v) => {
  if (v) {
    draftText.value = ''
    error.value = ''
    copied.value = false
  }
})

function buildCandidateInfo(c, mode) {
  if (mode === 'in' || c?.['trường họ và tên'] || c?.school) {
    return [
      `Họ tên: ${c.name || c['trường họ và tên'] || 'Không rõ'}`,
      `Chức vụ: ${c.position || c['chức vụ'] || ''}`,
      `Học vị / học hàm: ${c.degree || c['học vị'] || ''} ${c.academic_rank || c['học hàm'] || ''}`,
      `Trường / đơn vị: ${c.school || c['trường'] || ''}`,
      `Lĩnh vực nghiên cứu: ${c.expertise || c['sản phẩm thực hiện'] || ''}`,
    ].filter(line => !line.endsWith(': ')).join('\n')
  } else {
    return [
      `Họ tên: ${c.name || 'Không rõ'}`,
      `Tổ chức: ${c.affiliation || ''}`,
      `Trường: ${c.university_name || ''} (${c.university_abbr || ''})`,
      `Địa điểm: ${c.city || ''}`,
      `Email: ${c.email || ''}`,
      `Citations: ${c.citations || ''} | h-index: ${c.h_index || ''}`,
      `Lĩnh vực nghiên cứu: ${(c.interests || []).join(', ')}`,
    ].filter(line => !line.endsWith(': ') && !line.endsWith('()')).join('\n')
  }
}

async function generateDraft() {
  if (!props.candidate) return
  loading.value = true
  error.value = ''
  draftText.value = ''

  try {
    const response = await axios.get('/api/method/ct_datalake.ct_datalake.api.draft_document', {
      params: {
        candidate_info: buildCandidateInfo(props.candidate, props.mode),
        doc_type:       selectedType.value,
        org_name:       orgName.value,
        sender_name:    senderName.value,
        extra_note:     extraNote.value,
      }
    })
    draftText.value = response.data.message.draft
  } catch (e) {
    error.value = 'Lỗi: ' + (e.response?.data?.message || e.message)
  } finally {
    loading.value = false
  }
}

async function copyText() {
  if (!draftText.value) return
  await navigator.clipboard.writeText(draftText.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
        <div class="modal-box">

          <div class="modal-header">
            <div class="modal-title">
              <FileText :size="20" />
              <span>Soạn thảo văn bản</span>
            </div>
            <button class="close-btn" @click="emit('close')">
              <X :size="20" />
            </button>
          </div>

          <div class="modal-body">
            <div class="candidate-preview">
              <span class="preview-label">Ứng viên</span>
              <strong>{{ candidate?.name || candidate?.['trường họ và tên'] || 'Unknown' }}</strong>
              <span class="preview-sub">{{ candidate?.affiliation || candidate?.school || candidate?.['trường'] || '' }}</span>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Loại văn bản</label>
                <div class="select-wrapper">
                  <select v-model="selectedType">
                    <option v-for="t in DRAFT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
                  </select>
                  <ChevronDown :size="16" class="select-icon" />
                </div>
              </div>
              <div class="form-group">
                <label>Đơn vị gửi</label>
                <input v-model="orgName" placeholder="Ví dụ: Cục Thống kê, Bộ KH&ĐT..." />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Người ký (tùy chọn)</label>
                <input v-model="senderName" placeholder="Ví dụ: TS. Nguyễn Văn A, Cục trưởng" />
              </div>
              <div class="form-group">
                <label>Ghi chú thêm (tùy chọn)</label>
                <input v-model="extraNote" placeholder="Ví dụ: Họp vào tháng 8/2026..." />
              </div>
            </div>

            <button class="generate-btn" @click="generateDraft" :disabled="loading">
              <Loader2 v-if="loading" class="spin" :size="18" />
              <FileText v-else :size="18" />
              {{ loading ? 'Đang soạn thảo...' : 'Tạo văn bản bằng AI' }}
            </button>

            <div v-if="error" class="error-box">{{ error }}</div>

            <div v-if="draftText" class="draft-output">
              <div class="draft-toolbar">
                <span class="draft-label">Văn bản đã soạn</span>
                <button class="copy-btn" @click="copyText">
                  <Check v-if="copied" :size="16" />
                  <Copy v-else :size="16" />
                  {{ copied ? 'Đã sao chép!' : 'Sao chép' }}
                </button>
              </div>
              <textarea class="draft-textarea" :value="draftText" readonly rows="16" />
            </div>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-box {
  background: #111214;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px;
  width: 100%;
  max-width: 680px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 1rem;
  font-weight: 600;
  color: white;
}

.close-btn {
  background: rgba(255,255,255,0.05);
  border: none;
  color: rgba(255,255,255,0.5);
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.close-btn:hover { background: rgba(255,255,255,0.1); color: white; }

.modal-body {
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.candidate-preview {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 0.875rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.preview-label { font-size: 0.75rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.06em; }
.candidate-preview strong { font-size: 0.95rem; color: white; }
.preview-sub { font-size: 0.8rem; color: rgba(255,255,255,0.45); margin-left: auto; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-group label { font-size: 0.78rem; color: rgba(255,255,255,0.5); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }

.form-group input,
.select-wrapper select {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 0.6rem 0.875rem;
  color: white;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
  box-sizing: border-box;
}
.form-group input:focus,
.select-wrapper select:focus { border-color: rgba(255,255,255,0.3); }

.select-wrapper { position: relative; }
.select-wrapper select { appearance: none; padding-right: 2.2rem; cursor: pointer; }
.select-icon { position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.4); pointer-events: none; }

.generate-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  background: linear-gradient(135deg, #4f8ef7 0%, #6c63ff 100%);
  border: none;
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
  padding: 0.75rem 1.5rem;
  border-radius: 12px;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.generate-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.generate-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.error-box {
  background: rgba(220, 53, 69, 0.1);
  border: 1px solid rgba(220, 53, 69, 0.25);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  color: #f77;
  font-size: 0.875rem;
}

.draft-output { display: flex; flex-direction: column; gap: 0.75rem; }
.draft-toolbar { display: flex; justify-content: space-between; align-items: center; }
.draft-label { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: rgba(255,255,255,0.4); font-weight: 500; }

.copy-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.7);
  padding: 0.4rem 0.875rem;
  border-radius: 8px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}
.copy-btn:hover { background: rgba(255,255,255,0.1); color: white; }

.draft-textarea {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  color: rgba(255,255,255,0.85);
  font-size: 0.875rem;
  line-height: 1.75;
  padding: 1rem 1.125rem;
  resize: vertical;
  width: 100%;
  box-sizing: border-box;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-active .modal-box { transition: transform 0.2s; }
.modal-fade-enter-from .modal-box { transform: translateY(20px); }

@media (max-width: 600px) {
  .form-row { grid-template-columns: 1fr; }
}
</style>