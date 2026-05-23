<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { FileText, Upload, Rocket, Loader2, FileCheck } from 'lucide-vue-next'
import CandidateCard from './CandidateCard.vue'

const jdText = ref('')
const topK = ref(5)
const mode = ref('in')
const fastMode = ref(false)
const selectedFile = ref(null)
const loading = ref(false)
const error = ref('')
const results = ref(null)

const onFileChange = (e) => {
  selectedFile.value = e.target.files[0]
}

const handleMatch = async () => {
  if (!jdText.value.trim() && !selectedFile.value) {
    error.value = 'Vui lòng upload hoặc nhập JD'
    return
  }

  loading.value = true
  error.value = ''
  results.value = null

  try {
    let response
    if (selectedFile.value) {
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      formData.append('mode', mode.value)
      formData.append('top_k', topK.value)
      formData.append('fast', fastMode.value)
      
      response = await axios.post('/api/method/ct_datalake.ct_datalake.api.jd_match_upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    } else {
      response = await axios.post('/api/method/ct_datalake.ct_datalake.api.jd_match', null, {
        params: {
          jd_text: jdText.value,
          mode: mode.value,
          top_k: topK.value,
          fast: fastMode.value
        }
      })
    }

    results.value = response.data.message
  } catch (e) {
    error.value = 'Đã xảy ra lỗi: ' + (e.response?.data?.message || e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="jd-match-section">
    <div class="glass-card controls-card">
      <div class="title-with-icon">
        <FileText class="icon-accent" :size="24" />
        <h2>JD Matching</h2>
      </div>

      <div class="options-grid">
        <div class="input-group">
          <label class="label">Nguồn dữ liệu JD</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" value="in" v-model="mode" />
              <span>🏢 Nội bộ</span>
            </label>
            <label class="radio-item">
              <input type="radio" value="out" v-model="mode" />
              <span>🌐 Bên ngoài</span>
            </label>
          </div>
        </div>

        <div class="input-group">
          <label class="label">Top ứng viên</label>
          <input type="range" v-model="topK" min="1" max="20" class="slider" />
          <div class="slider-value">{{ topK }}</div>
        </div>

        <div class="input-group">
          <label class="label">Chế độ</label>
          <label class="checkbox-item">
            <input type="checkbox" v-model="fastMode" />
            <span>⚡ Fast mode (không rerank LLM)</span>
          </label>
        </div>
      </div>

      <div class="input-section">
        <div class="upload-area" :class="{ active: selectedFile }">
          <input type="file" id="jd-upload" @change="onFileChange" hidden accept=".pdf,.docx,.txt,.md" />
          <label for="jd-upload" class="upload-label">
            <Upload v-if="!selectedFile" :size="32" />
            <FileCheck v-else :size="32" class="success-icon" />
            <span>{{ selectedFile ? selectedFile.name : 'Upload PDF / DOCX / TXT' }}</span>
          </label>
          <button v-if="selectedFile" @click="selectedFile = null" class="clear-btn">Clear</button>
        </div>

        <div class="divider"><span>HOẶC</span></div>

        <textarea 
          v-model="jdText" 
          placeholder="Dán nội dung JD vào đây..." 
          rows="8"
          class="jd-textarea"
          :disabled="!!selectedFile"
        ></textarea>
      </div>

      <button @click="handleMatch" class="btn btn-primary btn-block" :disabled="loading">
        <Loader2 v-if="loading" class="animate-spin" :size="20" />
        <Rocket v-else :size="20" />
        <span>{{ loading ? 'Đang phân tích...' : 'Match JD' }}</span>
      </button>
    </div>

    <div v-if="error" class="error-msg glass-card">
      {{ error }}
    </div>

    <div v-if="results" class="results-container">
      <div v-if="results.parsed_jd" class="parsed-jd glass-card fade-in">
        <h3>📋 Phân tích JD</h3>
        <div class="jd-info-grid">
          <div class="jd-item" v-if="results.parsed_jd.title">
            <strong>Vị trí:</strong> {{ results.parsed_jd.title }}
          </div>
          <div class="jd-item" v-if="results.parsed_jd.years_experience">
            <strong>Kinh nghiệm:</strong> {{ results.parsed_jd.years_experience }}
          </div>
        </div>
        <div class="keywords-list" v-if="results.parsed_jd.keywords && results.parsed_jd.keywords.length">
          <span v-for="kw in results.parsed_jd.keywords" :key="kw" class="kw-badge">{{ kw }}</span>
        </div>
      </div>

      <div class="results-list" v-if="results.candidates && results.candidates.length">
        <h3>🎯 Kết quả Matching</h3>
        <CandidateCard 
          v-for="(candidate, index) in results.candidates" 
          :key="index"
          :index="index + 1"
          :candidate="candidate.candidate"
          :score="candidate.faiss_score"
          :mode="mode"
        />
      </div>
      <div v-else-if="!loading" class="no-results glass-card">
        Không tìm thấy ứng viên phù hợp.
      </div>
    </div>
  </section>
</template>

<style scoped>
.controls-card {
  margin-bottom: 2rem;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  margin: 1.5rem 0;
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

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  margin-top: 0.5rem;
}

.input-section {
  margin-bottom: 1.5rem;
}

.upload-area {
  border: 2px dashed var(--card-border);
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  transition: all 0.2s;
  position: relative;
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
  color: var(--text-secondary);
}

.success-icon {
  color: var(--success-color);
}

.clear-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  cursor: pointer;
}

.divider {
  text-align: center;
  margin: 1.5rem 0;
  position: relative;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--card-border);
  z-index: 1;
}

.divider span {
  background: var(--bg-color);
  padding: 0 1rem;
  position: relative;
  z-index: 2;
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 600;
}

.jd-textarea {
  resize: vertical;
}

.btn-block {
  width: 100%;
}

.parsed-jd {
  margin-bottom: 2rem;
  border-left: 4px solid var(--success-color);
}

.jd-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin: 1rem 0;
}

.keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.no-results {
  text-align: center;
  color: var(--text-secondary);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
