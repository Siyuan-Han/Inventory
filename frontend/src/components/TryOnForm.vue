<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  dressId: { type: Number, required: true },
})
const emit = defineEmits(['close', 'saved'])

const store = useInventoryStore()
const localError = ref(null)

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  tryon_date: today,
  fee: '',
  payment: 'cash', // 'cash' | 'card' | 'split'
  cash_amount: '', // only used when payment === 'split'
  received_by: '', // who holds the cash — required whenever cash is involved
  notes: '',
})

const fee = computed(() => Number(form.fee) || 0)
const cardPortion = computed(() => Math.max(0, fee.value - (Number(form.cash_amount) || 0)))
const cashInvolved = computed(() => form.payment === 'cash' || form.payment === 'split')

onMounted(() => store.loadPartners().catch(() => {}))

// Keep the split amount sane if the fee changes after it was set.
watch(fee, (value) => {
  if (form.payment === 'split' && Number(form.cash_amount) > value) form.cash_amount = value
})

function setPayment(mode) {
  form.payment = mode
  if (mode === 'split' && form.cash_amount === '') {
    form.cash_amount = fee.value ? (fee.value / 2).toFixed(2) : ''
  }
}

async function submit() {
  localError.value = null
  if (!form.tryon_date) {
    localError.value = 'Pick a try-on date.'
    return
  }
  if (form.payment === 'split' && form.cash_amount === '') {
    localError.value = 'Enter how much was paid in cash.'
    return
  }
  if (cashInvolved.value && !form.received_by) {
    localError.value = 'Choose who received the cash.'
    return
  }

  const payload = {
    dress_id: props.dressId,
    tryon_date: form.tryon_date,
    fee: form.fee === '' ? null : Number(form.fee),
    received_by: cashInvolved.value ? form.received_by : null,
    notes: form.notes || null,
  }
  if (form.payment === 'cash') {
    payload.is_cash = true
    payload.cash_amount = null
  } else if (form.payment === 'card') {
    payload.is_cash = false
    payload.cash_amount = null
  } else {
    payload.cash_amount = Number(form.cash_amount)
  }

  try {
    await store.createTryOn(payload)
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
      <h2 class="text-lg font-semibold">Record a try-on</h2>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-sm text-stone-600">Try-on date</span>
          <input
            v-model="form.tryon_date"
            type="date"
            required
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
        <label class="block">
          <span class="text-sm text-stone-600">Fee</span>
          <input
            v-model="form.fee"
            type="number"
            min="0"
            step="0.01"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
      </div>

      <div class="block">
        <span class="text-sm text-stone-600">Payment</span>
        <div class="mt-1 flex gap-1 rounded-lg bg-stone-100 p-1 text-sm">
          <button
            type="button"
            class="grow rounded-md py-1.5 transition-colors"
            :class="form.payment === 'cash' ? 'bg-white shadow-sm font-medium' : 'text-stone-500'"
            @click="setPayment('cash')"
          >
            Cash
          </button>
          <button
            type="button"
            class="grow rounded-md py-1.5 transition-colors"
            :class="form.payment === 'card' ? 'bg-white shadow-sm font-medium' : 'text-stone-500'"
            @click="setPayment('card')"
          >
            Card
          </button>
          <button
            type="button"
            class="grow rounded-md py-1.5 transition-colors"
            :class="form.payment === 'split' ? 'bg-white shadow-sm font-medium' : 'text-stone-500'"
            @click="setPayment('split')"
          >
            Split
          </button>
        </div>

        <div v-if="form.payment === 'split'" class="mt-2 flex items-center gap-2">
          <label class="grow">
            <span class="text-xs text-stone-500">Cash amount</span>
            <input
              v-model="form.cash_amount"
              type="number"
              min="0"
              :max="fee || undefined"
              step="0.01"
              class="mt-0.5 w-full rounded-lg border border-stone-300 px-3 py-2"
            />
          </label>
          <p class="text-sm text-stone-500 pt-4">
            + ${{ cardPortion.toFixed(2) }} card
          </p>
        </div>
      </div>

      <div v-if="cashInvolved" class="block">
        <span class="text-sm text-stone-600">Cash received by</span>
        <div class="mt-1 flex gap-1 rounded-lg bg-stone-100 p-1 text-sm">
          <button
            v-for="partner in store.partners"
            :key="partner.value"
            type="button"
            class="grow rounded-md py-1.5 transition-colors"
            :class="form.received_by === partner.value ? 'bg-white shadow-sm font-medium' : 'text-stone-500'"
            @click="form.received_by = partner.value"
          >
            {{ partner.label }}
          </button>
        </div>
      </div>

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
          {{ store.saving ? 'Saving…' : 'Record try-on' }}
        </button>
      </div>
    </form>
  </div>
</template>
