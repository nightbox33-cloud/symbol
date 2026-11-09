# Auditoría ofensiva — Symbol (XYM) mainnet y stack de la fundación

Fecha del anclaje live: **2026-11-09**
Alcance: nodo/consenso/p2p (`client/catapult`), REST, catbuffer, SDKs, bridge y tooling de la Symbol Foundation.

**Veredicto: no hay crítico live que cumpla los 4 criterios en el nodo/consenso de Symbol.**
Sí hay **dos defectos reales en el código del bridge** (`symbol/product`), ambos reproducidos contra el clon:

* **H‑1** (§6): el parser de depósitos Ethereum no valida el selector ERC‑20 ⇒ `approve(bridge, X)` cuenta como
  depósito de X (PoC: 1e27 unidades con 1000 approvals).
* **H‑2** (§7): una transferencia con `message` no‑UTF‑8 mata el downloader (DoS permissionless de 1 tx) y, con el
  *scheduling* del README, el `reset()` del checkpoint re‑inserta depósitos ya pagados ⇒ pago repetido del escrow.

Ninguno es explotable **live** hoy: la única instancia desplegada y accesible es testnet (Symbol testnet + Sepolia),
sin TVL de terceros. Condición que los convertiría en críticos live en §6.3 y §7.1‑7.2.

---

## 1. Requisito previo: repos de la fundación

### 1.1 Orgs / espacios enumerados

| org / espacio | estado | notas |
|---|---|---|
| `github.com/symbol` | **activo, 32 repos** | org principal; nodo, REST, SDKs, catbuffer, bootstrap, bridge, wallets, explorer, docs |
| `github.com/nemtech` | vacío | descripción: "Repositories moved to symbol organization" |
| `github.com/symbolplatform` | activo | imágenes Docker (`symbolplatform/bridge:1.1`) |
| `github.com/nemproject` | activo | **fuera de alcance**: NEM/XEM (NIS, nem-core, nanoWallet); cadena y nodo distintos de Symbol |
| `github.com/nemgroup` | sin repos de protocolo | home de la NEM Group |

No se detectaron GitHub/GitLab/Bitbucket adicionales de la fundación que hospeden el nodo o el bridge.
No hay repos privados accesibles desde esta sesión (solo `github.com` + `pypi.org`).

### 1.2 Inventario de repos (org `symbol`) con commit exacto

`SHA` = HEAD del branch por defecto en el momento del anclaje (`gh api repos/symbol/<repo>/commits/HEAD`).

| repo | branch | HEAD SHA | clonado | rol en el alcance |
|---|---|---|---|---|
| `symbol` (monorepo) | dev | `cdfc513891e8` (2026-11-02) | **sí** | nodo catapult C++, REST, sdk/js, sdk/python, catbuffer, openapi |
| `product` | dev | `cb3151d5c505` (2026-11-06) | **sí** | bridge (escrow terceros), wallets, explorer, lightapi, faucet |
| `symbol-bootstrap` | main | `ce5c7c6b1e76` (2025-09-23) | **sí** | preset **mainnet**: params live, fork heights, sinks |
| `networks` | main | `e9d55462d7b0` (2023-03-14) | **sí** | vacío (solo README) → no es fuente de params |
| `miscellaneous` | dev | `b87b2992b521` (2026-03-30) | **sí** | scripts de operación |
| `statistics-service` | dev | `0a460f78144d` (2026-10-30) | **sí** | monitoring; usado para descubrir gateways REST |
| `sdk-java` | dev | `43d103594629` (2025-09-22) | no | cliente |
| `symbol-sdk-typescript-javascript` | dev | `360e3cc0ba19` (2025-09-25) | no | cliente |
| `symbol-openapi` | main | `83d6033f6d2d` (2026-04-13) | no | spec |
| `catapult-rest` | main | `d0e7edee32a9` (2022-01-11) | no | **archivado**; el código live está en `symbol/client/rest` |
| `explorer` | dev | `e8b0bed554a0` (2025-09-23) | no | UI/indexer, sin custodia |
| `symbol-docs` | main | `ec694fa06502` (2026-05-27) | no | documentación |
| `faucet` | dev | `f3c2c9c623c4` (2022-09-23) | no | testnet, sin TVL |
| `desktop-wallet` | dev | `117e9c175cf0` (2025-09-26) | no | cliente (claves locales) |
| `mobile-wallet` | main | `3e2b1b454e84` (2022-11-09) | no | cliente; su config vive en `product/wallet` |
| `wallets-lib` | dev | `cb164cfef5f6` (2022-06-01) | no | librería de clientes |
| `ledger-app-symbol` | main | `94603ef8209d` (2026-08-24) | no | firmware app (firma local) |
| `trezor-firmware` | master | `e77082f34f4f` (2021-05-24) | no | fork de terceros, >1 GB, no es código Symbol |
| `symbol-server-dependencies` | dev | `2e1c887259de` (2026-10-27) | no | dependencias de build |
| `nodewatch` | main | `75ee6032191b` (2022-03-16) | no | **archivado**; el live está en `product/explorer/nodewatch` |
| `symbol-cli`, `symbol-openapi-generator`, `symbol-technicalref`, `symbol-uri-scheme`, `symbol-hd-wallets`, `qr-library`, `ripemd`, `garush`, `bazinga`, `sdk-typescript`, `symbol-wallet-address-book`, `.github` | — | `c70ce740…`, `0916acb9…`, `b59758a6…`, `1a7317b1…`, `d0d68d9b…`, `6141b777…`, `076cb06d…`, `4bac32d2…`, `0c9f6588…`, `0cf86fdb…`, `abcfbabf…`, (vacío) | no | todas archivadas, vacías o sin custodia de valor (`.github` está vacío) |

