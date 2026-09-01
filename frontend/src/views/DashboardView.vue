<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
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

const settlementForm = reactive({
  settlement_date: now.toISOString().slice(0, 10),
  amount: '',
  paid_by: '',
  paid_to: '',
  notes: '',
})
const settlementError = ref(null)
const showSettlementForm = ref(false)

function otherPartner(value) {
  return store.partners.find((p) => p.value !== value)?.value || ''
}

watch(
  () => settlementForm.paid_by,
  (value) => {
    if (value && settlementForm.paid_to === value) settlementForm.paid_to = otherPartner(value)
  },
)

async function submitSettlement() {
  settlementError.value = null
  if (!settlementForm.paid_by || !settlementForm.paid_to) {
    settlementError.value = 'Choose who paid and who received it.'
    return
  }
  if (settlementForm.amount === '' || Number(settlementForm.amount) <= 0) {
    settlementError.value = 'Enter an amount.'
    return
  }
  try {
    await store.createSettlement({
      settlement_date: settlementForm.settlement_date,
      amount: Number(settlementForm.amount),
      paid_by: settlementForm.paid_by,
      paid_to: settlementForm.paid_to,
      notes: settlementForm.notes || null,
    })
    settlementForm.amount = ''
    settlementForm.notes = ''
    showSettlementForm.value = false
  } catch {
    settlementError.value = store.error
  }
}

async function removeSettlement(settlement) {
  if (!confirm(`Delete the ${money(settlement.amount)} settlement from ${settlement.settlement_date}?`)) return
  await store.deleteSettlement(settlement.id).catch(() => {})
}

/** Prefill the equalizing settlement from the summary's suggested direction. */
function openSettlementForm() {
  const summary = store.settlementSummary
  if (summary?.equalize_direction === 'camille_to_zoe') {
    settlementForm.paid_by = 'camille'
    settlementForm.paid_to = 'zoe'
    settlementForm.amount = summary.to_equalize
  } else if (summary?.equalize_direction === 'zoe_to_camille') {
    settlementForm.paid_by = 'zoe'
    settlementForm.paid_to = 'camille'
    settlementForm.amount = summary.to_equalize
  }
  showSettlementForm.value = true
}

