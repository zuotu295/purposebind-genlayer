# Validation

Verified on 2026-10-29 against Stable Studionet RPC `https://studio.genlayer.com/api`, chain 61999. GenLayerJS 1.1.8 and viem 2.57.8 were tested with the stable preset. Stable receipt fields `result_name` and leader `execution_result` are normalized by the scripts; the network's deployment source matched the exact pinned contract bytes.

Contract: `0x70e939Ee73425fd58dcc243Fd3034C96B93b6722`.

Source SHA-256: `6ce6001094a05fa81d865cf343c2c503805176868cd60d3921ffcc1a2ff211cb`.

## Local checks

- 18 mocked-host tests passed. They execute the actual deployable source; one test compares all 64 binary 3×2 matrices against an independent combinations/set-union oracle.
- Official `genvm-lint check`: lint passed (3 checks), validation passed, five methods (three writes, two views). Generated ABI is `schema.json`.
- Pinned SDK Direct Mode: storage, calldata serialization, independently rerun validator acceptance, validator disagreement and recipient claim passed with mocked LLM responses. This runs native Python with real SDK/storage, not Wasm or live consensus.
- Python 3.12.14, genvm-linter 0.11.0, genlayer-test 0.29.2, genlayer-py 0.16.3. The exact `py-genlayer` dependency is in the contract header. The newer-runner advisory was not treated as proof of stable compatibility; actual deployment and execution establish this pinned source's observed compatibility.

## Real network execution

All five transactions reached FINALIZED with MAJORITY_AGREE, `leader_only:false` and zero gas limit. The intentionally rejected claim has ERROR and rollback `NOT_MINIMUM_COVER`; the other four have successful leader execution.

| Action | Transaction hash | Result |
|---|---|---|
| Deploy | `0x38c7267803878c51d1841ec087f74f8ae81203cbefaf6afeb68c667bc6c09a7d` | Source matched |
| Register | `0xdf7070550ab77b6d33b12464bcfcd65b598aa7705648fe6aa38036dc03ff2ec0` | Immutable catalog recorded |
| Assess | `0x927a77827c3aae4f030b202c8c55da331c49e1713547b78515977962d9ee7b58` | Six coverage cells accepted |
| Reject extra fields | `0xae5fad26a7645df642803a18d881f787ed45a08fa3a6c6ef25787d7a413d4bc3` | Reverted; READY unchanged |
| Claim minimum | `0x7e8ed849d84c0da9659a96f99302ca4a931d7da345255ffd506aee86648b9da7` | CLAIMED |

Consensus coverage was YES/YES for `city_weekly_totals`, NO/NO for `visitor_emails`, NO/NO for `staff_birthdays`. The only offered and selected set was `["city_weekly_totals"]`. The assessment recorded three agree votes and two idle votes, with no rotation. Idle is not counted as an independent acceptance.

The read-only verifier fetched receipts again, decoded exact method/arguments from binary calldata, checked signer and destination, verified full-consensus mode and deployed source, and compared the complete finalized chain record against the saved record. The JSON evidence contains a projection of receipt fields; timing logs, node configurations and redundant byte arrays are omitted. Each hash can retrieve the complete public RPC response.

Two dedicated test wallets were controlled by one operator. The metadata and purpose are synthetic public-library examples. This demonstrates distinct-address enforcement, not independent institutions, real personal data handling or an actual data release. No user wallet key was requested, and no user funds or paid API were used.

## Unobserved behavior

REVIEW, UNSATISFIABLE, tied minimum covers, ownership rejection, digest mismatch and replay rejection are local test coverage only. They were not all exercised on chain. No browser-wallet signing, production data connector, dataset authenticity test or legal/privacy review was performed. Consensus verifies a bounded semantic matrix and can still be wrong. A successful demonstration does not prove general model accuracy.

Official references:

- https://docs.genlayer.com/developers/networks
- https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- https://docs.genlayer.com/api-references/genlayer-js/contracts