**Bloqueado / no disponible (no se declara cobertura completa de esa pieza):**
el **contrato ERC‑20 wrapped** (`wXYM`/`bXYM`) y el **repositorio de despliegue del bridge** (compose/nginx/keys)
no están en ninguna org accesible. Solo se dispone del *operador* Python (`symbol/product/bridge`).
No hay repos privados clonados; si la fundación opera un repo privado de despliegue, no está cubierto.

### 1.3 Mapa componente live → repo + commit + artefacto

| componente / identificador live | repo | ruta | commit | artefacto |
|---|---|---|---|---|
| chain **104** (mainnet), genHashSeed `57F7DA20…B2D6` | `symbol` | `client/catapult` | `cdfc513891e8` | `catapult.server` 1.0.3.9 (`client/catapult/CHANGELOG.md`) |
| plugin params live (ver §2.3) | `symbol` + `symbol-bootstrap` | `client/catapult/src/catapult/model/BlockchainConfiguration.cpp`, `presets/mainnet/network.yml` | `cdfc513891e8` / `ce5c7c6b1e76` | `/network/properties` del nodo |
| XYM `0x6BED913F A20223F8` (div 6, supply mutable) | `symbol` | genesis `resources/` + live REST | idem | `/mosaics/6BED913FA20223F8` |
| REST gateway `restVersion 2.5.1` | `symbol` | `client/rest` | `cdfc513891e8` | `symbolplatform/symbol-rest:2.5.1` |
| bridge operador (wrap/unwrap/swap) | `product` | `bridge/` | `cb3151d5c505` | `symbolplatform/bridge:1.1` (`product/bridge/README.md`) |
| API bridge | `product` | `bridge/bridge/api` | `cb3151d5c505` | `bridge.symbol.tools/{,testnet/}ethereum-{wrapped,native}` |
| wallets (config bridge/uniswap) | `product` | `wallet/symbol/mobile/src/main/config/config.json` | `cb3151d5c505` | app móvil symbol |
| rental/harvest fee sinks | `symbol-bootstrap` | `presets/mainnet/network.yml` (L14‑19) | `ce5c7c6b1e76` | cuentas mainnet (saldos §3) |

---

## 2. Anclaje del estado live (medido, no de memoria)

### 2.1 Cadena

```
GET https://xym776.allnodes.me:3001/network/properties      (gateway mainnet, restVersion 2.5.1)
GET https://nodewatch.symbol.tools/api/symbol/height
```

* `network.identifier = mainnet`, `generationHashSeed = 57F7DA205008026C776CB6AED843393F04CD458E0AA2D9F1D5F31A402072B2D6`
* `epochAdjustment = 1615853185s` (2021‑03‑16), `blockGenerationTargetTime = 30s`
* altura **5 936 121**, finalizada **5 936 100** (2026‑11‑09)
* `currencyMosaicId = harvestingMosaicId = 0x6BED913FA20223F8`, `maxMosaicsPerAccount = 1000`

### 2.2 Fork heights live (idénticos al preset `symbol-bootstrap/presets/mainnet/network.yml`)

| fork | altura | estado |
|---|---|---|
| `totalVotingBalanceCalculationFix` | 528 000 | activo |
| `treasuryReissuance` | 689 761 | activo |
| `strictAggregateTransactionHash` | 1 690 500 | activo |
| `skipSecretLockUniquenessChecks` | 3 191 538 | activo |
| `forceSecretLockExpirations` | 3 197 458, 3 197 781 | activo |
| `skipSecretLockExpirations` | 3 197 860, 3 197 866 | activo |
| **`uniqueAggregateTransactionHash`** | **4 759 100** | **activo** (head 5.936M) |

→ Todo el código fork‑gated de 1.0.3.4/1.0.3.7/1.0.3.9 **ya está en vigor**.

### 2.3 Params de plugins live (relevantes para dinero)

