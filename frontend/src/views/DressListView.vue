<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'
import DressCard from '../components/DressCard.vue'

const props = defineProps({
  category: { type: String, default: 'new' }, // 'new' | 'secondhand'
})

const store = useInventoryStore()
const route = useRoute()
const router = useRouter()

const isSecondhand = computed(() => props.category === 'secondhand')
const listRouteName = computed(() => (isSecondhand.value ? 'secondhand' : 'dresses'))
const addRouteName = computed(() => (isSecondhand.value ? 'secondhand-new' : 'dress-new'))
const noun = computed(() => (isSecondhand.value ? 'secondhand piece' : 'dress'))

const query = ref(store.search)
const archived = computed(() => route.query.archived === 'true')
const supplier = computed(() => route.query.supplier || '')
const status = computed(() => route.query.status || '')
const hasFilters = computed(() => Boolean(supplier.value || status.value))
let debounce

function currentFilters() {
  return {
    search: query.value,
    archived: archived.value,
    supplier: supplier.value,
    status: status.value,
    category: props.category,
  }
}

function refetch() {
  return store.fetchDresses(currentFilters()).catch(() => {})
}

watch(query, () => {
  clearTimeout(debounce)
  debounce = setTimeout(refetch, 250)
})

watch([archived, supplier, status], refetch)

// /dresses and /secondhand both render this same component, so Vue Router
// reuses one instance across the two routes instead of remounting — the
// category prop changes, but onMounted (below) only fires once. Without
// this watcher, switching tabs would keep showing whichever list loaded
// first, since nothing else re-triggers a fetch.
watch(
  () => props.category,
  () => {
    query.value = ''
    store.fetchSuppliers(props.category).catch(() => {})
    refetch()
  },
)

function toggleArchived(value) {
  router.push({ name: listRouteName.value, query: { ...route.query, archived: value ? 'true' : undefined } })
}

function setSupplier(value) {
  router.push({ name: listRouteName.value, query: { ...route.query, supplier: value || undefined } })
}

function setStatus(value) {
  router.push({ name: listRouteName.value, query: { ...route.query, status: value || undefined } })
}

function clearFilters() {
  router.push({ name: listRouteName.value, query: { archived: route.query.archived } })
}

// --- Bulk select (secondhand only): pick several pieces sitting at the same
// status filter, then advance them all to the next stage together. ---
const selectedIds = ref(new Set())
const bulkDate = ref(new Date().toISOString().slice(0, 10))

const canBulkSelect = computed(() => isSecondhand.value && Boolean(status.value) && !archived.value)
const bulkTarget = computed(() => (status.value ? store.nextStatus(status.value) : null))
const selectedCount = computed(() => selectedIds.value.size)
const allVisibleSelected = computed(
  () => store.dresses.length > 0 && store.dresses.every((d) => selectedIds.value.has(d.id)),
)

function clearSelection() {
  selectedIds.value = new Set()
}

// A selection only makes sense within one status filter's results — drop it
// whenever the visible set could change under it.
watch([status, archived, () => props.category], clearSelection)

function toggleSelect(dressId) {
  const next = new Set(selectedIds.value)
  if (next.has(dressId)) next.delete(dressId)
  else next.add(dressId)
  selectedIds.value = next
}

function toggleSelectAll() {
  selectedIds.value = allVisibleSelected.value
    ? new Set()
    : new Set(store.dresses.map((d) => d.id))
}

async function confirmBulkAdvance() {
  if (!bulkTarget.value) return
  const orderIds = store.dresses
    .filter((d) => selectedIds.value.has(d.id))
    .map((d) => d.latest_order_id)
    .filter((id) => id != null)
  if (!orderIds.length) return

  await store.bulkAdvanceOrders(orderIds, bulkTarget.value.value, bulkDate.value).catch(() => {})
  if (!store.error) {
    clearSelection()
    await refetch()
  }
}

