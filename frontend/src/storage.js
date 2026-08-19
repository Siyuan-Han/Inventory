// Uploads dress photos straight to Supabase Storage from the browser using
// the anon key. This is safe because the anon key is meant to be public and
// the `dress-photos` bucket's RLS policies only permit access to that one
// bucket (see backend/README notes) — it can't touch the database.
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || '').replace(/\/$/, '')
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
const BUCKET = import.meta.env.VITE_SUPABASE_BUCKET || 'dress-photos'

export const photoUploadEnabled = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)

function extensionFor(file) {
  const fromName = file.name?.split('.').pop()
  if (fromName && fromName.length <= 5) return fromName.toLowerCase()
  return (file.type.split('/')[1] || 'jpg').toLowerCase()
}

export async function uploadDressPhoto(file) {
  if (!photoUploadEnabled) {
    throw new Error('Photo upload is not configured (missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY).')
  }
  const path = `dresses/${crypto.randomUUID()}.${extensionFor(file)}`
  const url = `${SUPABASE_URL}/storage/v1/object/${BUCKET}/${path}`

  let response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        apikey: SUPABASE_ANON_KEY,
        'Content-Type': file.type || 'application/octet-stream',
      },
      body: await file.arrayBuffer(),
    })
  } catch {
    throw new Error('Could not reach Supabase Storage to upload the photo.')
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`Photo upload failed (${response.status}): ${text || response.statusText}`)
  }

  return `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/${path}`
}
