<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'
import DressCard from '../components/DressCard.vue'

const store = useInventoryStore()
const route = useRoute()
const router = useRouter()

const query = ref(store.search)
const archived = computed(() => route.query.archived === 'true')
let debounce

watch(query, (value) => {
  clearTimeout(debounce)
  debounce = setTimeout(() => store.fetchDresses(value, archived.value).catch(() => {}), 250)
})

watch(archived, (value) => store.fetchDresses(query.value, value).catch(() => {}))

function toggleArchived(value) {
  router.push({ name: 'dresses', query: value ? { archived: 'true' } : {} })
}

onMounted(async () => {
  await store.loadStatuses().catch(() => {})
  await store.fetchDresses(query.value, archived.value).catch(() => {})
})
</script>

<template>
  <section class="space-y-4">
    <div class="flex items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">
          {{ archived ? 'Archived dresses' : 'Dresses' }}
        </h1>
        <p class="text-sm text-stone-500">{{ store.dresses.length }} style(s)</p>
      </div>
      <RouterLink
        v-if="!archived"
        :to="{ name: 'dress-new' }"
        class="rounded-lg bg-blush-600 px-4 py-2 text-sm text-white hover:bg-blush-700"
      >
        Add dress
      </RouterLink>
    </div>

    <div class="flex gap-1 rounded-lg bg-stone-100 p-1 w-fit text-sm">
      <button
        type="button"
        class="rounded-md px-3 py-1.5 transition-colors"
        :class="!archived ? 'bg-white shadow-sm font-medium' : 'text-stone-500'"
        @click="toggleArchived(false)"
      >
        Active
      </button>
      <button
        type="button"
        class="rounded-md px-3 py-1.5 transition-colors"
        :class="archived ? 'bg-white shadow-sm font-medium' : 'text-stone-500'"
        @click="toggleArchived(true)"
      >
        Archived
      </button>
    </div>

    <input
      v-model="query"
      type="search"
      placeholder="Search code, style or supplier…"
      class="w-full rounded-lg border border-stone-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blush-300"
    />

    <p v-if="store.loading && !store.dresses.length" class="text-sm text-stone-500">Loading…</p>

    <div
      v-else-if="!store.dresses.length"
      class="rounded-xl border border-dashed border-stone-300 p-10 text-center"
    >
      <p class="text-stone-500">
        {{ query ? 'No dresses match that search.' : archived ? 'No archived dresses.' : 'No dresses yet.' }}
      </p>
      <RouterLink
        v-if="!query && !archived"
        :to="{ name: 'dress-new' }"
        class="mt-3 inline-block text-sm text-blush-700 underline"
      >
        Add your first dress
      </RouterLink>
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      <DressCard v-for="dress in store.dresses" :key="dress.id" :dress="dress" />
    </div>
  </section>
</template>