```json
"aggregate": { "maxTransactionsPerAggregate":"100", "maxCosignaturesPerAggregate":"25",
               "enableStrictCosignatureCheck": false, "enableBondedAggregateSupport": true,
               "maxBondedTransactionLifetime":"48h" },
"lockhash":  { "lockedFundsPerAggregate":"10'000'000", "maxHashLockDuration":"2d" },
"locksecret":{ "maxSecretLockDuration":"365d", "minProofSize":"0", "maxProofSize":"1024" },
"mosaic":    { "mosaicRentalFee":"500000", "maxMosaicDivisibility":"6", "maxMosaicDuration":"3650d" },
"namespace": { "rootNamespaceRentalFeePerBlock":"2", "childNamespaceRentalFee":"100000" },
"network":   { "harvestBeneficiaryPercentage":"25", "harvestNetworkPercentage":"5",
               "minHarvesterBalance":"10'000'000'000", "maxHarvesterBalance":"50'000'000'000'000" }
```

### 2.4 Código auditado = código live

`client/catapult/CHANGELOG.md` head = **1.0.3.9 (23‑Sept‑2025)**; el árbol `dev` sólo añade dependabot.
El único cambio de consenso posterior a 1.0.3.8 es el fix de unicidad del hash de agregados, **ya fork‑activado**
a 4 759 100 (head 5 936 121).

---

## 3. Inventario ajeno medido (mainnet, height ≈5 936 100)

| cuenta / activo | dirección | saldo |
|---|---|---|
| supply total XYM (`0x6BED913F…F8`) | — | **8 570 172 810.049058 XYM** (8 570 172 810 049 058 atomic) |
| harvest network fee sink (`NAVORTEX3…`) | `682AE8CC97DA1E1052D00851B46C2343A5C054EFCAC4517F` | **36 246 523.820925 XYM** |
| namespace+mosaic rental fee sink (`NCVORTEX4…`) | `68AAE8CC97E5C7D44012CC0871DA979EF770BA61628A312D` | **690 014.199317 XYM** |
| uncirculating `E85D10BF…` | `688E494F708C25C4E4CE77B933FDA54E81EDE01F9BD9D7DD` | **1 352 987 951.624116 XYM** |
| uncirculating `FE454406…` | `6840D50A498C3EEDF23F7455291ABA30EFEA0389D80F5145` | **628 549 820.123009 XYM** |
| sinks V1 (`NBUTOBVT…`, `NBDTBUD6…`, `NC733XE7…`) | — | residuo histórico, no consultado |

Cuentas "uncirculating" declaradas por el propio nodo (`restUncirculatingAccountPublicKeys`):
`A4739036…`, `2BF1E1F3…`, `E85D10BF…`, `FE454406…` (las dos primeras son los sinks; las dos últimas, tesorería).

**Nota de alcance:** Symbol **no** tiene contratos/DeFi on‑chain ni pools. El "inventario de terceros" live es:
(a) saldos y cuentas multisig de usuarios, (b) escrows de `SecretLock`, (c) depósitos de `LockFunds` (10 XYM por
agregado bonded), (d) sinks/tesorería de arriba. Para drenar (a)–(d) hace falta un fallo de autenticación,
de contabilidad de supply, de hash/replay o de firma en el nodo.

---

## 4. Veredicto: **no crítico live** — vectores revisados y el hecho que los mata

Cada fila es un candidato evaluado contra el código del clon y el estado live; "mata" = hecho concreto que
impide el claim (no es una lista de keywords: es el descarte de cada hipótesis).

