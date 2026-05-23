<script setup>
import { ref } from 'vue'
import { GraduationCap, Building2, MapPin, Mail, BookOpen, TrendingUp, Link as LinkIcon, User, FileEdit } from 'lucide-vue-next'
import DraftModal from './DraftModal.vue'

const props = defineProps({
  candidate: Object,
  score: Number,
  mode: String,
  index: Number
})

const d = props.candidate
const showDraftModal = ref(false)
</script>

<template>
  <div class="glass-card candidate-card fade-in">
    <div class="card-header">
      <div class="candidate-info">
        <div class="avatar">
          <User :size="24" />
        </div>
        <div class="name-section">
          <h3 class="name">#{{ index }} {{ d.name || d['trường họ và tên'] || 'Unknown Candidate' }}</h3>
          <span class="source-tag" :class="mode">{{ mode === 'in' ? '🏫 Nội bộ' : '🌐 Google Scholar' }}</span>
        </div>
      </div>
      <div class="score-section">
        <div class="metric-box">
          <div class="small-label">Score</div>
          <div class="big-value">{{ score }}</div>
        </div>
      </div>
    </div>

    <div class="card-body">
      <!-- Internal Layout -->
      <template v-if="mode === 'in'">
        <div class="info-grid">
          <div class="info-item" v-if="d.school || d['trường']">
            <GraduationCap :size="16" />
            <span>{{ d.school || d['trường'] }}</span>
          </div>
          <div class="info-item" v-if="d.position || d['chức vụ']">
            <Building2 :size="16" />
            <span>{{ d.position || d['chức vụ'] }}</span>
          </div>
          <div class="info-item" v-if="d.degree || d['học vị']">
            <GraduationCap :size="16" />
            <span>{{ d.academic_rank || d['học hàm'] }} {{ d.degree || d['học vị'] }}</span>
          </div>
        </div>
        <div class="expertise-section" v-if="d.expertise || d['sản phẩm thực hiện']">
          <h4>🧠 Mô tả nghiên cứu / sản phẩm</h4>
          <p class="expertise-text">{{ d.expertise || d['sản phẩm thực hiện'] }}</p>
        </div>
      </template>

      <!-- External Layout -->
      <template v-else>
        <div class="info-grid">
          <div class="info-item" v-if="d.affiliation">
            <Building2 :size="16" />
            <span>{{ d.affiliation }}</span>
          </div>
          <div class="info-item" v-if="d.university_name">
            <GraduationCap :size="16" />
            <span>{{ d.university_name }} ({{ d.university_abbr }})</span>
          </div>
          <div class="info-item" v-if="d.city">
            <MapPin :size="16" />
            <span>{{ d.city }}</span>
          </div>
          <div class="info-item" v-if="d.email">
            <Mail :size="16" />
            <span>{{ d.email }}</span>
          </div>
        </div>

        <div class="stats-row">
          <div class="stat-item">
            <BookOpen :size="16" />
            <span>Citations: <strong>{{ d.citations }}</strong></span>
          </div>
          <div class="stat-item">
            <TrendingUp :size="16" />
            <span>h-index: <strong>{{ d.h_index }}</strong></span>
          </div>
        </div>

        <div class="interests-section" v-if="d.interests && d.interests.length">
          <h4>🔬 Research Interests</h4>
          <div class="tags-container">
            <span v-for="tag in d.interests" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>

        <a v-if="d.url" :href="d.url" target="_blank" class="btn btn-secondary scholar-btn">
          <LinkIcon :size="16" />
          <span>Google Scholar Profile</span>
        </a>
      </template>
    </div>

    <!-- Draft Button -->
    <div class="card-footer">
      <button class="draft-btn" @click="showDraftModal = true">
        <FileEdit :size="16" />
        <span>Soạn thảo văn bản mời</span>
      </button>
    </div>

    <!-- Draft Modal -->
    <DraftModal
      :candidate="d"
      :mode="mode"
      :visible="showDraftModal"
      @close="showDraftModal = false"
    />
  </div>
</template>

<style scoped>
.candidate-card {
  margin-bottom: 1.5rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.candidate-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-color);
}

.name {
  margin: 0;
  font-size: 1.25rem;
}

.source-tag {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.source-tag.in {
  background: rgba(40, 167, 69, 0.15);
  color: #71dd8a;
}

.source-tag.out {
  background: rgba(0, 123, 255, 0.15);
  color: #70b9ff;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.expertise-section, .interests-section {
  margin-top: 1.5rem;
}

h4 {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.expertise-text {
  font-size: 0.95rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.03);
  border-left: 3px solid var(--accent-color);
  border-radius: 4px;
}

.stats-row {
  display: flex;
  gap: 2rem;
  margin: 1rem 0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.scholar-btn {
  margin-top: 1.5rem;
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--card-border);
  color: white;
}

.scholar-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* Draft button footer */
.card-footer {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  justify-content: flex-end;
}

.draft-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(79, 142, 247, 0.12);
  border: 1px solid rgba(79, 142, 247, 0.3);
  color: #7eb3ff;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.draft-btn:hover {
  background: rgba(79, 142, 247, 0.22);
  border-color: rgba(79, 142, 247, 0.55);
  color: #aaccff;
  transform: translateY(-1px);
}
</style>