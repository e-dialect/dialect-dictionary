// Public deployment settings only. Never put secrets in this file.
import defaults from './defaults.json';
import generated from './generated.json';

let supplied = null;
// #ifdef H5
// eslint-disable-next-line no-underscore-dangle
supplied = window.__DICTIONARY_CONFIG__;
// #endif
const selected = supplied || generated;
const siteConfig = {
  ...defaults,
  ...selected,
  dialect: { ...defaults.dialect, ...((selected.dialect) || {}) },
  contentSource: { ...defaults.contentSource, ...((selected.contentSource) || {}) },
  features: { ...defaults.features, ...((selected.features) || {}) },
};
export const featureEnabled = (name) => siteConfig.features[name] === true;
export default siteConfig;
