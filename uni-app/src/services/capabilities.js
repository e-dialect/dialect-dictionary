import { BASE_URL } from '@/const/urls';

/** A fresh public capability is a UI hint, never an authorization grant. */
export function wordApplicationsEnabled(payload, receivedAt = Date.now()) {
  if (!payload || payload.version !== 1 || payload.features?.wordApplications?.enabled !== true) {
    return false;
  }
  if (!Number.isFinite(payload.ttlSeconds) || payload.ttlSeconds <= 0 || payload.ttlSeconds > 15) {
    return false;
  }
  const generated = Date.parse(payload.generatedAt);
  const expires = Date.parse(payload.expiresAt);
  return Number.isFinite(generated) && Number.isFinite(expires)
    && generated <= receivedAt && expires > receivedAt
    && expires > generated && expires - generated <= payload.ttlSeconds * 1000
    && expires <= receivedAt + 15000;
}

/** Do not cache or persist enabled state; every entry and submission fetches anew. */
export async function checkWordApplications() {
  try {
    const response = await uni.request({
      url: `${BASE_URL}/capabilities?_=${Date.now()}`,
      method: 'GET',
      header: { 'Cache-Control': 'no-cache' },
      dataType: 'json',
      timeout: 10000,
    });
    return response.statusCode === 200 && wordApplicationsEnabled(response.data);
  } catch (error) {
    return false;
  }
}
