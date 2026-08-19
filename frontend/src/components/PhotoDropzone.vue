<script setup>
import { ref } from 'vue'
import { uploadDressPhoto, photoUploadEnabled } from '../storage'

const props = defineProps({
  modelValue: { type: String, default: null },
})
const emit = defineEmits(['update:modelValue'])

const fileInput = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const error = ref(null)

async function handleFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    error.value = 'Please choose an image file.'
    return
  }
  error.value = null
  uploading.value = true
  try {
    const url = await uploadDressPhoto(file)
    emit('update:modelValue', url)
  } catch (err) {
    error.value = err.message
  } finally {
    uploading.value = false
  }
}

function onDrop(event) {
  dragging.value = false
  handleFile(event.dataTransfer.files?.[0])
}

function onPick(event) {
  handleFile(event.target.files?.[0])
  event.target.value = '' // allow re-picking the same file
}

function clear() {
  emit('update:modelValue', null)
  error.value = null
}
</script>

<template>
  <div>
    <div
      v-if="modelValue"
      class="relative rounded-xl overflow-hidden border border-stone-200 w-32"
    >
      <img :src="modelValue" alt="Dress photo" class="w-full aspect-[3/4] object-cover" />
      <button
        type="button"
        class="absolute top-1 right-1 h-6 w-6 rounded-full bg-stone-900/60 text-white text-xs leading-none hover:bg-stone-900/80"
        @click="clear"
      >
        ✕
      </button>
    </div>

    <label
      v-else
      class="flex flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed px-4 py-8 text-center cursor-pointer transition-colors"
      :class="dragging ? 'border-blush-400 bg-blush-50' : 'border-stone-300 hover:border-stone-400'"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onPick" />
      <span v-if="uploading" class="text-sm text-stone-500">Uploading…</span>
      <template v-else>
        <span class="text-2xl text-stone-300">📷</span>
        <span class="text-sm text-stone-600">Drag a photo here, or tap to choose</span>
        <span v-if="!photoUploadEnabled" class="text-xs text-blush-600">
          Photo upload isn't configured yet.
        </span>
      </template>
    </label>

    <p v-if="error" class="mt-1 text-sm text-blush-700">{{ error }}</p>
  </div>
</template>
