<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' },
  maxlength: { type: Number, default: undefined },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)

const filtered = computed(() => {
  const query = props.modelValue.trim().toLowerCase()
  const list = query
    ? props.options.filter((o) => o.toLowerCase().includes(query))
    : props.options
  // Don't show the option that exactly matches what's already typed.
  return list.filter((o) => o.toLowerCase() !== query)
})

function select(value) {
  emit('update:modelValue', value)
  open.value = false
}
</script>

<template>
  <div class="relative">
    <input
      :value="modelValue"
      :maxlength="maxlength"
      :placeholder="placeholder"
      autocomplete="off"
      class="w-full rounded-lg border border-stone-300 px-3 py-2"
      @input="emit('update:modelValue', $event.target.value)"
      @focus="open = true"
      @blur="open = false"
    />
    <ul
      v-if="open && filtered.length"
      class="absolute z-10 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-stone-200 bg-white shadow-lg py-1"
    >
      <li v-for="option in filtered" :key="option">
        <button
          type="button"
          class="block w-full text-left px-3 py-1.5 text-sm hover:bg-blush-50"
          @mousedown.prevent="select(option)"
        >
          {{ option }}
        </button>
      </li>
    </ul>
  </div>
</template>
