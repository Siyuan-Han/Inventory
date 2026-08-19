<script setup>
import { reactive, ref } from 'vue'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  dressId: { type: Number, required: true },
  orders: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const store = useInventoryStore()
const localError = ref(null)

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  sale_date: today,
  sale_price: '',
  is_cash: false,
  order_id: '',
  notes: '',
})

async function submit() {
  localError.value = null
  if (!form.sale_date) {
    localError.value = 'Pick a sale date.'
    return
  }
  try {
    await store.createSale({
      dress_id: props.dressId,
      order_id: form.order_id === '' ? null : Number(form.order_id),
      sale_date: form.sale_date,
      sale_price: form.sale_price === '' ? null : Number(form.sale_price),
      is_cash: form.is_cash,
      notes: form.notes || null,
    })
    emit('saved')
  } catch {
    localError.value = store.error
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-30 bg-stone-900/40 flex items-end sm:items-center justify-center p-0 sm:p-4"
    @click.self="emit('close')"
  >
    <form
      class="w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl p-5 space-y-4 max-h-[90dvh] overflow-y-auto"
      @submit.prevent="submit"
    >
      <h2 class="text-lg font-semibold">Record a sale</h2>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-sm text-stone-600">Sale date</span>
          <input
            v-model="form.sale_date"
            type="date"
            required
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
        <label class="block">
          <span class="text-sm text-stone-600">Sale price</span>
          <input
            v-model="form.sale_price"
            type="number"
            min="0"
            step="0.01"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
      </div>

      <label class="block">
        <span class="text-sm text-stone-600">From order (optional)</span>
        <select
          v-model="form.order_id"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 bg-white"
        >
          <option value="">Not linked to an order</option>
          <option v-for="order in orders" :key="order.id" :value="order.id">
            {{ order.order_date }} · qty {{ order.quantity }}<template v-if="order.unit_cost"> · ${{ order.unit_cost }} each</template>
          </option>
        </select>
      </label>

      <label class="flex items-center gap-2">
        <input
          v-model="form.is_cash"
          type="checkbox"
          class="h-4 w-4 rounded border-stone-300 accent-blush-600"
        />
        <span class="text-sm text-stone-700">Paid in cash</span>
      </label>

      <label class="block">
        <span class="text-sm text-stone-600">Notes</span>
        <textarea
          v-model="form.notes"
          rows="2"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
        />
      </label>

      <p v-if="localError" class="text-sm text-blush-700">{{ localError }}</p>

      <div class="flex gap-2 pt-1">
        <button
          type="button"
          class="grow rounded-lg border border-stone-300 py-2.5 text-sm"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button
          type="submit"
          :disabled="store.saving"
          class="grow rounded-lg bg-blush-600 py-2.5 text-sm text-white disabled:opacity-60"
        >
          {{ store.saving ? 'Saving…' : 'Record sale' }}
        </button>
      </div>
    </form>
  </div>
</template>
