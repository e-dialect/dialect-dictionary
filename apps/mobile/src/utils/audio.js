// All callers of this helper share one preview player.
let active = null;
let generation = 0;

export const audioGeneration = () => generation;

function release(session, status = 'idle') {
  if (active !== session) return;
  active = null;
  session.audio.stop();
  session.audio.destroy();
  session.onState({ status, src: session.src });
}

export function stopAudio(owner) {
  if (owner === undefined) generation += 1;
  if (active && (owner === undefined || active.owner === owner)) release(active);
}

/** Repeating the same preview stops it; a different preview replaces it. */
export function playAudio(src, warn = true, { owner, onState = () => {} } = {}) {
  if (!src || src === 'null') {
    if (warn) uni.showToast({ title: '暂无可播放的录音', icon: 'none' });
    return;
  }
  if (active && active.src === src && active.owner === owner) {
    stopAudio(owner);
    return;
  }
  stopAudio();
  const audio = uni.createInnerAudioContext();
  const session = {
    audio, src, owner, onState,
  };
  active = session;
  const fail = () => {
    if (active !== session) return;
    release(session, 'error');
    uni.showToast({ title: '播放失败，请再点一次重试', icon: 'none' });
  };
  audio.onPlay(() => {
    if (active !== session) return;
    onState({ status: 'playing', src });
    if (owner === undefined) uni.showToast({ title: '正在播放，再点停止', icon: 'none' });
  });
  audio.onEnded(() => release(session));
  audio.onError(fail);
  audio.onStop(() => release(session));
  onState({ status: 'loading', src });
  audio.src = src;
  try {
    audio.play();
  } catch {
    fail();
  }
}
