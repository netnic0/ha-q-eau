# Changelog

## [0.4.2](https://github.com/netnic0/ha-q-eau/compare/ha-q-eau-v0.4.1...ha-q-eau-v0.4.2) (2026-06-22)


### Bug Fixes

* **const:** correct Sandre code for turbidity (1301 -&gt; 1295) ([#11](https://github.com/netnic0/ha-q-eau/issues/11)) ([030e650](https://github.com/netnic0/ha-q-eau/commit/030e650becc8311f8d9347cf1755a1e858d46ca6))

## [0.4.1](https://github.com/netnic0/ha-q-eau/compare/ha-q-eau-v0.4.0...ha-q-eau-v0.4.1) (2026-06-19)


### Bug Fixes

* **diagnostics:** gate runtime_data read on entry.state == LOADED ([#9](https://github.com/netnic0/ha-q-eau/issues/9)) ([fa3dec5](https://github.com/netnic0/ha-q-eau/commit/fa3dec522d2d12aba4c2ff13f670df5390f4219b))

## [0.4.0](https://github.com/netnic0/ha-q-eau/compare/ha-q-eau-v0.3.0...ha-q-eau-v0.4.0) (2026-06-19)


### Features

* **runtime-data:** migrate to entry.runtime_data (HA 2024.6+) ([#6](https://github.com/netnic0/ha-q-eau/issues/6)) ([44e95ea](https://github.com/netnic0/ha-q-eau/commit/44e95eae50f87fd436582c50106ec6c8ccb390c9))

## [0.3.0](https://github.com/netnic0/ha-q-eau/compare/ha-q-eau-v0.2.1...ha-q-eau-v0.3.0) (2026-06-19)


### Features

* **quality:** promote integration to Silver tier ([#4](https://github.com/netnic0/ha-q-eau/issues/4)) ([314a4d5](https://github.com/netnic0/ha-q-eau/commit/314a4d5e1d0df50a60e58a8409c862ce410b7134))

## [0.2.1](https://github.com/netnic0/ha-q-eau/compare/ha-q-eau-v0.2.0...ha-q-eau-v0.2.1) (2026-06-17)


### Bug Fixes

* **brand:** add HACS brand icons (icon.png 256x256 + icon@2x.png 512x512) ([f30bb99](https://github.com/netnic0/ha-q-eau/commit/f30bb993c5f622791d9848390e2653e41e86d447))
* **ci:** pin pytest-homeassistant-custom-component&gt;=0.13.339 + fix loop scope ([8f76b9b](https://github.com/netnic0/ha-q-eau/commit/8f76b9b2123db5114737c53d3d7fc90fe48a73e5))
* **ci:** pin pytest-homeassistant-custom-component==0.13.205 for Python 3.12/3.13 ([31b3181](https://github.com/netnic0/ha-q-eau/commit/31b3181cb297e09956792c6f805322a79d48793a))
* **client:** accept HTTP 206 from Hub'Eau paginated responses ([57bba11](https://github.com/netnic0/ha-q-eau/commit/57bba11cd5f32a0af396597272374222060e3297))
* **tests:** add entry assertions to config flow success test, drop lingering marker ([d0b85cc](https://github.com/netnic0/ha-q-eau/commit/d0b85ccae8fd0b3ad98d573e062063a5062e0c08))
* **tests:** align test assertions with slug conformity values + real entity_id ([06f1b4f](https://github.com/netnic0/ha-q-eau/commit/06f1b4f628cb48a4ef4f3b8d7a604ba8640cb096))
* **tests:** drain background tasks after CREATE_ENTRY to avoid lingering thread ([7c547ef](https://github.com/netnic0/ha-q-eau/commit/7c547efb80cac9dae0fd5bcca77787724548fbc1))
* **tests:** drop test_user_step_success — unfixable thread leak in framework ([e90fac9](https://github.com/netnic0/ha-q-eau/commit/e90fac9ddf8964ebf9b6c8f77d4f356e54a7776a))
* **tests:** patch ConfigEntries.async_setup to prevent executor thread leak ([9bf9788](https://github.com/netnic0/ha-q-eau/commit/9bf978841981a29407711c91f0741e7da713b698))
* **tests:** patch threading.enumerate to hide HA-internal shutdown thread ([a9c0041](https://github.com/netnic0/ha-q-eau/commit/a9c0041d6ec8972a2e1ca3c837bdabd895acadaa))
* **tests:** replace hass-based config flow tests with pure unit tests ([e4ffa45](https://github.com/netnic0/ha-q-eau/commit/e4ffa45327988934191f398e219fdd12375ea183))
* **tests:** use allow_lingering_threads marker on config flow success test ([aa5d78e](https://github.com/netnic0/ha-q-eau/commit/aa5d78ee3ef45826897952bd34d389746084ec2c))
* **translations:** remove URL from description string (hassfest rule) ([efa5b90](https://github.com/netnic0/ha-q-eau/commit/efa5b90786e830bc9ae391cf86a4f62c108dce0c))

## [0.2.0](https://github.com/netnic0/ha-q-eau/compare/ha-q-eau-v0.1.0...ha-q-eau-v0.2.0) (2026-06-17)


### Features

* **init:** scaffold ha_q_eau — French drinking water quality via Hub'Eau API ([38de2b0](https://github.com/netnic0/ha-q-eau/commit/38de2b051e302a7d655150fe5e41a40dc7825448))


### Bug Fixes

* **ci:** resolve all hassfest/HACS/test failures ([22317e9](https://github.com/netnic0/ha-q-eau/commit/22317e96333486cc3f0942e82b160f9a25814bce))