| # | Candidato | Dónde | Por qué **no** es crítico live |
|---|---|---|---|
| 1 | **Hash de agregado no único** → dos agregados distintos con el mismo hash; el observer `CompletedAggregate` acredita el lock al owner **sin comprobar `lockInfo.Status == Unused`** ⇒ un lock de 10 XYM podría pagarse N veces (mint neto) | `plugins/txes/aggregate/src/plugins/AggregateTransactionPlugin.cpp` (`dataBuffer`), `validators/AggregateTransactionsHashValidator.cpp`, `plugins/txes/lock_hash/src/observers/CompletedAggregateObserver.cpp`, `lock_shared/…/LockStatusAccountBalanceObserver.h` | Pre‑V3 el buffer firmado/hasheado excluía **8** bytes (`PayloadSize` + reserved) ⇒ `PayloadSize` era malleable y, para v1, el validador aceptaba **4** cálculos distintos del `TransactionsHash` (merkle normal/`InvalidMerkleHashBuilder` × con/sin padding). Eso permitía identidad repetida. **Mata:** `uniqueAggregateTransactionHash = 4 759 100` activo (head 5 936 121); `AggregateTransactionVersionValidator` sólo admite **v3**; v3 `Footer_Size = 4` ⇒ `PayloadSize` entra en el buffer ⇒ identidad = SHA3(sig‖pubkey‖genHash‖[ver,net,type,TransactionsHash,PayloadSize]‖cosig‑pubkeys). Los 20 pares `corruptAggregateTransactionHashes` del nodo son históricos y **sólo** se consultan para `AggregateVersion == 1`, que ya se rechaza. |
| 2 | **Secret locks duplicados** (incidente 2024, workarounds `skip/forceSecretLockExpirations` ~3.19M) | `plugins/txes/lock_secret/src/observers/*`, `ExpiredSecretLockInfoObserver.cpp` | Los heights de skip/force están consumidos (3.19M < 5.93M). Un `SecretLock` sólo debita al firmante (`BalanceDebitNotification`, con `BalanceValidator` ⇒ `Failure_Core_Insufficient_Balance` si no hay saldo) y crea una entrada en la historia del `(secret, recipient)`; el proof usa `iter.get().back()` y acredita **sólo** al `RecipientAddress` del lock ⇒ no hay credo duplicado ni destino ajeno. |
| 3 | **`MosaicSupplyRevocation`** para quedarse con mosaicos de terceros | `plugins/txes/mosaic/src/plugins/MosaicSupplyRevocationTransactionPlugin.cpp`, `validators/MosaicRequiredValidator.cpp`, `validators/ActiveMosaicView.cpp` | Se exige `mosaic.definition().ownerAddress() == signer` (`Failure_Mosaic_Owner_Conflict`) **y** flag `Revokable` (`Failure_Mosaic_Required_Property_Flag_Unset`); el plugin además no valida restricciones a propósito. Sin ser owner no hay camino. |
| 4 | **Overflow / cap de supply** al emitir (`newSupply < initialSupply`) | `validators/MosaicSupplyChangeAllowedValidator.cpp` | El chequeo de wrap está presente y el cap live es `maxMosaicAtomicUnits = 8 999 999 999 000 000`; sólo afecta a mosaicos propios del firmante. |
| 5 | **Rental fees / harvest fees** (sinks con 36.9M XYM) | `plugins/txes/namespace/src/observers/*`, `mosaic/src/observers/MosaicDefinitionObserver.cpp`, `coresystem` fee observers | El fee se **debita al firmante** y se **acredita al sink**; no hay path de refund ni de débito del sink. Mover esos saldos exige la clave del sink (rol privilegiado ⇒ prohibido como crítico). |
| 6 | **Multisig**: robar cuentas multisig | `plugins/txes/multisig/src/validators/*`, `plugins/txes/aggregate/src/validators/Basic|StrictAggregateCosignaturesValidator.cpp` | `enableStrictCosignatureCheck = false` está live, pero ese check es anti‑griefing (rechaza cosignatarios inútiles), no de autorización; la autorización sigue siendo `minApproval` cosignaturas de cosignatarios en el cache. No encontré path de conteo duplicado (el `ArrayPointerFlagMap` deduplica y rechaza duplicados en basic). |
| 7 | **Malleabilidad v3** (nuevo código de 1.0.3.9) | `AggregateTransactionPlugins` v3 buffer | El buffer cubre `Version/Network/Type/TransactionsHash/PayloadSize` y los pubkeys de cosignatarios van en `merkleSupplementaryBuffers`; `Reserved1` (excluido) no se interpreta. No hay campo semántico fuera de la identidad. |
| 8 | **Precompiles / VM / pallets / CosmWasm / SVM** | — | No existen en Symbol: no hay VM on‑chain ni contratos. Los "program ids"/módulos son plugins nativos del nodo, ya cubiertos arriba. |
| 9 | **Bridge** (escrow de terceros) | `product/bridge` | **Bugs reales** (§6 H‑1, §7 H‑2), pero **no live en mainnet**: ver §6.3. |
| 10 | **Bloque inválido gratis / overdraw dentro de una tx**: la fee se debita *después* de las notificaciones custom (`shouldApplyFeeDebitLast`, fork `treasuryReissuance`) ⇒ ¿una tx puede pasar validación gastando todo el saldo y reventar el `debit` de la fee en ejecución (bloque inválido, coste 0 para el atacante)? | `src/catapult/model/NotificationPublisher.cpp` (líneas 163‑192 y 222‑230), `src/catapult/model/NotificationPublisher`/`ProcessingNotificationSubscriber`, `plugins/coresystem/src/validators/BalanceValidator.cpp`, `src/catapult/state/AccountBalances.cpp` | **Mata:** el procesado valida y **ejecuta notificación a notificación** en la misma pasada (`chain/BatchEntityProcessor.cpp` + `chain/ProcessingNotificationSubscriber`), no "valida todo y luego ejecuta". Tras el `BalanceTransferObserver` de la transferencia (que ya debitó), la `BalanceDebitNotification` de la fee se valida contra el saldo **ya actualizado** ⇒ `Failure_Core_Insufficient_Balance` ⇒ la tx se rechaza limpiamente. `AccountBalances::debit` sí lanza `catapult_runtime_error` si falta un validador, pero cada débito (`BalanceTransfer` y `BalanceDebit`) tiene el suyo registrado (`CoreSystem.cpp` L199‑200). |
| 11 | **Inflar/revocar XYM** (el nemesis currency) | `plugins/txes/mosaic/src/validators/*`, estado live del mosaico | **Mata:** el mosaico `0x6BED913FA20223F8` live tiene `flags = 2` (**Transferable**; sin `Supply_Mutable` ni `Revokable`), `duration = 0`, owner = dirección nemesis. Sin `Supply_Mutable` sólo podría cambiar supply si el owner tuviera el 100% (`MosaicSupplyChangeAllowed`), y sin `Revokable` `MosaicSupplyRevocation` falla siempre. No hay mint ni revoke de XYM. |
| 12 | **Squatting de claves remotas** (`AccountKeyLink`/`VrfKeyLink`/`VotingKeyLink`): la clave remota no firma el link ⇒ cualquiera puede enlazar la clave de un tercero a su cuenta | `plugins/coresystem/src/validators/KeyLinkValidators.h`, `plugins/txes/account_link/src/*` | Es **griefing permissionless** (el dueño real ya no puede enlazar esa clave), pero no mueve valor: importance/harvest van a la cuenta que cosecha y el atacante no tiene la privada VRF ⇒ no cumple "saca más valor del que puso". |

