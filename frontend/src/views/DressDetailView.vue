<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'
import OrderForm from '../components/OrderForm.vue'
import SaleForm from '../components/SaleForm.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const route = useRoute()
const router = useRouter()
const store = useInventoryStore()

const showOrderForm = ref(false)
const showSaleForm = ref(false)
// Per-order state for the inline "pick a date, then advance" prompt.
const advancing = reactive({})
// Per-order state for the standalone tracking-number edit box.
const trackingEdits = reactive({})

const dress = computed(() => store.dress)
const dressId = computed(() => Number(props.id ?? route.params.id))
const isSecondhand = computed(() => dress.value?.category === 'secondhand')
const listRoute = computed(() => (isSecondhand.value ? 'secondhand' : 'dresses'))
const editRoute = computed(() => (isSecondhand.value ? 'secondhand-edit' : 'dress-edit'))
const today = () => new Date().toISOString().slice(0, 10)

const money = (value) =>
  value === null || value === undefined || value === ''
    ? '—'
    : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value))

const stamp = (value) =>
  value ? new Date(value + (value.endsWith('Z') ? '' : 'Z')).toLocaleDateString() : null

/** The pipeline stages for one order, each with its timestamp. */
function timeline(order) {
  const reachedIndex = store.statusIndex(order.status)
  return store.statuses.map((status, index) => ({
    ...status,
    at: stamp(order[status.field]),
    done: index <= reachedIndex,
  }))
}

function orderLabel(orderId) {
  const order = dress.value?.orders.find((o) => o.id === orderId)
  return order ? `order from ${order.order_date}` : 'a linked order'
}

/** How a sale was paid: fully cash, fully card, or a cash/card split. */
function payment(sale) {
  const price = Number(sale.sale_price) || 0
  if (sale.cash_amount === null || sale.cash_amount === undefined) {
    return sale.is_cash
      ? { label: 'Cash', tone: 'emerald' }
      : { label: 'Card', tone: 'stone' }
  }
  const cash = Number(sale.cash_amount)
  const card = Math.max(0, price - cash)
  if (cash <= 0) return { label: 'Card', tone: 'stone' }
  if (card <= 0) return { label: 'Cash', tone: 'emerald' }
  return { label: `${money(cash)} cash + ${money(card)} card`, tone: 'amber' }
}

function openAdvance(order) {
  advancing[order.id] = { date: today(), trackingNumber: order.tracking_number || '' }
}

function cancelAdvance(order) {
  delete advancing[order.id]
}

async function confirmAdvance(order) {
  const next = store.nextStatus(order.status)
  const { date, trackingNumber } = advancing[order.id] || {}
  if (!next) return
  const includeTracking = next.value === 'shipped_from_factory'
  await store
    .setOrderStatus(order.id, next.value, dressId.value, date, includeTracking ? trackingNumber?.trim() : undefined)
    .catch(() => {})
  delete advancing[order.id]
}

function openTrackingEdit(order) {
  trackingEdits[order.id] = order.tracking_number || ''
}

function cancelTrackingEdit(order) {
  delete trackingEdits[order.id]
}

async function saveTracking(order) {
  const value = trackingEdits[order.id]?.trim() || null
  await store.updateOrder(order.id, dressId.value, { tracking_number: value }).catch(() => {})
  delete trackingEdits[order.id]
}

async function removeOrder(order) {
  if (!confirm(`Delete order from ${order.order_date}?`)) return
  await store.deleteOrder(order.id, dressId.value).catch(() => {})
}

async function removeSale(sale) {
  if (!confirm(`Delete the sale from ${sale.sale_date}?`)) return
  await store.deleteSale(sale.id, dressId.value).catch(() => {})
}

async function removeDress() {
  if (!confirm(`Delete ${dress.value.dress_code} and all its orders and sales?`)) return
  const listRoute = dress.value.category === 'secondhand' ? 'secondhand' : 'dresses'
  await store.deleteDress(dressId.value).catch(() => {})
  if (!store.error) router.push({ name: listRoute })
}

async function archiveDress() {
  if (!confirm(`Archive ${dress.value.dress_code}? It will move out of the active dress list, but nothing is deleted.`)) return
  await store.archiveDress(dressId.value).catch(() => {})
}

async function restoreDress() {
  await store.restoreDress(dressId.value).catch(() => {})
}

async function load() {
  await store.loadStatuses().catch(() => {})
  await store.fetchDress(dressId.value).catch(() => {})
}

onMounted(load)
watch(dressId, load)
</script>

