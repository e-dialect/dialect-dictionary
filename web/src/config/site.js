// Public deployment settings only. Never put secrets in this file.
import defaults from './defaults.json'
import generated from './generated.json'

const supplied = typeof window !== 'undefined' && window.__DICTIONARY_CONFIG__
const selected = supplied || generated
const siteConfig = {
  ...defaults,
  ...selected,
  dialect: { ...defaults.dialect, ...((selected.dialect) || {}) },
  contentSource: { ...defaults.contentSource, ...((selected.contentSource) || {}) },
  features: { ...defaults.features, ...((selected.features) || {}) }
}
export const featureEnabled = name => siteConfig.features[name] === true
export default siteConfig