Conclusión §4: **no crítico live** en el nodo Symbol a la altura 5 936 121 (8.57B XYM de supply, 2.7M+ XYM en sinks/tesorería medidos, todos los forks de seguridad activos).

---

## 5. Cómo se descartó el candidato más cercano (para trazabilidad)

Cadena de razonamiento sobre el primitivo "mint neto" (pre‑fork):

1. `LockFundsTransaction` debita `lockedFundsPerAggregate = 10 XYM` del firmante y crea `HashLockInfo{key = hash del agregado}`.
2. Al confirmarse el `AggregateBonded`, `CompletedAggregateObserver` → `LockStatusAccountBalanceObserver`:
   `lockInfo.Status = Used; accountState.Balances.credit(lockInfo.Amount)` — **acredita siempre**, sin mirar el estado previo.
3. Si existieran dos agregados distintos con el **mismo** `EntityHash`, ambos completarían y el mismo lock se acreditaría dos veces ⇒ +10 XYM por ciclo, sin contrapartida (inflación contra todos los tenedores).
4. Pre‑fork eso era alcanzable porque el `EntityHash` de un agregado = SHA3(sig‖pubkey‖genHash‖buffer) y el `buffer` (v1/v2) **omitía `PayloadSize`**; para v1 el validador aceptaba además 4 cálculos distintos del `TransactionsHash`, incluido un merkle builder inválido — de ahí los 20 pares whitelisted en `corruptAggregateTransactionHashes` (p. ej. `B35D60C8…` y `D91689D6…` mapean al mismo valor `D8915C7E…`: dos agregados con el mismo contenido y hashes distintos).
5. **Hoy** el paso 4 es imposible: v1/v2 rechazados y v3 incluye `PayloadSize` ⇒ la identidad cubre la frontera payload/cosignaturas. Por eso **no** es crítico live; y por eso el fix se marcó "BREAKING FORK".

---

## 6. H‑1 — Bridge `symbol/product`: el parser de depósitos Ethereum no valida el selector ERC‑20

> **Estado: crítico en código, NO live hoy (solo testnet).** Se documenta porque es un fallo real,
> reproducible y de drenaje total del escrow en cuanto exista despliegue mainnet de `ethereum-wrapped`.

### 6.1 Bug

`bridge/ethereum/EthereumUtils.py::extract_wrap_request_from_transaction` decodifica el depósito por **offsets
fijos** de calldata y **nunca comprueba los 4 primeros bytes**:

```python
input_data = parse_rpc_response_hex_bytes(transaction_json['input'])
if len(input_data) < DESTINATION_ADDRESS_OFFSET: return make_wrap_error_result(...)
recipient_address = input_data[16:36]                       # 4 selector + 12 padding
if recipient_address != target_search_address.bytes: return None
if DESTINATION_ADDRESS_OFFSET == len(input_data): return make_wrap_error_result('required message is missing')
if not transaction_with_meta_json['meta']['isSuccess']: return make_wrap_error_result(...)
amount = int.from_bytes(input_data[36:68], 'big')
destination_address = input_data[68:]
```

