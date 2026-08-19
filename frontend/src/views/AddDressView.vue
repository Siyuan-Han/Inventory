<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({ id: { type: [String, Number], default: null } })
const route = useRoute()
const router = useRouter()
const store = useInventoryStore()

const dressId = computed(() => (props.id ?? route.params.id) || null)
const isEdit = computed(() => Boolean(dressId.value))
const localError = ref(null)

const form = reactive({
  dress_code: '',
  style_name: '',
  supplier: '',
  base_cost: '',
  photo_url: '',
})

onMounted(async () => {
  if (!isEdit.value) return
  const dress = await store.fetchDress(dressId.value).catch(() => null)
  if (!dress) return
  form.dress_code = dress.dress_code || ''
  form.style_name = dress.style_name || ''
  form.supplier = dress.supplier || ''
  form.base_cost = dress.base_cost ?? ''
  form.photo_url = dress.photo_url || ''
})

async function submit() {
  localError.value = null
  const code = form.dress_code.trim()
  if (!code) {
    localError.value = 'A dress code is required.'
    return
  }

  const payload = {
    dress_code: code,
    style_name: form.style_name.trim() || null,
    supplier: form.supplier.trim() || null,
    base_cost: form.base_cost === '' ? null : Number(form.base_cost),
    photo_url: form.photo_url.trim() || null,
  }

  try {
    const dress = isEdit.value
      ? await store.updateDress(dressId.value, payload)
      : await store.createDress(payload)
    router.push({ name: 'dress-detail', params: { id: dress.id } })
  } catch {
    localError.value = store.error
  }
}
</script>

<template>
  <section class="max-w-lg mx-auto space-y-5">
    <h1 class="text-2xl font-semibold tracking-tight">
      {{ isEdit ? 'Edit dress' : 'Add a dress' }}
    </h1>

    <form class="space-y-4" @submit.prevent="submit">
      <label class="block">
        <span class="text-sm text-stone-600">Dress code <span class="text-blush-600">*</span></span>
        <input
          v-model="form.dress_code"
          required
          maxlength="20"
          placeholder="WD001"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blush-300"
        />
      </label>

      <label class="block">
        <span class="text-sm text-stone-600">Style name</span>
        <input
          v-model="form.style_name"
          maxlength="200"
          placeholder="White Lace"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blush-300"
        />
      </label>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-sm text-stone-600">Supplier</span>
          <input
            v-model="form.supplier"
            maxlength="200"
            placeholder="Shanghai Factory"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
        <label class="block">
          <span class="text-sm text-stone-600">Base cost</span>
          <input
            v-model="form.base_cost"
            type="number"
            min="0"
            step="0.01"
            placeholder="150"
            class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
          />
        </label>
      </div>

      <label class="block">
        <span class="text-sm text-stone-600">Photo URL</span>
        <input
          v-model="form.photo_url"
          type="url"
          placeholder="https://…/dress-photos/wd001.jpg"
          class="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2"
        />
        <span class="mt-1 block text-xs text-stone-400">
          Paste a public link, e.g. from the Supabase <code>dress-photos</code> bucket.
        </span>
      </label>

      <div v-if="form.photo_url" class="rounded-xl overflow-hidden border border-stone-200 w-32">
        <img :src="form.photo_url" alt="Preview" class="w-full aspect-[3/4] object-cover" />
      </div>

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
          {{ store.saving ? 'Saving…' : isEdit ? 'Save changes' : 'Add dress' }}
        </button>
      </div>
    </form>
  </section>
</template>
