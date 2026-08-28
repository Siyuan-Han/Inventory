<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  dress: { type: Object, required: true },
  selectable: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle-select'])

const store = useInventoryStore()

const detailRoute = computed(() =>
  props.dress.category === 'secondhand' ? 'secondhand-detail' : 'dress-detail',
)

const badge = computed(() => {
  const d = props.dress
  if (d.archived_at) return { text: 'Archived', tone: 'stone' }
  if (d.in_stock > 0) return { text: `${d.in_stock} in stock`, tone: 'emerald' }
  if (d.pending_orders > 0) return { text: store.statusLabel(d.latest_status), tone: 'amber' }
  if (d.total_sold > 0) return { text: 'Sold out', tone: 'stone' }
  return { text: 'No orders', tone: 'stone' }
})

const toneClass = {
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  amber: 'bg-amber-50 text-amber-700 border-amber-200',
  stone: 'bg-stone-100 text-stone-600 border-stone-200',
}
</script>

<template>
  <RouterLink
    :to="{ name: detailRoute, params: { id: dress.id } }"
    class="group relative rounded-xl border border-stone-200 bg-white overflow-hidden hover:border-blush-300 hover:shadow-sm transition"
    :class="{ 'opacity-60': dress.archived_at }"
  >
    <button
      v-if="selectable"
      type="button"
      :aria-pressed="selected"
      :aria-label="selected ? 'Deselect' : 'Select'"
      class="absolute top-2 left-2 z-10 flex h-7 w-7 items-center justify-center rounded-full border-2 shadow transition-colors"
      :class="selected ? 'border-blush-600 bg-blush-600' : 'border-stone-300 bg-white/90'"
      @click.prevent.stop="emit('toggle-select', dress.id)"
    >
      <svg v-if="selected" viewBox="0 0 20 20" fill="none" class="h-4 w-4">
        <path
          d="M4.5 10.5l3.5 3.5 7.5-8.5"
          stroke="white"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    <div class="aspect-[3/4] bg-stone-100 flex items-center justify-center overflow-hidden">
      <img
        v-if="dress.photo_url"
        :src="dress.photo_url"
        :alt="dress.style_name || dress.dress_code"
        class="h-full w-full object-cover group-hover:scale-[1.02] transition-transform"
        loading="lazy"
      />
      <span v-else class="text-3xl text-stone-300">❖</span>
    </div>

    <div class="p-3 space-y-1.5">
      <div class="flex items-baseline justify-between gap-2">
        <p class="font-medium text-sm">{{ dress.dress_code }}</p>
        <p class="text-xs text-stone-400 tabular-nums">{{ dress.total_ordered }} ordered</p>
      </div>
      <p class="text-sm text-stone-600 truncate">{{ dress.style_name || '—' }}</p>
      <span
        class="inline-block rounded-full border px-2 py-0.5 text-[11px]"
        :class="toneClass[badge.tone]"
      >
        {{ badge.text }}
      </span>
    </div>
  </RouterLink>
</template>
