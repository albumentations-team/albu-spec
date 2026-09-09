# albu-spec CLA Archive Manifest

This directory preserves the exact agreement texts needed to interpret CLA
acceptance records. The SHA-256 digest identifies the accepted text.

| CLA text | Source or document date | Archive file | SHA-256 of CLA bytes |
|---|---|---|---|
| Version 1 initial | commit `eb00f754790c04e85ac0e1f8ce8ac338e393c36d`, 2026-01-21 | `CLA-v1-eb00f75.md` | `126fa969d9961f7417bbdb749280b041adcc299bcc3f3d4887794da858282c51` |
| Version 2.0 | document dated 2026-09-09 | `CLA-v2.0-2026-09-09.md` | `7951d80788a1bae3abd89473f2a959fc27300838bd93265de57d3897113247b2` |

CLA Assistant Version 2.0 uses the public Gist
<https://gist.github.com/ternaus/e6e90220438d04c0023cb80658cb8823>,
immutable revision `8af30991a0c8eddc57ca9b4ab7907183992aaa08`, created
`2026-09-09T14:16:35Z`. The hosted `CLA.md` is 15,142 bytes with SHA-256
`7951d80788a1bae3abd89473f2a959fc27300838bd93265de57d3897113247b2`.
The hosted `metadata` file is 609 bytes with SHA-256
`12128a19faaa944ba2078943380abbc37541cd16d14a3fb3d08bc1af97a685b6`.

The previous GitHub Action stored its Version 1 acceptance record in
`signatures/version1/cla.json`. Commit
`d1a5f4b07c1b15d7f307da17780713dd8c8a2871` preserves that 221-byte record
with SHA-256
`d4a80da716ed0e12d8de160868353a60f40c49980718b63e29212f31c4007185`.
A Version 1 acceptance does not accept Version 2.0.

Acceptance records are not committed in the current tree because they may
contain personal or company information. The record system must retain the
accepting identity, timestamp, individual-versus-entity path, covered
identities for an Entity Acceptance, CLA version, and the SHA-256 identifier
from this manifest.

Changing `CLA.md` requires a new version, a new immutable archive file, a new
manifest entry, and explicit acceptance of that version. Never overwrite an
archived CLA file or reinterpret an old acceptance as consent to a later text.