<template>
  <section v-if="dress" class="space-y-6">
    <RouterLink :to="{ name: listRoute }" class="text-sm text-stone-500 hover:text-stone-800">
      ← All {{ isSecondhand ? 'secondhand' : 'dresses' }}
    </RouterLink>

    <p
      v-if="dress.archived_at"
      class="rounded-lg bg-stone-100 border border-stone-200 px-3 py-2 text-sm text-stone-600 flex items-center justify-between gap-2"
    >
      This dress is archived — it's hidden from the active list.
      <button
        class="shrink-0 rounded-lg border border-stone-300 bg-white px-3 py-1 text-sm hover:bg-stone-50"
        :disabled="store.saving"
        @click="restoreDress"
      >
        Restore
      </button>
    </p>

    <div class="grid sm:grid-cols-[200px_1fr] gap-5">
      <div class="aspect-[3/4] sm:aspect-auto sm:h-64 rounded-xl bg-stone-100 overflow-hidden flex items-center justify-center">
        <img
          v-if="dress.photo_url"
          :src="dress.photo_url"
          :alt="dress.style_name || dress.dress_code"
          class="h-full w-full object-cover"
        />
        <span v-else class="text-4xl text-stone-300">❖</span>
      </div>

      <div class="space-y-3">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight">{{ dress.dress_code }}</h1>
          <p class="text-stone-600">{{ dress.style_name || 'Unnamed style' }}</p>
        </div>

        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt class="text-stone-500">{{ isSecondhand ? 'Seller' : 'Supplier' }}</dt>
            <dd>{{ dress.supplier || '—' }}</dd>
          </div>
          <div>
            <dt class="text-stone-500">Base cost</dt>
            <dd class="tabular-nums">{{ money(dress.base_cost) }}</dd>
          </div>
          <div>
            <dt class="text-stone-500">Revenue</dt>
            <dd class="tabular-nums">{{ money(dress.total_revenue) }}</dd>
          </div>
          <div>
            <dt class="text-stone-500">Order cost</dt>
            <dd class="tabular-nums">{{ money(dress.total_cost) }}</dd>
          </div>
        </dl>

        <div class="flex flex-wrap gap-2 pt-1">
          <RouterLink
            :to="{ name: editRoute, params: { id: dress.id } }"
            class="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100"
          >
            Edit
          </RouterLink>
          <button
            v-if="!dress.archived_at"
            class="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100"
            :disabled="store.saving"
            @click="archiveDress"
          >
            Archive
          </button>
          <button
            class="rounded-lg border border-blush-300 text-blush-700 px-3 py-1.5 text-sm hover:bg-blush-50"
            @click="removeDress"
          >
            Delete
          </button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <div class="rounded-xl border border-stone-200 bg-white p-3 text-center">
        <p class="text-2xl font-semibold tabular-nums">{{ dress.total_ordered }}</p>
        <p class="text-xs text-stone-500">ordered</p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-3 text-center">
        <p class="text-2xl font-semibold tabular-nums">{{ dress.in_stock }}</p>
        <p class="text-xs text-stone-500">in stock</p>
      </div>
      <div class="rounded-xl border border-stone-200 bg-white p-3 text-center">
        <p class="text-2xl font-semibold tabular-nums">{{ dress.total_sold }}</p>
        <p class="text-xs text-stone-500">sold</p>
      </div>
    </div>

    <!-- Orders -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Orders</h2>
        <button
          v-if="!isSecondhand"
          class="rounded-lg bg-blush-600 px-3 py-1.5 text-sm text-white hover:bg-blush-700"
          @click="showOrderForm = true"
        >
          Add order
        </button>
      </div>

      <p v-if="!dress.orders.length" class="text-sm text-stone-500">No orders yet.</p>

      <article
        v-for="order in dress.orders"
        :key="order.id"
        class="rounded-xl border border-stone-200 bg-white p-4 space-y-3"
      >
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <p class="font-medium">
            {{ order.order_date }}
            <span class="text-stone-500 font-normal">
              · qty {{ order.quantity }} · {{ money(order.unit_cost) }} each
            </span>
          </p>
          <span class="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
            {{ store.statusLabel(order.status) }}
          </span>
        </div>

        <ol class="flex gap-1">
          <li v-for="step in timeline(order)" :key="step.value" class="grow min-w-0">
            <span
              class="block h-1.5 rounded-full"
              :class="step.done ? 'bg-blush-400' : 'bg-stone-200'"
            />
            <p class="mt-1 text-[10px] leading-tight text-stone-500 truncate" :title="step.label">
              {{ step.label }}
            </p>
            <p class="text-[10px] text-stone-400 tabular-nums">{{ step.at || '—' }}</p>
          </li>
        </ol>

        <p v-if="order.notes" class="text-sm text-stone-600">{{ order.notes }}</p>

        <!-- Tracking number: editable any time once there's a factory shipment to track. -->
        <div v-if="trackingEdits[order.id] !== undefined" class="flex flex-wrap items-center gap-2">
          <input
            v-model="trackingEdits[order.id]"
            type="text"
            placeholder="Tracking number"
            class="rounded-lg border border-stone-300 px-2 py-1 text-sm"
          />
          <button
            :disabled="store.saving"
            class="rounded-lg bg-blush-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            @click="saveTracking(order)"
          >
            Save
          </button>
          <button class="rounded-lg px-3 py-1 text-sm text-stone-500" @click="cancelTrackingEdit(order)">
            Cancel
          </button>
        </div>
        <p v-else-if="order.tracking_number" class="text-sm text-stone-600">
          Tracking: <span class="font-medium">{{ order.tracking_number }}</span>
          <button class="ml-2 text-xs text-stone-400 underline" @click="openTrackingEdit(order)">
            Edit
          </button>
        </p>
        <button
          v-else-if="store.statusIndex(order.status) >= store.statusIndex('shipped_from_factory')"
          type="button"
          class="text-sm text-stone-400 underline"
          @click="openTrackingEdit(order)"
        >
          + Add tracking number
        </button>

        <div
          v-if="advancing[order.id]"
          class="flex flex-wrap items-center gap-2 rounded-lg bg-stone-50 border border-stone-200 p-2"
        >
          <label class="text-sm text-stone-600">
            {{ store.nextStatus(order.status).label }} on
          </label>
          <input
            v-model="advancing[order.id].date"
            type="date"
            class="rounded-lg border border-stone-300 px-2 py-1 text-sm"
          />
          <input
            v-if="store.nextStatus(order.status).value === 'shipped_from_factory'"
            v-model="advancing[order.id].trackingNumber"
            type="text"
            placeholder="Tracking number (optional)"
            class="rounded-lg border border-stone-300 px-2 py-1 text-sm grow min-w-[10rem]"
          />
          <button
            :disabled="store.saving"
            class="rounded-lg bg-blush-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            @click="confirmAdvance(order)"
          >
            Confirm
          </button>
          <button class="rounded-lg px-3 py-1 text-sm text-stone-500" @click="cancelAdvance(order)">
            Cancel
          </button>
        </div>
        <div v-else class="flex gap-2">
          <button
            v-if="store.nextStatus(order.status)"
            :disabled="store.saving"
            class="rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100 disabled:opacity-50"
            @click="openAdvance(order)"
          >
            Mark {{ store.nextStatus(order.status).label.toLowerCase() }}
          </button>
          <button
            :disabled="store.saving"
            class="rounded-lg px-3 py-1.5 text-sm text-stone-500 hover:text-blush-700 disabled:opacity-50"
            @click="removeOrder(order)"
          >
            Delete
          </button>
        </div>
      </article>
    </div>

    <!-- Sales -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">Sales</h2>
        <button
          class="rounded-lg bg-blush-600 px-3 py-1.5 text-sm text-white hover:bg-blush-700"
          @click="showSaleForm = true"
        >
          Record sale
        </button>
      </div>

      <p v-if="!dress.sales.length" class="text-sm text-stone-500">No sales yet.</p>

      <ul v-else class="divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
        <li v-for="sale in dress.sales" :key="sale.id" class="p-3 flex items-center gap-3">
          <div class="grow min-w-0">
            <p class="text-sm">
              <span class="font-medium tabular-nums">{{ money(sale.sale_price) }}</span>
              <span class="text-stone-500"> · {{ sale.sale_date }}</span>
              <span v-if="sale.order_id" class="text-stone-400"> · {{ orderLabel(sale.order_id) }}</span>
            </p>
            <p v-if="sale.notes" class="text-xs text-stone-500 truncate">{{ sale.notes }}</p>
          </div>
          <span
            class="shrink-0 rounded-full px-2 py-0.5 text-[11px]"
            :class="{
              emerald: 'bg-emerald-50 text-emerald-700',
              stone: 'bg-stone-100 text-stone-600',
              amber: 'bg-amber-50 text-amber-700',
            }[payment(sale).tone]"
          >
            {{ payment(sale).label }}
          </span>
          <button
            :disabled="store.saving"
            class="shrink-0 text-sm text-stone-400 hover:text-blush-700 disabled:opacity-50"
            @click="removeSale(sale)"
          >
            ✕
          </button>
        </li>
      </ul>
    </div>

    <OrderForm
      v-if="showOrderForm"
      :dress-id="dress.id"
      :default-unit-cost="dress.base_cost"
      @close="showOrderForm = false"
      @saved="showOrderForm = false"
    />
    <SaleForm
      v-if="showSaleForm"
      :dress-id="dress.id"
      :orders="dress.orders"
      @close="showSaleForm = false"
      @saved="showSaleForm = false"
    />
  </section>

  <p v-else-if="store.loading" class="text-sm text-stone-500">Loading…</p>
  <p v-else class="text-sm text-stone-500">Dress not found.</p>
</template>