Sólo se asume la forma de `transfer(address,uint256)`. Pero `approve(address,uint256)` tiene **idéntico layout**
(spender en 16..36, amount en 36..68), **no mueve tokens** y **no requiere saldo**, y su `input` puede llevar
bytes extra (24 bytes = dirección Symbol raw) que Solidity ignora. El conector
(`EthereumConnector.incoming_transactions`, línea 259: `ots_searchTransactionsBefore(<tokenContract>, …)`) pide las
txs en las que aparece el **contrato del token** — es decir, todas las llamadas ERC‑20 dirigidas a él, `approve`
incluida. El parser sólo verifica que el address de 16..36 sea el bridge, que existan bytes de mensaje y que
`isSuccess == true`: **nunca** el selector ni que se hayan movido tokens (el PoC fabrica esa respuesta RPC igual
que el harness del propio repo, `tests/test/MockEthereumServer.py`).

Resultado: **cualquiera con una cuenta Ethereum y cero wXYM** encola un `unwrap` por el importe que quiera,
y `send_payouts --unwrap` paga XYM nativo **desde el escrow del bridge** (depósitos de otros usuarios).
Un `transfer` no es requisito; no hay verificación contra el evento `Transfer`, ni contra el balance del bridge,
ni contra `wXYM.totalSupply`.

### 6.2 PoC (contra el clon, sin modificar el código auditado)

`audit/poc/bridge_approve_poc.py` importa el parser real y le pasa la respuesta RPC que construiría el conector:

```
$ python3 -m venv /tmp/venv && . /tmp/venv/bin/activate
$ pip install symbol-sdk-python==3.3.3 web3==8.0.0
$ PYTHONPATH=<clone>/product/bridge python3 audit/poc/bridge_approve_poc.py <clone>/product/bridge
```

Salida (resumida, ejecutada 2026‑11‑09):

```
[control: transfer(bridge, amount)]
  -> QUEUED AS UNWRAP REQUEST   amount = 1000000000000000000000000
                                destination = NCVORTEX4XD5IQASZQEHDWUXT33XBOTBMKFDCLI
[exploit: approve(bridge, amount) + 24-byte destination]
  calldata: 0x095ea7b3 000…000 00d6dcee…f9ba 000…d3c21bcecceda1000000 68aae8cc…312d
  -> QUEUED AS UNWRAP REQUEST   amount = 1000000000000000000000000
                                destination = NCVORTEX4XD5IQASZQEHDWUXT33XBOTBMKFDCLI
[batch] 1000 distinct approve() txs -> 1e27 atomic units queued for payout
```

Contramedidas que sí funcionarían pero no están: comprobar `input_data[:4] == a9059cbb`, y/o verificar el evento
`Transfer(address,address,uint256)` con `address == token` y `topics[2] == bridge` y usar **ese** `amount`.

### 6.3 Por qué **no** es crítico live (hecho que lo mata)

| comprobación | resultado |
|---|---|
| `https://bridge.symbol.tools/ethereum-wrapped/…` (URL mainnet del wallet) | **404** (nginx) en `/`, `/unwrap/requests`, `/wrap/requests` |
| `https://bridge.symbol.tools/testnet/ethereum-wrapped/…` | **200**, requests y payouts reales (Sepolia → Symbol testnet) |
| `https://bridge.symbol.tools/testnet/ethereum-native/` | **200**: `mode=swap`, bridge Symbol testnet `TBYWIC4J…`, wrapped Sepolia `0x065e308D…` |
| `bridge.symbol.tools/ethereum-native/` | **404** |
| `known-accounts.json` (wallet) | sólo registra **una** cuenta bridge, en `symbol.testnet` (`TBQAAMLT…`) |
| `config.json` (wallet) "mainnet" Uniswap: `bxym=0x5e8343a4…`, `weth=0x3A8C1bd5…Ccb1`, `router=0xc50f6b8A…c349` | **no son contratos en Ethereum mainnet**: blockscout devuelve `is_contract=false`, `coin_balance=null`, `has_logs=false`, `has_token_transfers=false` para WETH y router (y el token es "not a token contract" en ethplorer) ⇒ la config mainnet es placeholder, no hay swap/stake desplegado |
| contrato `wXYM`/`bXYM` en la org `symbol` | **no está** ⇒ escrow/token no verificable |

⇒ Hoy el único despliegue accesible es **testnet sin TVL** ⇒ por criterio no se reporta como crítico live
(sería el error que el propio encargo prohíbe). **Pasa a crítico live** en el momento en que exista una instancia
`ethereum-wrapped` mainnet con saldo nativo en su cuenta bridge: el ataque es permissionless, cuesta sólo gas
(una tx `approve`), no requiere wXYM, y el PnL es ilimitado salvo `max_transfer_amount` (por request) y
`max_daily_transfer_amount` (rolling 24 h) — ambos límites de configuración, no de código.

### 6.4 Remedio

