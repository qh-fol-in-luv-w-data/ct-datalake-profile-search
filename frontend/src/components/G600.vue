<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { ClipboardList, Upload, Rocket, Loader2, FileCheck, ChevronDown, ChevronUp } from 'lucide-vue-next'
import CandidateCard from './CandidateCard.vue'

const selectedFile = ref(null)
const topK = ref(5)
const source = ref('both')
const scoreThreshold = ref(0.40)
const loading = ref(false)
const error = ref('')
const results = ref(null)
const expandedDomains = ref({})

const onFileChange = (e) => {
  selectedFile.value = e.target.files[0]
}

const handleAnalyze = async () => {
  if (!selectedFile.value) {
    error.value = 'Vui lòng upload file PDF tờ trình'
    return
  }

  loading.value = true
  error.value = ''
  results.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('source', source.value)
    formData.append('top_k', topK.value)
    formData.append('score_threshold', scoreThreshold.value)

    const response = await axios.post('/api/method/ct_datalake.api.g600_analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    results.value = response.data.message
    // Expand all by default
    results.value.domains.forEach((_, idx) => {
      expandedDomains.value[idx] = true
    })
  } catch (e) {
    error.value = 'Đã xảy ra lỗi: ' + (e.response?.data?.message || e.message)
  } finally {
    loading.value = false
  }
}

const toggleDomain = (idx) => {
  expandedDomains.value[idx] = !expandedDomains.value[idx]
}
</script>

<template>
  <section class="g600-section">
    <div class="glass-card controls-card">
      <div class="title-with-icon">
        <ClipboardList class="icon-accent" :size="24" />
        <h2>Đề xuất ứng viên từ Tờ trình G600</h2>
      </div>
      <p class="subtitle">Upload PDF tờ trình → GPT trích xuất lĩnh vực → FAISS tìm ứng viên phù hợp</p>

      <div class="upload-area" :class="{ active: selectedFile }">
        <input type="file" id="g600-upload" @change="onFileChange" hidden accept=".pdf" />
        <label for="g600-upload" class="upload-label">
          <Upload v-if="!selectedFile" :size="32" />
          <FileCheck v-else :size="32" class="success-icon" />
          <span>{{ selectedFile ? selectedFile.name : 'Upload tờ trình PDF' }}</span>
        </label>
      </div>

      <div class="options-grid">
        <div class="input-group">
          <label class="label">Top K mỗi lĩnh vực</label>
          <input type="range" v-model="topK" min="1" max="10" class="slider" />
          <div class="slider-value">{{ topK }}</div>
        </div>

        <div class="input-group">
          <label class="label">Nguồn dữ liệu</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" value="in" v-model="source" />
              <span>🏢 Nội bộ</span>
            </label>
            <label class="radio-item">
              <input type="radio" value="out" v-model="source" />
              <span>🌐 Bên ngoài</span>
            </label>
            <label class="radio-item">
              <input type="radio" value="both" v-model="source" />
              <span>🔀 Cả hai</span>
            </label>
          </div>
        </div>
      </div>

      <button @click="handleAnalyze" class="btn btn-primary btn-block" :disabled="loading">
        <Loader2 v-if="loading" class="animate-spin" :size="20" />
        <Rocket v-else :size="20" />
        <span>{{ loading ? 'Đang phân tích & Đề xuất...' : 'Phân tích & Đề xuất ứng viên' }}</span>
      </button>
    </div>

    <div v-if="error" class="error-msg glass-card">
      {{ error }}
    </div>

    <div v-if="results" class="results-container">
      <div class="results-summary">
        <p>✅ Tìm thấy <strong>{{ results.total_domains }} lĩnh vực</strong> cần tuyển chuyên gia</p>
      </div>

      <div v-for="(domain, dIdx) in results.domains" :key="dIdx" class="domain-block">
        <div class="domain-header" @click="toggleDomain(dIdx)">
          <div class="domain-title-group">
            <h3>🔬 {{ domain.domain_name }}</h3>
            <div class="domain-stats">
              <span class="domain-tag">{{ domain.total_candidates }} ứng viên</span>
            </div>
          </div>
          <component :is="expandedDomains[dIdx] ? ChevronUp : ChevronDown" :size="20" />
        </div>

        <div v-if="expandedDomains[dIdx]" class="domain-content fade-in">
          <div class="domain-meta">
            <div class="keywords-row">
              <span v-for="kw in domain.keywords_en.slice(0, 6)" :key="kw" class="kw-badge">{{ kw }}</span>
              <span v-for="kw in domain.keywords_vi.slice(0, 4)" :key="kw" class="tag">{{ kw }}</span>
            </div>
            <div class="queries">
              <p class="caption">Query VI: <code>{{ domain.query_vi }}</code></p>
              <p class="caption">Query EN: <code>{{ domain.query_en }}</code></p>
            </div>
          </div>

          <div class="candidates-list" v-if="domain.candidates.length">
            <CandidateCard 
              v-for="(hit, cIdx) in domain.candidates" 
              :key="cIdx"
              :index="cIdx + 1"
              :candidate="hit.candidate"
              :score="hit.faiss_score"
              :mode="hit.source.includes('Scholar') ? 'out' : 'in'"
            />
          </div>
          <div v-else class="no-candidates">
            <p>Không tìm thấy ứng viên phù hợp (score thấp hơn ngưỡng)</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.controls-card {
  margin-bottom: 2rem;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.upload-area {
  border: 2px dashed var(--card-border);
  border-radius: 12px;
  padding: 2.5rem;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
}

.upload-area:hover {
  border-color: var(--accent-color);
  background: rgba(255, 255, 255, 0.02);
}

.upload-area.active {
  border-color: var(--success-color);
  background: rgba(40, 167, 69, 0.05);
}

.upload-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
}

.success-icon {
  color: var(--success-color);
}

.options-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
  margin: 2rem 0;
}

.slider {
  width: 100%;
  accent-color: var(--accent-color);
}

.slider-value {
  text-align: center;
  font-weight: 700;
  color: var(--accent-color);
}

.btn-block {
  width: 100%;
}

.results-summary {
  margin-bottom: 1.5rem;
}

.domain-block {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  margin-bottom: 1rem;
  overflow: hidden;
}

.domain-header {
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: background 0.2s;
}

.domain-header:hover {
  background: rgba(255, 255, 255, 0.02);
}

.domain-title-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.domain-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.domain-tag {
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.domain-content {
  padding: 0 1.5rem 1.5rem 1.5rem;
  border-top: 1px solid var(--card-border);
}

.domain-meta {
  padding: 1rem 0;
  margin-bottom: 1rem;
}

.keywords-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.caption {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin: 2px 0;
}

code {
  background: rgba(0, 0, 0, 0.3);
  padding: 1px 4px;
  border-radius: 3px;
}

.candidates-list {
  margin-top: 1rem;
}

.no-candidates {
  padding: 2rem;
  text-align: center;
  color: var(--warning-color);
  background: rgba(255, 193, 7, 0.05);
  border-radius: 12px;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .options-grid {
    grid-template-columns: 1fr;
  }
}
</style>
