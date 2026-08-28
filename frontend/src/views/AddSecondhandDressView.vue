<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'
import PhotoDropzone from '../components/PhotoDropzone.vue'
import ComboBox from '../components/ComboBox.vue'

const router = useRouter()
const store = useInventoryStore()

const localError = ref(null)
const previewCode = ref('')
const today = new Date().toISOString().slice(0, 10)

const form = reactive({
  style_name: '',
  supplier: '', // the individual seller, shown as "Seller"
  cost: '', // one cost field — used as both the dress's base_cost and the order's unit_cost
  photo_url: '',
  order_date: today,
  status: 'ordered',
  tracking_number: '',
  order_notes: '',
})

onMounted(async () => {
  await store.loadStatuses().catch(() => {})
  store.fetchSuppliers('secondhand').catch(() => {})
  previewCode.value = await store.nextDressCode('secondhand').catch(() => '')
})

async function submit() {
  localError.value = null
  if (!form.order_date) {
    localError.value = 'Pick the date you acquired this piece.'
    return
  }

  const cost = form.cost === '' ? null : Number(form.cost)
  const payload = {
    style_name: form.style_name.trim() || null,
    supplier: form.supplier.trim() || null,
    base_cost: cost,
    photo_url: form.photo_url || null,
    order_date: form.order_date,
    unit_cost: cost,
    status: form.status,
    tracking_number: form.tracking_number.trim() || null,
    order_notes: form.order_notes.trim() || null,
  }

  try {
    const dress = await store.createSecondhandDress(payload)
    router.push({ name: 'secondhand-detail', params: { id: dress.id } })
  } catch {
    localError.value = store.error
  }
}
</script>

<template>
  <section class="max-w-lg mx-auto space-y-5">
    <h1 class="text-2xl font-semibold tracking-tight">Upload a secondhand piece</h1>
    <p class="text-sm text-stone-500 -mt-3">
      One piece, one order — this creates both at once, since a secondhand
      dress is never reordered.
    </p>

    <form class="space-y-4" @submit.prevent="submit">
      <div class="block">
        <span class="text-sm text-stone-600">Dress code</span>
        <p class="mt-1 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-stone-600">
          {{ previewCode || '…' }}
          <span class="text-xs text-stone-400">(assigned automatically)</span>
        </p>
      </div>

      <label class="block">
        <span class="text-sm text-stone-600">Style / description</span>
        <input
          v-model="form.style_name"
          maxlength="200"
          placeholder="Ivory mermaid, size 6"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blush-300"
        />
      </label>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-sm text-stone-600">Seller</span>
          <div class="mt-1">
            <ComboBox
              v-model="form.supplier"
              :options="store.suppliers"
              :maxlength="200"
              placeholder="Individual seller"
            />
          </div>
        </label>
        <label class="block">
          <span class="text-sm text-stone-600">Cost</span>
          <input
            v-model="form.cost"
            type="number"
            min="0"
            step="0.01"
            placeholder="150"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-sm text-stone-600">Acquired on</span>
          <input
            v-model="form.order_date"
            type="date"
            required
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
        <label class="block">
          <span class="text-sm text-stone-600">Status</span>
          <select
            v-model="form.status"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 bg-white"
          >
            <option v-for="s in store.statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </label>
      </div>

      <label class="block">
        <span class="text-sm text-stone-600">Tracking number</span>
        <input
          v-model="form.tracking_number"
          maxlength="100"
          placeholder="Optional"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
        />
      </label>

      <label class="block">
        <span class="text-sm text-stone-600">Photo</span>
        <div class="mt-1">
          <PhotoDropzone v-model="form.photo_url" />
        </div>
      </label>

      <label class="block">
        <span class="text-sm text-stone-600">Notes</span>
        <textarea
          v-model="form.order_notes"
          rows="2"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
        />
      </label>

      <p v-if="localError" class="text-sm text-blush-700">{{ localError }}</p>

      <div class="flex gap-2 pt-1">
        <button
          type="button"
          class="grow rounded-lg border border-stone-300 py-2.5 text-sm"
          @click="router.back()"
        >
          Cancel
        </button>
        <button
          type="submit"
          :disabled="store.saving"
          class="grow rounded-lg bg-blush-600 py-2.5 text-sm text-white disabled:opacity-60"
        >
          {{ store.saving ? 'Saving…' : 'Upload piece' }}
        </button>
      </div>
    </form>
  </section>
</template>