1. Validar selector (`transfer`) y/o reconstruir el depósito desde el log `Transfer` filtrado por
   `address == token` y `topics[2] == bridge` (mismo `amount` del log, no de la calldata).
2. Comprobar `isSuccess` **y** que el `tx.to == tokenContract`.
3. Reconciliar cada payout contra el incremento real de balance del bridge en la cadena wrapped
   (hoy `download_balance_changes` sólo existe para la cadena **nativa**).

---

## 7. H‑2 — Bridge `symbol/product`: crash permissionless del downloader y marcador de pago no idempotente

> **Estado: alto en cualquier despliegue, NO crítico live hoy (solo testnet, misma evidencia que H‑1 §6.3).**
> Se documenta porque es permissionless, cuesta una transacción y, con el *scheduling* del README, convierte
> un depósito en un pago repetido desde el escrow.

### 7.1 Bug 1 — excepción no capturada sobre datos del atacante

`bridge/symbol/SymbolUtils.py:24` (y el gemelo NEM `bridge/nem/NemUtils.py:63`):

```python
destination_address = unhexlify(transaction_json['message']).decode('utf8')
```

El `message` es **arbitrario, lo elige quien envía**. El REST lo entrega como hex (siempre válido), pero el
`.decode('utf8')` revienta con cualquier byte no‑UTF‑8: `FF`, `C3`, `E2 28 A1`… o directamente **una dirección
Symbol en binario** (24 bytes). No hay `try/except` en `_download_requests` ni en `main_impl`; sólo un
`sys.excepthook` que loguea y hace `sys.exit(1)` (`workflows/main_impl.py:38-41`).

Orden exacto dentro de `_download_requests`:

```
calculate_search_range()      # checkpoint C
database.reset()              # ← borra filas con height > C
for tx in get_incoming_transactions_from(..., order=desc):   # ← aquí revienta
database.set_max_processed_height(end_height - 1)            # ← nunca se ejecuta
```

Consecuencia 1 (**DoS permanente, permissionless**): el checkpoint nunca avanza; cada ejecución posterior
re‑escanea desde C, vuelve a encontrar la tx veneno y vuelve a morir. Con el entrypoint que se publica
(`scripts/entrypoint.sh` → `wrappedflow.sh`, `set -e`), el fallo del download aborta **también** `send_payouts`
y las dos direcciones ⇒ el bridge queda congelado con una sola transferencia de 1 XYM. Y `nativeflow.sh`
(swap XYM→ETH) usa el mismo downloader.

### 7.2 Bug 2 — `reset()` + re‑inserción = pago repetido del mismo depósito

`WrapRequestDatabase.reset()` (`bridge/db/WrapRequestDatabase.py:365`) borra **todas** las filas con
`request_transaction_height > max_processed_height`, es decir exactamente las que se añadieron en la ventana que
acabó de reventar — incluidas las que ya estaban **pagadas** (SENT/COMPLETED). `add_request` es un `INSERT`
simple, así que al re‑escanear se re‑insertan como `UNPROCESSED`.

Secuencia de ataque (si `download_*` y `send_payouts` corren como trabajos periódicos independientes, que es lo
que describe el README y permite el contenedor por comando):

1. atacante envía la tx veneno `P` (mensaje `FF`) a la cuenta bridge;
2. atacante envía su depósito `D` (mensaje = su dirección) en una altura **mayor** que `P` (el escaneo es `order=desc`, así `D` se procesa antes de morir en `P`);
3. el download añade `D` y muere en `P` ⇒ checkpoint sigue en `C`;
4. `send_payouts` paga `D` (SENT/COMPLETED);
5. siguiente download: `reset()` borra `D` (height > `C`), lo re‑añade como `UNPROCESSED`, vuelve a morir en `P`;
6. `send_payouts` **vuelve a pagar `D`**… y así cada ciclo, hasta que el escrow se agote o alguien pare el proceso
   (los límites `max_transfer_amount`/`max_daily_transfer_amount` acotan el ritmo, no el total).

Coste para el atacante: el depósito `D` (que recupera en el primer pago) + dos fees. Ganancia: `D` por ciclo desde
el escrow de terceros.

### 7.3 PoC

`audit/poc/bridge_crash_replay_poc.py` (código real del clon, sin modificarlo):

```
$ pip install symbol-sdk-python==3.3.3
$ PYTHONPATH=<clone>/product/bridge python3 audit/poc/bridge_crash_replay_poc.py <clone>/product/bridge

(a) downloader crash
    control (message = ascii address)     -> 1000000 queued
    message 0xFF               -> UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff ...  << escapes the workflow
    message 0xC3               -> UnicodeDecodeError: ... unexpected end of data
    message 0xE2 0x28 0xA1     -> UnicodeDecodeError: ... invalid continuation byte

(b) paid marker lost across a crashed window (checkpoint 100)
    run 1: request at height 200 marked SENT (rows with SENT status = 1)
    reset(): rows left above checkpoint = 0 (paid row deleted)
    re-scan: request re-inserted as UNPROCESSED = 1 -> send_payouts pays it again
    => each cycle pays the same deposit again while the poison tx stays in the window
```

