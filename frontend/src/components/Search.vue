<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { Search as SearchIcon, Rocket, Brain, Loader2 } from 'lucide-vue-next'
import CandidateCard from './CandidateCard.vue'

const query = ref('')
const topK = ref(5)
const mode = ref('in') // 'in' or 'out'
const searchType = ref('faiss') // 'faiss' or 'llm'
const results = ref([])
const llmAnalysis = ref('')
const loading = ref(false)
const error = ref('')

const handleSearch = async () => {
  if (!query.value.trim()) return
  
  loading.value = true
  error.value = ''
  results.value = []
  llmAnalysis.value = ''
  
  try {
    const endpoint = searchType.value === 'faiss' 
      ? 'semantic_search' 
      : 'semantic_search_llm'
    
    const response = await axios.get(`/api/method/ct_datalake.api.${endpoint}`, {
      params: {
        query: query.value,
        mode: mode.value,
        top_k: topK.value
      }
    })
    
    const data = response.data.message
    
    if (searchType.value === 'faiss') {
      results.value = data.results
    } else {
      llmAnalysis.value = data.llm_analysis
    }
    
    if (!results.value.length && !llmAnalysis.value) {
      error.value = 'Không tìm thấy kết quả phù hợp'
    }
  } catch (e) {
    error.value = 'Đã xảy ra lỗi khi tìm kiếm: ' + (e.response?.data?.message || e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="search-section">
    <div class="glass-card search-controls">
      <div class="header-row">
        <div class="title-with-icon">
          <SearchIcon class="icon-accent" :size="24" />
          <h2>Semantic Search</h2>
        </div>
      </div>

      <div class="search-form">
        <div class="input-row">
          <div class="input-group flex-grow">
            <label class="label">Nhập yêu cầu</label>
            <div class="input-with-icon">
              <input 
                type="text" 
                v-model="query" 
                placeholder="Ví dụ: AI engineer, NLP, fintech, professor robotics..."
                @keyup.enter="handleSearch"
              />
            </div>
          </div>
          <div class="input-group width-small">
            <label class="label">Top K</label>
            <input type="number" v-model="topK" min="1" max="20" />
          </div>
        </div>

        <div class="options-row">
          <div class="input-group">
            <label class="label">Nguồn dữ liệu</label>
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
            <label class="label">Chế độ</label>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" value="faiss" v-model="searchType" />
                <span>⚡ FAISS</span>
              </label>
              <label class="radio-item">
                <input type="radio" value="llm" v-model="searchType" />
                <span>🧠 LLM</span>
              </label>
            </div>
          </div>
        </div>

        <button @click="handleSearch" class="btn btn-primary btn-block" :disabled="loading">
          <Loader2 v-if="loading" class="animate-spin" :size="20" />
          <Rocket v-else :size="20" />
          <span>{{ loading ? 'Đang tìm kiếm...' : 'Search' }}</span>
        </button>
      </div>
    </div>

    <div v-if="error" class="error-msg glass-card">
      {{ error }}
    </div>

    <div v-if="llmAnalysis" class="analysis-results glass-card fade-in">
      <h3><Brain :size="20" /> LLM Analysis</h3>
      <div class="markdown-content">{{ llmAnalysis }}</div>
    </div>

    <div v-if="results.length" class="results-list">
      <div class="results-header">
        <p>Tìm thấy <strong>{{ results.length }}</strong> ứng viên phù hợp</p>
      </div>
      <CandidateCard 
        v-for="(res, index) in results" 
        :key="index"
        :index="index + 1"
        :candidate="res.candidate"
        :score="res.faiss_score"
        :mode="mode"
      />
    </div>
  </section>
</template>

<style scoped>
.search-controls {
  margin-bottom: 2rem;
}

.header-row {
  margin-bottom: 1.5rem;
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.icon-accent {
  color: var(--accent-color);
}

.input-row {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
}

.flex-grow {
  flex: 1;
}

.width-small {
  width: 100px;
}

.options-row {
  display: flex;
  gap: 3rem;
  margin-bottom: 1.5rem;
}

.btn-block {
  width: 100%;
}

.error-msg {
  color: var(--danger-color);
  border-color: rgba(220, 53, 69, 0.2);
  margin-bottom: 2rem;
}

.analysis-results {
  margin-bottom: 2rem;
  border-left: 4px solid #ffaa44;
}

.analysis-results h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #ffaa44;
}

.markdown-content {
  white-space: pre-wrap;
  font-size: 1.05rem;
  line-height: 1.7;
}

.results-header {
  margin-bottom: 1rem;
  color: var(--text-secondary);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .input-row, .options-row {
    flex-direction: column;
    gap: 1rem;
  }
  .width-small {
    width: 100%;
  }
}
</style>
