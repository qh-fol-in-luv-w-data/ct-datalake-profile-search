<script setup>
import { ref } from 'vue'
import Search from './components/Search.vue'
import JDMatch from './components/JDMatch.vue'
import G600 from './components/G600.vue'
import { Search as SearchIcon, FileText, ClipboardList } from 'lucide-vue-next'

const currentTab = ref('search')
</script>

<template>
  <div class="app-container">
    <header class="header">
      <div class="container header-content">
        <div class="logo">
          <span class="logo-icon">🔍</span>
          <div class="logo-text">
            <h1>AI Candidate Search</h1>
            <p>Semantic Search + JD Matching + LLM Ranking</p>
          </div>
        </div>
        <nav class="nav">
          <button 
            @click="currentTab = 'search'" 
            :class="['nav-btn', { active: currentTab === 'search' }]"
          >
            <SearchIcon :size="18" />
            <span>Search</span>
          </button>
          <button 
            @click="currentTab = 'jd'" 
            :class="['nav-btn', { active: currentTab === 'jd' }]"
          >
            <FileText :size="18" />
            <span>JD Match</span>
          </button>
          <button 
            @click="currentTab = 'g600'" 
            :class="['nav-btn', { active: currentTab === 'g600' }]"
          >
            <ClipboardList :size="18" />
            <span>G600</span>
          </button>
        </nav>
      </div>
    </header>

    <main class="container">
      <div v-if="currentTab === 'search'" class="fade-in">
        <Search />
      </div>
      <div v-if="currentTab === 'jd'" class="fade-in">
        <JDMatch />
      </div>
      <div v-if="currentTab === 'g600'" class="fade-in">
        <G600 />
      </div>
    </main>

    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 CT DataLake AI. Powered by Frappe & GPT-4o.</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  border-bottom: 1px solid var(--card-border);
  background: rgba(5, 5, 5, 0.8);
  backdrop-filter: blur(20px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo-icon {
  font-size: 2rem;
}

.logo-text h1 {
  font-size: 1.25rem;
  margin: 0;
}

.logo-text p {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0;
}

.nav {
  display: flex;
  gap: 0.5rem;
}

.nav-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  transition: all 0.2s;
}

.nav-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.nav-btn.active {
  background: var(--card-bg);
  color: white;
  box-shadow: 0 0 0 1px var(--card-border);
}

.footer {
  margin-top: auto;
  padding: 2rem 0;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.875rem;
  border-top: 1px solid var(--card-border);
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>