### 7.4 Remedio

1. Envolver el parseo del mensaje/dirección en `try/except` y emitir un `WrapError` (nunca dejar que una tx
   del usuario mate el workflow); idem `unhexlify` en NEM.
2. `add_request` → `INSERT ... ON CONFLICT(hash, subindex) DO NOTHING` y **nunca** degradar una fila pagada a
   `UNPROCESSED`; que `reset()` no toque filas con `payout_status != UNPROCESSED`.
3. Pago idempotente por request: una única `payout_transaction_hash` persistida *antes* de anunciar, y reintentos
   sólo si esa tx no existe en la cadena (reconciliación por hash, no por estado del nodo).

---

## 8. Limitaciones / lo que no se pudo cerrar

1. **Bridge mainnet**: sin repo de despliegue ni contrato wrapped en la org, no se puede mapear el escrow
   mainnet (si existe). Se midió lo accesible: sólo testnet.
2. **Saldos del bridge**: el endpoint `/metrics` (que expone `bridge_balance`) devuelve **403** desde esta sesión.
3. No se clonaron `trezor-firmware` (>1 GB, fork de terceros) ni los repos de UI; su SHA queda registrado.
4. Todos los datos on‑chain se tomaron de un gateway público mainnet (`xym776.allnodes.me:3001`,
   `restVersion 2.5.1`) y de `nodewatch.symbol.tools`; no se usó explorer para *interpretar* bytecode.
5. `client/catapult` es árbol de fuentes: no se compiló el nodo ni se ejecutó un fork de mainnet; el análisis
   de consenso es estático sobre el código del commit `cdfc513891e8`, contrastado con `/network/properties` live.

---

## 9. Reproducción (comandos usados)

```bash
# 0) clones
git clone --depth 1 https://github.com/symbol/product        /home/user/audit/product
git clone --depth 1 https://github.com/symbol/symbol-bootstrap /home/user/audit/symbol-bootstrap
git clone --depth 1 https://github.com/symbol/statistics-service /home/user/audit/statistics-service

# 1) estado live
curl -s https://xym776.allnodes.me:3001/network/properties        # forkHeights + plugin params
curl -s https://nodewatch.symbol.tools/api/symbol/height          # 5936121 / 5936100
curl -s https://xym776.allnodes.me:3001/mosaics/6BED913FA20223F8  # supply 8570172810049058
curl -s https://xym776.allnodes.me:3001/accounts/NAVORTEX3IPBAUWQBBI3I3BDIOS4AVHPZLCFC7Y
curl -s https://xym776.allnodes.me:3001/accounts/NCVORTEX4XD5IQASZQEHDWUXT33XBOTBMKFDCLI

# 2) estado del bridge (mainnet vs testnet)
curl -s -o /dev/null -w '%{http_code}\n' https://bridge.symbol.tools/ethereum-wrapped/unwrap/requests
curl -s https://bridge.symbol.tools/testnet/ethereum-wrapped/  | head -c 400
curl -s https://bridge.symbol.tools/testnet/ethereum-native/   | head -c 400

# 3) PoC (parser real del clon)
python3 -m venv /tmp/venv && . /tmp/venv/bin/activate
pip install symbol-sdk-python==3.3.3 web3==8.0.0
PYTHONPATH=/home/user/audit/product/bridge python3 audit/poc/bridge_approve_poc.py /home/user/audit/product/bridge
PYTHONPATH=/home/user/audit/product/bridge python3 audit/poc/bridge_crash_replay_poc.py /home/user/audit/product/bridge

# 4) código relevante del nodo
sed -n '25,80p' client/catapult/plugins/txes/aggregate/src/validators/AggregateTransactionsHashValidator.cpp
sed -n '140,160p' client/catapult/plugins/txes/aggregate/src/plugins/AggregateTransactionPlugin.cpp
sed -n '1,60p'  client/catapult/plugins/txes/lock_shared/src/observers/LockStatusAccountBalanceObserver.h
sed -n '25,60p' client/catapult/plugins/txes/mosaic/src/validators/ActiveMosaicView.cpp
sed -n '160,235p' client/catapult/src/catapult/model/NotificationPublisher.cpp   # fee debit last
sed -n '45,90p'  client/catapult/src/catapult/chain/BatchEntityProcessor.cpp       # validate+observe intercalado
sed -n '85,105p' client/catapult/src/catapult/state/AccountBalances.cpp           # debit lanza si falta saldo
```
