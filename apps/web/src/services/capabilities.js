import axios from 'axios'

// Match the mobile client's short-lived capability contract on every form entry and submit.
export async function checkWordApplications () {
  const { data } = await axios.get('/capabilities', {
    params: { _: Date.now() }, headers: { 'Cache-Control': 'no-cache' }, timeout: 10000
  })
  const now = Date.now()
  const generated = Date.parse(data?.generatedAt)
  const expires = Date.parse(data?.expiresAt)
  if (data?.version !== 1 || !Number.isFinite(data.ttlSeconds) ||
      data.ttlSeconds <= 0 || data.ttlSeconds > 15 || !(generated <= now && now < expires) ||
      expires - generated > data.ttlSeconds * 1000 || typeof data.features?.wordApplications?.enabled !== 'boolean') {
    throw new Error('无有效的词条申请状态')
  }
  return data.features.wordApplications.enabled
}
