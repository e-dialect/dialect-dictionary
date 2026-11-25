// Word preview buttons share one player. Native audio controls remain independent.
let active = null

function release (session, status = 'idle') {
  if (active !== session) return
  active = null
  session.audio.pause()
  session.audio.removeAttribute('src')
  session.audio.load()
  session.onState({ status, src: session.src })
}

export function stopAudio (owner) {
  if (active && (owner === undefined || active.owner === owner)) release(active)
}

export function playAudio (src, { owner, onState = () => {}, onError = () => {} } = {}) {
  if (!src || src === 'null') return
  if (active && active.src === src && active.owner === owner) {
    stopAudio(owner)
    return
  }
  stopAudio()
  const audio = new Audio(src)
  const session = { audio, src, owner, onState }
  active = session
  const fail = () => {
    if (active !== session) return
    release(session, 'error')
    onError()
  }
  audio.addEventListener('playing', () => {
    if (active === session) onState({ status: 'playing', src })
  })
  audio.addEventListener('ended', () => release(session))
  audio.addEventListener('error', fail)
  onState({ status: 'loading', src })
  try {
    Promise.resolve(audio.play()).catch(fail)
  } catch {
    fail()
  }
}