onMounted(async () => {
  await store.loadStatuses().catch(() => {})
  await store.loadPartners().catch(() => {})
  await store.fetchStats().catch(() => {})
  await store.fetchSettlementSummary().catch(() => {})
  await store.fetchSettlements().catch(() => {})
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

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Revenue</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums">
          {{ money(store.stats?.total_revenue) }}
        </p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Cost</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums">
          {{ money(store.stats?.cost_of_goods_sold) }}
        </p>
        <p class="mt-0.5 text-xs text-stone-400">sold dresses only</p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Inventory</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums">
          {{ money(store.stats?.inventory_value) }}
        </p>
        <p class="mt-0.5 text-xs text-stone-400">unsold stock, at cost</p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-4">
        <p class="text-xs uppercase tracking-wide text-stone-500">Profit</p>
        <p
          class="mt-1 text-2xl font-semibold tabular-nums"
          :class="Number(store.stats?.profit || 0) < 0 ? 'text-blush-700' : 'text-emerald-700'"
        >
          {{ money(store.stats?.profit) }}
        </p>
        <p class="mt-0.5 text-xs text-stone-400">revenue − cost + try-on fees</p>
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
      <p class="mt-3 pt-3 border-t border-stone-100 text-xs text-stone-500">
        Includes {{ money(store.stats?.tryon_revenue) }} in try-on fees ({{ store.stats?.tryon_count ?? 0 }})
      </p>
    </div>

    <div class="rounded-xl border border-stone-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-medium text-stone-700">Cash settlement</h2>
        <button
          class="text-sm text-blush-700 hover:text-blush-800"
          @click="openSettlementForm"
        >
          Record settlement
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div
          v-for="pos in store.settlementSummary?.positions || []"
          :key="pos.partner"
          class="rounded-lg bg-stone-50 border border-stone-200 p-3"
        >
          <p class="text-xs text-stone-500">{{ pos.label }}</p>
          <p class="mt-0.5 text-xl font-semibold tabular-nums">{{ money(pos.net_position) }}</p>
          <p class="mt-0.5 text-[11px] text-stone-400">
            {{ money(pos.cash_collected) }} collected
          </p>
        </div>
      </div>

      <p class="rounded-lg bg-blush-50 border border-blush-200 px-3 py-2 text-sm text-blush-800">
        <template v-if="store.settlementSummary?.equalize_direction === 'camille_to_zoe'">
          Camille owes Zoe {{ money(store.settlementSummary.to_equalize) }} to equalize.
        </template>
        <template v-else-if="store.settlementSummary?.equalize_direction === 'zoe_to_camille'">
          Zoe owes Camille {{ money(store.settlementSummary.to_equalize) }} to equalize.
        </template>
        <template v-else>All settled up.</template>
      </p>

      <p
        v-if="Number(store.settlementSummary?.unattributed_cash || 0) > 0"
        class="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800"
      >
        {{ money(store.settlementSummary.unattributed_cash) }} in cash sales/try-ons predate
        partner tracking and aren't included above.
      </p>

      <form
        v-if="showSettlementForm"
        class="space-y-2 rounded-lg border border-stone-200 p-3"
        @submit.prevent="submitSettlement"
      >
        <div class="grid grid-cols-2 gap-2">
          <label class="block">
            <span class="text-xs text-stone-500">Date</span>
            <input
              v-model="settlementForm.settlement_date"
              type="date"
              class="mt-0.5 w-full rounded-lg border border-stone-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label class="block">
            <span class="text-xs text-stone-500">Amount</span>
            <input
              v-model="settlementForm.amount"
              type="number"
              min="0"
              step="0.01"
              class="mt-0.5 w-full rounded-lg border border-stone-300 px-2 py-1.5 text-sm"
            />
          </label>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <label class="block">
            <span class="text-xs text-stone-500">Paid by</span>
            <select
              v-model="settlementForm.paid_by"
              class="mt-0.5 w-full rounded-lg border border-stone-300 px-2 py-1.5 text-sm bg-white"
            >
              <option value="">Choose</option>
              <option v-for="p in store.partners" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </label>
          <label class="block">
            <span class="text-xs text-stone-500">Paid to</span>
            <select
              v-model="settlementForm.paid_to"
              class="mt-0.5 w-full rounded-lg border border-stone-300 px-2 py-1.5 text-sm bg-white"
            >
              <option value="">Choose</option>
              <option v-for="p in store.partners" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </label>
        </div>
        <label class="block">
          <span class="text-xs text-stone-500">Notes</span>
          <input
            v-model="settlementForm.notes"
            type="text"
            class="mt-0.5 w-full rounded-lg border border-stone-300 px-2 py-1.5 text-sm"
          />
        </label>
        <p v-if="settlementError" class="text-sm text-blush-700">{{ settlementError }}</p>
        <div class="flex gap-2 pt-1">
          <button
            type="button"
            class="grow rounded-lg border border-stone-300 py-1.5 text-sm"
            @click="showSettlementForm = false"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="store.saving"
            class="grow rounded-lg bg-blush-600 py-1.5 text-sm text-white disabled:opacity-60"
          >
            {{ store.saving ? 'Saving…' : 'Save settlement' }}
          </button>
        </div>
      </form>

      <ul v-if="store.settlements.length" class="divide-y divide-stone-100 text-sm">
        <li
          v-for="s in store.settlements.slice(0, 8)"
          :key="s.id"
          class="flex items-center justify-between gap-2 py-1.5"
        >
          <span class="text-stone-600">
            {{ s.settlement_date }} · {{ store.partnerLabel(s.paid_by) }} → {{ store.partnerLabel(s.paid_to) }}
            · <span class="tabular-nums">{{ money(s.amount) }}</span>
          </span>
          <button
            :disabled="store.saving"
            class="shrink-0 text-stone-400 hover:text-blush-700 disabled:opacity-50"
            @click="removeSettlement(s)"
          >
            ✕
          </button>
        </li>
      </ul>
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

      <div class="grid grid-cols-2 gap-3">
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
          <p class="mt-0.5 text-xs text-stone-400">sold this month</p>
        </div>
        <div>
          <p class="text-xs uppercase tracking-wide text-stone-500">Inventory</p>
          <p class="mt-1 text-xl font-semibold tabular-nums">
            {{ money(store.monthlyStats?.inventory_spend) }}
          </p>
          <p class="mt-0.5 text-xs text-stone-400">spent on new stock</p>
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
        <span>
          {{ store.monthlyStats?.sales_count ?? 0 }} sale(s) ·
          {{ store.monthlyStats?.tryon_count ?? 0 }} try-on(s) ·
          {{ store.monthlyStats?.orders_count ?? 0 }} order(s) placed
        </span>
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
