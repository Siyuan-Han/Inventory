<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'

const store = useInventoryStore()

const money = (value) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value || 0))

const now = new Date()
const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
const selectedMonth = ref(currentMonth)

// Last two years of months, newest first, for the dropdown.
const monthOptions = Array.from({ length: 24 }, (_, i) => {
  const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
  return {
    value: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`,
    label: d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
  }
})

watch(selectedMonth, (month) => store.fetchMonthlyStats(month).catch(() => {}), { immediate: true })

const cards = computed(() => {
  const s = store.stats
  return [
    { label: 'Dresses', value: s?.total_dresses ?? 0, hint: 'styles tracked' },
    { label: 'Pending orders', value: s?.pending_orders ?? 0, hint: 'not yet received' },
    { label: 'In stock', value: s?.in_stock ?? 0, hint: 'received minus sold' },
    { label: 'Sold', value: s?.total_sold ?? 0, hint: `${s?.cash_sales ?? 0} paid in cash` },
  ]
})

const pipeline = computed(() =>
  store.statuses.map((s) => ({
    ...s,
    count: store.stats?.status_breakdown?.[s.value] ?? 0,
  })),
)

const maxCount = computed(() => Math.max(1, ...pipeline.value.map((s) => s.count)))

onMounted(async () => {
  await store.loadStatuses().catch(() => {})
  await store.fetchStats().catch(() => {})
})
</script>

<template>
  <section class="space-y-6">
    <div class="flex items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p class="text-sm text-stone-500">A snapshot of inventory and orders.</p>
      </div>
      <button
        class="text-sm text-stone-500 hover:text-stone-800 disabled:opacity-50"
        :disabled="store.loading"
        @click="store.fetchStats()"
      >
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div
        v-for="card in cards"
        :key="card.label"
        class="rounded-xl border border-stone-200 bg-white p-4"
      >
        <p class="text-xs uppercase tracking-wide text-stone-500">{{ card.label }}</p>
        <p class="mt-1 text-3xl font-semibold tabular-nums">{{ card.value }}</p>
        <p class="mt-0.5 text-xs text-stone-400">{{ card.hint }}</p>
      </div>
    </div>

    <div class="grid gap-3 sm:grid-cols-3">
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Revenue</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums">
          {{ money(store.stats?.total_revenue) }}
        </p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Cost of orders</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums">
          {{ money(store.stats?.total_cost) }}
        </p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Profit</p>
        <p
          class="mt-1 text-2xl font-semibold tabular-nums"
          :class="Number(store.stats?.profit || 0) < 0 ? 'text-blush-700' : 'text-emerald-700'"
        >
          {{ money(store.stats?.profit) }}
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-stone-200 bg-white p-4">
      <p class="text-xs uppercase tracking-wide text-stone-500 mb-2">Revenue by payment</p>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <p class="text-xs text-stone-500">Cash</p>
          <p class="mt-0.5 text-xl font-semibold tabular-nums text-emerald-700">
            {{ money(store.stats?.cash_revenue) }}
          </p>
        </div>
        <div>
          <p class="text-xs text-stone-500">Card</p>
          <p class="mt-0.5 text-xl font-semibold tabular-nums text-stone-700">
            {{ money(store.stats?.card_revenue) }}
          </p>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-stone-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-medium text-stone-700">Monthly summary</h2>
        <select
          v-model="selectedMonth"
          class="rounded-lg border border-stone-300 px-2 py-1 text-sm bg-white"
        >
          <option v-for="m in monthOptions" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>
      </div>

      <div class="grid grid-cols-3 gap-3">
        <div>
          <p class="text-xs uppercase tracking-wide text-stone-500">Revenue</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">
            {{ money(store.monthlyStats?.revenue) }}
          </p>
        </div>
        <div>
          <p class="text-xs uppercase tracking-wide text-stone-500">Cost</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">
            {{ money(store.monthlyStats?.cost) }}
          </p>
        </div>
        <div>
          <p class="text-xs uppercase tracking-wide text-stone-500">Profit</p>
          <p
            class="mt-1 text-xl font-semibold tabular-nums"
            :class="Number(store.monthlyStats?.profit || 0) < 0 ? 'text-blush-700' : 'text-emerald-700'"
          >
            {{ money(store.monthlyStats?.profit) }}
          </p>
        </div>
      </div>
      <div class="flex items-center justify-between text-xs text-stone-400">
        <span>{{ store.monthlyStats?.sales_count ?? 0 }} sale(s) · {{ store.monthlyStats?.orders_count ?? 0 }} order(s) placed</span>
        <span>{{ money(store.monthlyStats?.cash_revenue) }} cash · {{ money(store.monthlyStats?.card_revenue) }} card</span>
      </div>
    </div>

    <div class="rounded-xl border border-stone-200 bg-white p-4">
      <h2 class="text-sm font-medium text-stone-700">Orders by stage</h2>
      <ul class="mt-3 space-y-2">
        <li v-for="stage in pipeline" :key="stage.value" class="flex items-center gap-3 text-sm">
          <span class="w-40 shrink-0 text-stone-600">{{ stage.label }}</span>
          <span class="grow h-2 rounded-full bg-stone-100 overflow-hidden">
            <span
              class="block h-full rounded-full bg-blush-300"
              :style="{ width: `${(stage.count / maxCount) * 100}%` }"
            />
          </span>
          <span class="w-8 text-right tabular-nums text-stone-700">{{ stage.count }}</span>
        </li>
      </ul>
      <p v-if="!pipeline.length" class="mt-2 text-sm text-stone-400">No orders yet.</p>
    </div>

    <div class="flex gap-2">
      <RouterLink
        :to="{ name: 'dresses' }"
        class="rounded-lg border border-stone-300 px-4 py-2 text-sm hover:bg-stone-100"
      >
        Browse dresses
      </RouterLink>
      <RouterLink
        :to="{ name: 'dress-new' }"
        class="rounded-lg bg-blush-600 px-4 py-2 text-sm text-white hover:bg-blush-700"
      >
        Add a dress
      </RouterLink>
    </div>
  </section>
</template>
