<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { computed, onMounted } from 'vue'
import { useInventoryStore } from './stores/inventory'

const store = useInventoryStore()
const route = useRoute()

// No dedicated "Add" tab — each of Dresses/Secondhand has its own add
// button on the list page, and a nav-level shortcut only ever pointed at
// the "new" category, which stopped making sense once secondhand existed.
const tabs = [
  { name: 'dashboard', label: 'Dashboard', icon: '◱' },
  { name: 'dresses', label: 'Dresses', icon: '❖' },
  { name: 'secondhand', label: 'Secondhand', icon: '⟲' },
]

// Detail and edit pages live "under" their list, so keep that tab lit.
const activeTab = computed(() => {
  const name = String(route.name || '')
  if (name.startsWith('secondhand')) return 'secondhand'
  if (name.startsWith('dress-detail') || name === 'dress-edit') return 'dresses'
  return route.name
})

onMounted(() => store.loadStatuses().catch(() => {}))
</script>

<template>
  <div class="min-h-dvh flex flex-col">
    <header class="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-stone-200">
      <div class="mx-auto max-w-5xl px-4 h-14 flex items-center justify-between gap-4">
        <RouterLink to="/" class="font-semibold tracking-tight text-blush-700">
          Dress Inventory
        </RouterLink>

        <nav class="hidden sm:flex items-center gap-1">
          <RouterLink
            v-for="tab in tabs"
            :key="tab.name"
            :to="{ name: tab.name }"
            class="px-3 py-1.5 rounded-full text-sm transition-colors"
            :class="
              activeTab === tab.name
                ? 'bg-blush-100 text-blush-800 font-medium'
                : 'text-stone-600 hover:bg-stone-100'
            "
          >
            {{ tab.label }}
          </RouterLink>
        </nav>
      </div>
    </header>

    <p
      v-if="store.error"
      class="mx-auto max-w-5xl w-full px-4 mt-3 text-sm text-blush-800 bg-blush-100 border border-blush-200 rounded-lg py-2 flex items-start gap-2"
    >
      <span class="grow">{{ store.error }}</span>
      <button class="shrink-0 underline" @click="store.clearError()">dismiss</button>
    </p>

    <main class="mx-auto max-w-5xl w-full px-4 py-5 grow pb-24 sm:pb-8">
      <RouterView />
    </main>

    <nav
      class="sm:hidden fixed bottom-0 inset-x-0 z-20 bg-white border-t border-stone-200 pb-[env(safe-area-inset-bottom)]"
    >
      <div class="grid grid-cols-3">
        <RouterLink
          v-for="tab in tabs"
          :key="tab.name"
          :to="{ name: tab.name }"
          class="py-2.5 flex flex-col items-center gap-0.5 text-xs"
          :class="activeTab === tab.name ? 'text-blush-700 font-medium' : 'text-stone-500'"
        >
          <span class="text-lg leading-none">{{ tab.icon }}</span>
          {{ tab.label }}
        </RouterLink>
      </div>
    </nav>
  </div>
</template>
