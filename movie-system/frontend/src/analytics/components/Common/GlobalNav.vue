<template>
  <nav class="webbar" aria-label="Global">
    <div class="brand">🎬 Movie Analytics</div>
    <div class="rail">
      <button class="link active">数据分析</button>
      <button class="link">推荐系统</button>
      <button class="link">数据管理</button>
    </div>
    <div class="actions">
      <button class="link" aria-label="搜索">🔍</button>
      <button class="link" aria-label="主题切换" @click="toggleTheme">🌓</button>
    </div>
  </nav>
</template>

<script setup>
function toggleTheme() {
  document.documentElement.classList.toggle('dark')
}
</script>

<style scoped>
.webbar {
  position: sticky;
  top: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(var(--spacing) * 2);
  width: 100%;
  height: 44px;
  padding: 0 calc(var(--spacing) * 3);
  background: var(--sidebar);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.brand {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
  color: var(--sidebar-foreground);
}

.rail {
  display: flex;
  align-items: center;
  gap: calc(var(--spacing) * 1.5);
}

.actions {
  display: flex;
  align-items: center;
  gap: calc(var(--spacing) * 1.5);
}

.link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  padding: 0 calc(var(--spacing) * 2.5);
  border-radius: 999px;
  color: inherit;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: -0.01em;
  text-decoration: none;
  white-space: nowrap;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease, opacity 0.18s ease;
}

.link:hover {
  background: var(--secondary);
}

.link:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

.link.active {
  color: var(--sidebar-primary);
  font-weight: 600;
}

.link.active:hover {
  background: var(--sidebar-accent);
}

@media (max-width: 832px) {
  .webbar {
    padding: 0 calc(var(--spacing) * 2);
  }
  
  .brand {
    font-size: 10px;
  }
  
  .link {
    padding: 0 calc(var(--spacing) * 2);
    font-size: 12px;
  }
}
</style>
