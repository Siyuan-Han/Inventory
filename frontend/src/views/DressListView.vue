<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'
import DressCard from '../components/DressCard.vue'

const store = useInventoryStore()
const query = ref(store.search)
let debounce

watch(query, (value) => {
  clearTimeout(debounce)
  debounce = setTimeout(() => store.fetchDresses(value).catch(() => {}), 250)
})

onMounted(async () => {
  await store.loadStatuses().catch(() => {})
  await store.fetchDresses(query.value).catch(() => {})
})
</script>

<template>
  <section class="space-y-4">
    <div class="flex items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Dresses</h1>
        <p class="text-sm text-stone-500">{{ store.dresses.length }} style(s)</p>
      </div>
      <RouterLink
        :to="{ name: 'dress-new' }"
        class="rounded-lg bg-blush-600 px-4 py-2 text-sm text-white hover:bg-blush-700"
      >
        Add dress
      </RouterLink>
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
        {{ query ? 'No dresses match that search.' : 'No dresses yet.' }}
      </p>
      <RouterLink
        v-if="!query"
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
