<script setup>
import { reactive, ref } from 'vue'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  dressId: { type: Number, required: true },
  defaultUnitCost: { type: [String, Number], default: null },
})
const emit = defineEmits(['close', 'saved'])

const store = useInventoryStore()
const localError = ref(null)

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  order_date: today,
  quantity: 1,
  unit_cost: props.defaultUnitCost ?? '',
  status: 'ordered',
  notes: '',
})

async function submit() {
  localError.value = null
  if (!form.order_date) {
    localError.value = 'Pick an order date.'
    return
  }
  try {
    await store.createOrder({
      dress_id: props.dressId,
      order_date: form.order_date,
      quantity: Number(form.quantity) || 1,
      unit_cost: form.unit_cost === '' ? null : Number(form.unit_cost),
      status: form.status,
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
      <h2 class="text-lg font-semibold">New order</h2>

      <label class="block">
        <span class="text-sm text-stone-600">Order date</span>
        <input
          v-model="form.order_date"
          type="date"
          required
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
        />
      </label>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-sm text-stone-600">Quantity</span>
          <input
            v-model="form.quantity"
            type="number"
            min="1"
            step="1"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
        <label class="block">
          <span class="text-sm text-stone-600">Unit cost</span>
          <input
            v-model="form.unit_cost"
            type="number"
            min="0"
            step="0.01"
            placeholder="uses base cost"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
      </div>

      <label class="block">
        <span class="text-sm text-stone-600">Status</span>
        <select
          v-model="form.status"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 bg-white"
        >
          <option v-for="s in store.statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
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
          {{ store.saving ? 'Saving…' : 'Add order' }}
        </button>
      </div>
    </form>
  </div>
</template>
