# Frontend deployment settings

One public JSON schema supplies both frontends. The deployment serves JavaScript assigning `window.__DICTIONARY_CONFIG__` before either application starts. Web loads `/site-config.js`, UniApp H5 loads `/mobile/site-config.js`; the H5 artifact is built at `/mobile/`. Runtime changes take effect on reload and require no source edits or rebuild. Do not place credentials in public settings.

For standalone development or mini-program builds, generate settings from the root configuration:

```sh
node tools/frontend-config/generate.mjs config/examples/coast.json
```

This writes both public runtime assets, compiled fallback JSON, mini-program name, and navigation title. It performs no build, deployment, or upload. `UNI_APP_ID` and `WECHAT_APP_ID` set your own application identifiers; original identifiers are blanked. For a mini-program build, validate its requirements explicitly:

```sh
WECHAT_APP_ID=your-own-appid node tools/frontend-config/generate.mjs /path/to/your-config.json --mini-program
cd uni-app
npm run build:mp-weixin
```

Mini-program API URLs must be absolute HTTPS URLs registered for your own application. A local relative `/api` is for H5. Mini-program publishing still requires WeChat tooling and review; Compose serves the Web and H5 sites only.

`siteConfig` is the default export of each frontend's `src/config/site.js`. `featureEnabled(name)` returns true only for an explicit boolean true; Vue templates use `$site` and `$featureEnabled`. Web `routeEnabled(name)` and UniApp `pageEnabled(path)` control navigation as well as direct visits. Features default to false: `pinyin` (upstream phonology tutorials, lookup tables, synthesized pronunciation), `kinship`, `geography`, `music`, `quiz`, `dailyExpressions`, `translation`, and `legacyLinks`. Dictionary text and real recordings from the deployment's own database remain available. Geography disables the original county/town controls; it does not replace them with another dialect's geography.

Enabling an upstream feature does not adapt its content to a new dialect. Its source tables, examples, or algorithms need separate review. Source files and notices retain the upstream provenance; deployment name changes do not grant permission to copy upstream dictionary data.

Run `node tools/frontend-config/test.mjs` from the repository root for dependency-free runtime checks. It executes the actual Web and H5 configuration/guard modules with both example brands, verifies disabled feature routes and enabled core dictionary routes, checks strict boolean feature switches, and checks mini-program generated fallback without browser globals. These checks do not replace rendered browser or real-device verification.

Phonology sample audio has no default remote host. Set optional public `phonologyAudioBase` only to an audio source you are authorized to use; its MP3 filenames match the retained upstream table keys. Both `features.pinyin=true` and a nonempty audio base are required to load samples. `contentSource.url` remains attribution only. All homepage/tool cards and mobile tabs use text and existing UI icons, with no purchased illustrations or additional static resources.

Safe defaults are canonical in `tools/frontend-config/defaults.json`; the generator synchronizes copies into each frontend. Generated brand settings are never a source of defaults for another brand. When a runtime configuration is present, missing feature flags become false and missing optional audio/feedback configuration becomes empty/null, even if the artifact was compiled for 兴化语记. The generator regression test uses an automatically removed temporary project.

Optional `feedback` contains `webUrl`, `miniProgramAppId`, and `productId`. With `legacyLinks=true`, H5 opens its configured web URL and WeChat opens the configured feedback mini-program. The generated `mp-weixin.embeddedAppIdList` includes that feedback app only when configured and enabled; other brands receive an empty list. This feedback application ID never becomes your own `WECHAT_APP_ID`.