onMounted(async () => {
  await store.loadStatuses().catch(() => {})
  await store.fetchSuppliers(props.category).catch(() => {})
  await refetch()
})
</script>

<template>
  <section class="space-y-4">
    <div class="flex items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">
          {{ archived ? `Archived ${isSecondhand ? 'secondhand' : 'dresses'}` : isSecondhand ? 'Secondhand' : 'Dresses' }}
        </h1>
        <p class="text-sm text-stone-500">{{ store.dresses.length }} style(s)</p>
      </div>
      <RouterLink
        v-if="!archived"
        :to="{ name: addRouteName }"
        class="rounded-lg bg-blush-600 px-4 py-2 text-sm text-white hover:bg-blush-700"
      >
        {{ isSecondhand ? 'Upload piece' : 'Add dress' }}
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

    <div class="flex flex-wrap items-center gap-2">
      <select
        :value="supplier"
        class="rounded-lg border border-stone-300 px-3 py-2 text-sm bg-white"
        @change="setSupplier($event.target.value)"
      >
        <option value="">All suppliers</option>
        <option v-for="s in store.suppliers" :key="s" :value="s">{{ s }}</option>
      </select>

      <select
        :value="status"
        class="rounded-lg border border-stone-300 px-3 py-2 text-sm bg-white"
        @change="setStatus($event.target.value)"
      >
        <option value="">All statuses</option>
        <option v-for="s in store.statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>

      <button
        v-if="hasFilters"
        type="button"
        class="text-sm text-stone-500 underline"
        @click="clearFilters"
      >
        Clear filters
      </button>
    </div>

    <p v-if="canBulkSelect && !store.loading && store.dresses.length" class="text-xs text-stone-500">
      Tap the circle on a piece to select it, then mark several as
      "{{ bulkTarget ? bulkTarget.label : '—' }}" together.
    </p>

    <p v-if="store.loading && !store.dresses.length" class="text-sm text-stone-500">Loading…</p>

    <div
      v-else-if="!store.dresses.length"
      class="rounded-xl border border-dashed border-stone-300 p-10 text-center"
    >
      <p class="text-stone-500">
        {{
          query || hasFilters
            ? 'No dresses match these filters.'
            : archived
              ? `No archived ${isSecondhand ? 'pieces' : 'dresses'}.`
              : `No ${isSecondhand ? 'secondhand pieces' : 'dresses'} yet.`
        }}
      </p>
      <RouterLink
        v-if="!query && !archived && !hasFilters"
        :to="{ name: addRouteName }"
        class="mt-3 inline-block text-sm text-blush-700 underline"
      >
        Add your first {{ noun }}
      </RouterLink>
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      <DressCard
        v-for="dress in store.dresses"
        :key="dress.id"
        :dress="dress"
        :selectable="canBulkSelect"
        :selected="selectedIds.has(dress.id)"
        @toggle-select="toggleSelect"
      />
    </div>

    <!-- Sticky bulk-action bar -->
    <div
      v-if="canBulkSelect && selectedCount > 0"
      class="fixed inset-x-0 bottom-16 sm:bottom-4 z-20 mx-auto w-full max-w-md px-4"
    >
      <div class="flex flex-wrap items-center gap-2 rounded-xl border border-stone-200 bg-white p-3 shadow-lg">
        <button type="button" class="text-sm text-stone-500 underline" @click="toggleSelectAll">
          {{ allVisibleSelected ? 'Clear' : 'Select all' }}
        </button>
        <span class="text-sm font-medium">{{ selectedCount }} selected</span>
        <input
          v-model="bulkDate"
          type="date"
          class="rounded-lg border border-stone-300 px-2 py-1 text-sm"
        />
        <button
          type="button"
          :disabled="store.saving || !bulkTarget"
          class="grow rounded-lg bg-blush-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          @click="confirmBulkAdvance"
        >
          {{ store.saving ? 'Saving…' : `Mark as ${bulkTarget ? bulkTarget.label : '—'}` }}
        </button>
      </div>
    </div>
  </section>
</template>
