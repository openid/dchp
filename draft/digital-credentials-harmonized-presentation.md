%%%
title = "Digital Credentials Harmonized Presentation - Editor's Copy"
abbrev = "dchp"
ipr = "none"
workgroup = "Digital Credentials Harmonized Presentation"
keyword = ["digital credentials", "mdoc", "sd-jwt vc", "presentation", "iso"]

# NOTE: this [seriesInfo] block is IETF Internet-Draft scaffolding needed by the
# markdown2rfc (mmark/xml2rfc) HTML toolchain; it is NOT a claim that this is an
# IETF document. mmark 2.2.31 hard-codes <rfc submissionType="IETF"> and does not
# propagate the stream, so a non-IETF stream (e.g. "independent") makes xml2rfc
# fail with a stream/submissionType mismatch. We therefore leave "stream" unset
# rather than assert a false "IETF" stream; mmark only warns ("Empty 'stream'")
# and the HTML still builds. The real publication reference for this OpenID/ISO
# joint document is a WG/SDO decision -- see issue 13.
[seriesInfo]
name = "Internet-Draft"
value = "digital-credentials-harmonized-presentation"
status = "standard"

[[author]]
initials = "TBD"
surname = "Editor"
fullname = "TBD Editor"
organization = "OpenID Foundation"
  [author.address]
  email = "openid-specs-dchp@lists.openid.net"

%%%

.# Abstract

This document specifies a harmonized protocol for the presentation of digital
credentials, bringing together the credential presentation approaches of
ISO/IEC 18013-5 and OpenID for Verifiable Presentations across multiple
credential formats, including ISO mdoc and IETF SD-JWT VC.

.# Foreword

This specification has been jointly developed by members of ISO/IEC JTC 1/SC 17
WG 10 and members of the OpenID Foundation Digital Credentials Protocols (DCP)
Working Group, under the OpenID Foundation's Digital Credentials Harmonized
Presentation (DCHP) Working Group.

This is an Editor's Copy. It is a work in progress and is subject to change
at any time.

.# Introduction

ISO/IEC 18013-5 (Device Request / Device Response) and OpenID for Verifiable
Presentations (Authorization Request / Authorization Response) take different
approaches to credential presentation. This document defines a harmonized
digital credentials request protocol that brings these together, supporting both
in-person and online presentation and the coexistence of multiple credential
formats, including ISO mdoc and IETF SD-JWT VC.

The objective is to enable interoperability among the parties involved in the
presentation of digital credentials while allowing existing deployments to
continue to operate.

> Development of this specification started with an initial starting contribution. This initial contribution was accepted as a starting point, but it doesn't yet constitute consensus on its full content. Each section will therefore have a note at the start of that section to track whether the DCHP working group considers that section to have consensus. There is a linked issue for each section to track this.

{mainmatter}

# Scope

To be completed.

# Normative references

The following documents are referred to in the text in such a way that some or
all of their content constitutes requirements of this document.

To be completed.

# Terms and definitions

For the purposes of this document, the following terms and definitions apply.

ISO and IEC maintain terminology databases for use in standardization at the
following addresses:

* ISO Online browsing platform: available at <https://www.iso.org/obp>
* IEC Electropedia: available at <https://www.electropedia.org/>

To be completed.

# Symbols and abbreviated terms

To be completed.
# Credential Request
> This section does not yet have working group consensus, which is tracked in [issue #24](https://github.com/openid/dchp/issues/24).

The request is sent by the **verifier** (reader) to the **wallet** (holder).

## Request Structure

The top-level `CredentialRequest` contains:

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `payload` | `1` | `bytes` | M | CBOR-encoded `RequestPayload` |
| `reader_auth` | `2` | `COSE_Sign` | O | Optional reader authentication signature |

The `RequestPayload` contains:

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `ScenarioSets` | `1` | `{ + ScenarioRef => ScenarioSet }` | M | Map of scenarios the reader is requesting, keyed by `ScenarioRef` |
| `CredentialQueries` | `2` | `{ + CredentialRef => CredentialQuery }` | M | Dictionary of all requested credential definitions |
| `encryption_context` | `3` | `EncryptionContext` | C | Primary response encryption context; absent when ISO/IEC 18013-5 session encryption is used |
| `additional_encryption_contexts` | `4` | `{ + int => EncryptionContext }` | O | Additional encryption contexts for multi-key routing, keyed by integer |

## Scenario Sets

A **ScenarioSet** represents an overarching purpose or business context (e.g., "Age Verification", "Identity Check"). It references the credential definitions via `CredentialRef` and defines the valid combinations a wallet can use to satisfy the scenario. `ScenarioSet`s are carried as a map in `RequestPayload`, keyed directly by `ScenarioRef`, so the `scenario_ref` field is the map key rather than an item inside the structure.

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `mandatory` | `1` | `bool` | M | Whether satisfying this scenario is required |
| `combinations` | `2` | `[ + CredentialCombination ]` | M | Valid credential combinations (logical **OR** between array items) |
| `purpose_id` | `3` | `[ controller_id: tstr, + int ]` | M | Namespaced identifier defining the purpose of the scenario |
| `extensions` | `4` | `{ * int / tstr => any }` | O | Extensions; `int` keys are RFU, `tstr` keys are application-specific |

- A `CredentialCombination` is an array of `CredentialRef` values — all referenced credentials must be presented (logical **AND**).
- The wallet need only satisfy **one** combination per ScenarioSet (logical **OR** across combinations).

## Credential Queries

A `CredentialQuery` defines the exact credential requirements for a single credential type.

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `credential_format` | `1` | `tstr` | M | Format identifier (e.g., `"mso_mdoc"`, `"vc+sd-jwt"`) |
| `credential_type` | `2` | `tstr` | M | Credential type (e.g., `"org.iso.18013.5.1.mDL"`) |
| `elements_dict` | `3` | `{ + ElementRef => DataElementDef }` | M | Dictionary of requested data elements |
| `requested_elements` | `4` | `ElementLogic` | M | Boolean logic tree defining which elements are required |
| `general_extensions` | `5` | `generalExtensions` | O | Protocol-level extensions applicable across formats |
| `format_extensions` | `6` | `formatExtensions` | O | Format-specific extensions (e.g., `mdocExtensions`, `sdjwtExtensions`) |
| `encryption_ref` | `7` | `int` | O | Reference to an entry in `additional_encryption_contexts`; absent means the main `encryption_context` is used |

### General Extensions

| Field | Key | Type | Description |
|---|---|---|---|
| `issuer_identifiers` | `1` | `IssuerIdentifiers` | Acceptable credential issuers (e.g., X.509 certificate references) |
| `allow_multiple` | `2` | `bool` | Allow returning multiple credentials of the same type |
| `credential_auth_data` | `3` | `{ + int / tstr => any }` | Data to be authenticated/signed by the credential presentation |
| `support_no_cryptographic_binding` | `4` | `bool` | Indicates if the reader accepts responses without cryptographic binding |

### Format-Specific Extensions

**`mdocExtensions`:**

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `issuer_alg_values` | `1` | `[ + int ]` | O | Acceptable issuer signature algorithm identifiers |
| `device_alg_values` | `2` | `[ + int ]` | O | Acceptable device signature algorithm identifiers |

> **Note:** A verifier that has no constraint on one of the two algorithm classes should include the field with a permissive list of acceptable values rather than omitting it.

**`sdjwtExtensions`:**

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `sd-jwt_alg_values` | `1` | `[ + tstr ]` | O | Acceptable SD-JWT algorithm values |
| `kb-jwt_alg_values` | `2` | `[ + tstr ]` | O | Acceptable Key Binding JWT algorithm values |

### Issuer Identifiers

| Field | Key | Type | Description |
|---|---|---|---|
| `x509_ref` | `1` | `[ + bstr ]` | Array of authoritykeyidentifiers|

## Data Elements & Logic

### DataElementDef

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `path` | `1` | `[ + tstr ]` | M | Path to the element. For mdocs: `[namespace, identifier]` |
| `value_match` | `2` | `any` | O | Expected value for matching/filtering |
| `intent_to_retain` | `3` | `bool` | M | Indicates if the verifier intends to store this element |

### ElementLogic — Conjunctive Normal Form

The `requested_elements` field uses a three-level structure:

```
ElementLogic  = [ + OrGroup ]   ; Level 1 — AND: ALL OrGroups must be satisfied
OrGroup       = [ + AndGroup ]  ; Level 2 — OR:  AT LEAST ONE AndGroup must be satisfied
AndGroup      = [ + ElementRef ] ; Level 3 — AND: ALL referenced elements must be provided
```

This enables expressing complex requirements such as:

> *[Family Name] AND ( [Age Over 18] OR [Birth Date] )*

> *[Street address] AND ( [Full name] OR ( [Given name] AND [Family name] ) )*


# Response Encryption

> This section does not yet have working group consensus, which is tracked in [issue #25](https://github.com/openid/dchp/issues/25).

The protocol provides **application-layer response encryption** via `EncryptionContext` (in the request) and the `encrypted` array (in the response). Usage depends on the underlying transport.

| Transport type | Encryption requirement |
|---|---|
| No session-layer encryption (e.g., DC API, scheme-based) | **Mandatory** — protocol-level response encryption must be used |
| Session encryption present (e.g., ISO/IEC 18013-5 BLE/NFC) | **Not applicable** — protocol-level encryption may be omitted |

## Multi-Key Routing

The request defines a primary `encryption_context` and optionally additional contexts in `additional_encryption_contexts`, keyed by integer. Each `CredentialQuery` may carry an optional `encryption_ref` pointing to one of the additional contexts by integer key. If `encryption_ref` is absent the credential uses the primary `encryption_context`. If `encryption_context` is also absent (BLE/NFC session encryption), the credential is unencrypted at the application layer. This allows a wallet to encrypt an "Identity" credential for one backend and a "Payment" credential for a different backend within the same response payload.

## EncryptionContext

| Field | Key | Type | Description |
|---|---|---|---|
| `key` | `1` | `COSE_Key` | The reader's public key (e.g., HPKE key) |
| `nonce` | `2` | `bstr` | Nonce value |
| `algorithms` | `3` | `[ + int ]` | Supported COSE algorithm identifiers (e.g., HPKE ciphersuites) |

## Algorithm

For non-post-quantum-cryptography (non-PQC) operations, **HPKE** is mandated, potentially based on [draft-ietf-cose-hpke](https://datatracker.ietf.org/doc/draft-ietf-cose-hpke/).


# Reader Authentication

> This section does not yet have working group consensus, which is tracked in [issue #26](https://github.com/openid/dchp/issues/26).

The verifier can optionally authenticate itself using the `reader_auth` field in the top-level `CredentialRequest`.

- **Structure:** Uses a standard `COSE_Sign` structure.
- **Payload:** The signature uses a **detached payload**.
- **Detached payload content:** The raw CBOR-encoded `RequestPayload` together with the **transaction transcript**.


# Transaction Transcript

> This section does not yet have working group consensus, which is tracked in [issue #27](https://github.com/openid/dchp/issues/27).

The transaction transcript provides a cryptographic context binding across all protocol operations, ensuring that messages from one session cannot be replayed in another, and that the verifier and wallet are bound to the same channel and request.

Because deterministic CBOR encoding (RFC 8949 §4.2) is required throughout this protocol, the transcript is defined as a **CBOR map** rather than a fixed-order array. Deterministic CBOR guarantees a unique canonical byte encoding for any given map value, making it safe to hash or sign over without ambiguity. This is the key difference from the ISO/IEC 18013-5 `SessionTranscript` array, which used a fixed order precisely to achieve the same determinism property.

Two transcript types are defined:

- **`ReaderTransactionTranscript`** — constructed by the **verifier** and used in reader authentication and response encryption.
- **`WalletTransactionTranscript`** — constructed by the **wallet** for credential authentication. It includes the applicable encryption context reference for the credential being presented, or no encryption context if the credential is unencrypted.

Both share the same base fields; they differ in whether an encryption context reference is present.

## ReaderTransactionTranscript

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `request_hash` | `1` | `bstr` | M | SHA-256 of the CBOR-encoded `RequestPayload` bytes |
| `channel_binding` | `2` | `ChannelBinding` | M | Transport- and engagement-specific binding; see §5.3 |

## WalletTransactionTranscript

| Field | Key | Type | Presence | Description |
|---|---|---|---|---|
| `request_hash` | `1` | `bstr` | M | SHA-256 of the CBOR-encoded `RequestPayload` bytes — identical value to the reader transcript |
| `channel_binding` | `2` | `ChannelBinding` | M | Identical to the reader transcript |
| `encryption_context` | `3` | `int` | O | The `encryption_ref` value from the `CredentialQuery` for this credential; absent when no application-layer encryption is used |

The wallet determines the applicable value from `CredentialQuery.encryption_ref`: if present, it is copied directly into this field; if absent, the field is omitted (indicating the main `encryption_context` is used or no application-layer encryption applies).

## Channel Binding

`ChannelBinding` is a CBOR map capturing the engagement and transmission channel used to initiate the session. The fields present depend on the transport. At most one engagement field and at most one transmission field will be present for any given session.

### Engagement fields

These fields capture how the credential request was initiated (device engagement in 18013-5 terminology, or equivalent invocation context in OpenID4VP / 18013-7):

| Field | Key | Type | Transport / Protocol | Description |
|---|---|---|---|---|
| `qr_device_engagement` | `1` | `bstr` | 18013-5 QR | CBOR-encoded `DeviceEngagement` structure from QR code engagement |
| `reverse_qr_device_engagement` | `2` | `bstr` | 18013-5 Reverse QR | CBOR-encoded `ReaderEngagement` structure from reverse QR engagement |
| `nfc_static_handover_engagement` | `3` | `bstr` | 18013-5 NFC static | Handover select message from NFC static handover |
| `nfc_negotiated_handover_engagement` | `4` | `bstr` | 18013-5 NFC negotiated | Handover select and response message from NFC negotiated handover |
| `nfcv2_handover` | `5` | `bstr` | CBOR-encoded `DeviceEngagement` and `ReaderEngagement` structures from NFCv2 handover |
| `oidc4vp_request_uri` | `6` | `tstr` | OID4VP | The `request_uri` value from the OID4VP authorisation request |
| `oidc4vp_client_id` | `7` | `tstr` | OID4VP | The `client_id` from the OID4VP authorisation request |
| `dc_api_origin` | `8` | `tstr` | DC API | Web origin (`scheme://host[:port]`) of the page invoking the Digital Credentials API |

### Transmission fields

These fields capture the data-transport channel over which the credential presentation is being performed:

| Field | Key | Type | Transport / Protocol | Description |
|---|---|---|---|---|
| `ble_gatt` | `10` | `bstr` | 18013-5 BLE GATT | BLE UUID |
| `ble_l2cap` | `11` | `uint` | 18013-5 BLE L2CAP | L2CAP PSM value |


## Use in Protocol Operations

| Operation | Transcript used | How it is bound |
|---|---|---|
| **Reader authentication** | `ReaderTransactionTranscript` | Combined with the `RequestPayload` bytes as the detached COSE_Sign payload |
| **Response encryption** | `WalletTransactionTranscript` for that credential | Supplied as info parameter for HPKE |
| **mdoc device authentication** | `WalletTransactionTranscript` for that credential | Embedded in a derived `SessionTranscript`; see §5.5 |
| **SD-JWT Key Binding JWT** | `WalletTransactionTranscript` for that credential | SHA-256 of the CBOR-encoded transcript used as the `nonce` claim in the KB-JWT |
| **Session key derivation** (BLE/NFC) | `WalletTransactionTranscript` (no encryption context) | Used as an input to the session key derivation function |


# Credential Response

> This section does not yet have working group consensus, which is tracked in [issue #28](https://github.com/openid/dchp/issues/28).

The `CredentialResponse` contains any combination of an optional unencrypted envelope and zero or more encrypted envelopes. Both fields are optional; at least one should be present in a well-formed response. Each envelope is **self-contained**: it holds its own credential pool and its own scenario map. A credential that must appear in multiple envelopes is duplicated across them; no cross-envelope references exist.

| Field | Key | Type | Description |
|---|---|---|---|
| `unencrypted` | `1` | `Envelope` | Plaintext envelope |
| `encrypted` | `2` | `[ + COSE_Encrypt ]` | Each item decrypts to `bytes .cbor Envelope` |

## Envelope Structure

An `Envelope` contains a credential pool and a scenario map:

| Field | Key | Type | Description |
|---|---|---|---|
| `credentials` | `1` | `{ + CredentialRef => CredentialItem }` | Pool of all credentials returned in this envelope, keyed by `CredentialRef` (the same integer identifiers used in the request's `CredentialQueries`) |
| `scenarios` | `2` | `{ + ScenarioRef => [ + CredentialRef ] }` | Maps each satisfied `ScenarioRef` to the list of `CredentialRef`s from the pool that satisfy it |

The `CredentialRef` keys in the pool are the **same integers** used in the request's `CredentialQueries` map, so the verifier can directly correlate a returned credential to the query that requested it without any additional mapping.

Each `CredentialItem`:

| Field | Key | Type | Description |
|---|---|---|---|
| `format` | `1` | `tstr` | The format of the returned credential |
| `data` | `2` | `Document / ZkDocument / SdJwtData` | The credential data payload |

## Credential Data Types

| Type | Encoding | Description |
|---|---|---|
| `Document` | `bstr` | Standard mdoc presentation (aligns with ISO/IEC 18013-5 `Document` structure) |
| `SdJwtData` | `tstr` | SD-JWT combined presentation string |



# CDDL Definitions

> CBOR data definitions use [CDDL (RFC 8610)](https://www.rfc-editor.org/rfc/rfc8610).  
> External references: `COSE_Sign`, `COSE_Key`, `COSE_Encrypt` are defined in [RFC 9052](https://www.rfc-editor.org/rfc/rfc9052).

## Request CDDL

```cddl
; ==========================================
; TOP-LEVEL REQUEST
; ==========================================

CredentialRequest = {
  payload:        1 => bstr,      ; CBOR-encoded RequestPayload
  ? reader_auth:  2 => COSE_Sign, ; Optional reader authentication (detached payload)
  * int => any                    ; RFU extensions
}

RequestPayload = {
  ScenarioSets:                     1 => { + ScenarioRef => ScenarioSet },
  CredentialQueries:                2 => { + CredentialRef => CredentialQuery },
  ? encryption_context:             3 => EncryptionContext,
  ? additional_encryption_contexts: 4 => { + int => EncryptionContext },
  * int => any                      ; RFU extensions
}

ScenarioRef   = int
CredentialRef = int

; ==========================================
; ENCRYPTION PARAMETERS
; ==========================================

EncryptionContext = {
  key:        1 => COSE_Key,
  nonce:      2 => bstr,
  algorithms: 3 => [ + int ],     ; COSE algorithm identifiers (e.g. HPKE ciphersuites)
  * int / tstr => any             ; RFU / application-specific extensions
}

; ==========================================
; SCENARIO SETS
; ==========================================

ScenarioSet = {
  mandatory:    1 => bool,
  combinations: 2 => [ + CredentialCombination ],
  purpose_id:   3 => [ controlled_id: tstr, + int ],
  ? extensions: 4 => { * int / tstr => any }, ; int = RFU, tstr = application-specific
  * int => any                    ; RFU extensions
}

CredentialCombination = [ + CredentialRef ]

; ==========================================
; CREDENTIAL QUERIES & EXTENSIONS
; ==========================================

CredentialQuery = {
  credential_format:    1 => tstr,
  credential_type:      2 => tstr,
  elements_dict:        3 => { + ElementRef => DataElementDef },
  requested_elements:   4 => ElementLogic,
  ? general_extensions: 5 => generalExtensions,
  ? format_extensions:  6 => formatExtensions,
  ? encryption_ref:     7 => int,   ; Key into additional_encryption_contexts; absent = use main
  * int => any                      ; RFU extensions
}

generalExtensions = {
  ? issuer_identifiers:               1 => IssuerIdentifiers,
  ? allow_multiple:                   2 => bool,
  ? credential_auth_data:             3 => { + int / tstr => any },
  ? support_no_cryptographic_binding: 4 => bool,
  * int / tstr => any             ; int = RFU, tstr = application-specific
}

formatExtensions = mdocExtensions / sdjwtExtensions / zkFormatExtensions

mdocExtensions = {
  ? issuer_alg_values: 1 => [ + int ],
  ? device_alg_values: 2 => [ + int ],
  * int / tstr => any             ; int = RFU, tstr = application-specific
}

sdjwtExtensions = {
  ? sd-jwt_alg_values: 1 => [ + tstr ],
  ? kb-jwt_alg_values: 2 => [ + tstr ],
  * int / tstr => any             ; int = RFU, tstr = application-specific
}

IssuerIdentifiers = {
  ? x509_ref: 1 => [ + bstr ],
  * int / tstr => [ + any ]       ; int = RFU, tstr = application-specific
}

; ==========================================
; DATA ELEMENTS & LOGIC
; ==========================================

ElementRef = int

DataElementDef = {
  path:               1 => [ + tstr ],
  ? value_match:      2 => any,
  intent_to_retain:   3 => bool,
  * int => any                    ; RFU extensions
}

; Conjunctive Normal Form (CNF): AND of OR of AND
ElementLogic = [ + OrGroup ]    ; Level 1 (AND): All OrGroups must be satisfied
OrGroup      = [ + AndGroup ]   ; Level 2 (OR):  At least one AndGroup must be satisfied
AndGroup     = [ + ElementRef ] ; Level 3 (AND): All referenced elements must be provided
```

## Response CDDL

```cddl
; ==========================================
; PRIMITIVE TYPE ALIASES
; ==========================================

; full-date is defined in RFC 8943 as CBOR tag 1004 applied to a text string (tstr).
full-date = #6.1004(tstr)

; ==========================================
; TOP-LEVEL RESPONSE
; ==========================================

CredentialResponse = {
  ? unencrypted:  1 => Envelope,
  ? encrypted:    2 => [ + COSE_Encrypt ], ; Each item decrypts to bytes .cbor Envelope
  * int => any                             ; RFU extensions
}

; Both unencrypted and encrypted envelopes share the same structure.
; Each envelope is self-contained: credentials that must appear in multiple
; envelopes are duplicated; no cross-envelope references are permitted.
Envelope = {
  credentials:    1 => { + CredentialRef => CredentialItem },
  scenarios:      2 => { + ScenarioRef   => [ + CredentialRef ] },
  * int => any                             ; RFU extensions
}

CredentialItem = {
  format:         1 => tstr,
  data:           2 => Document / ZkDocument / SdJwtData,
  * int => any                             ; RFU extensions
}

; ==========================================
; FORMAT-SPECIFIC DATA
; ==========================================

Document = bstr   ; ISO/IEC 18013-5 Document structure

NameSpace = tstr

SdJwtData = tstr   ; SD-JWT combined presentation string
```



*External type references: `COSE_Sign`, `COSE_Key`, `COSE_Encrypt` — defined in [RFC 9052](https://www.rfc-editor.org/rfc/rfc9052) (COSE); `COSE_X509` — defined in [RFC 9360](https://www.rfc-editor.org/rfc/rfc9360); `full-date` — defined in [RFC 8943](https://www.rfc-editor.org/rfc/rfc8943) (CBOR Tags for Date).*

## Transaction Transcript CDDL

```cddl
; ==========================================
; TRANSACTION TRANSCRIPTS
; Deterministic CBOR encoding (RFC 8949 §4.2) is REQUIRED for all transcript values.
; ==========================================

; Used by the verifier: for reader authentication and as info parameter for response encryption.
ReaderTransactionTranscript = {
  request_hash:    1 => bstr,          ; SHA-256 of CBOR-encoded RequestPayload bytes
  channel_binding: 2 => ChannelBinding,
  * int / tstr => any                  ; RFU / application-specific extensions
}

; Used by the wallet: for mdoc device authentication, SD-JWT KB-JWT nonce, and response encryption.
; Includes the encryption_ref from the CredentialQuery for the credential being presented.
WalletTransactionTranscript = {
  request_hash:         1 => bstr,          ; Same value as in ReaderTransactionTranscript
  channel_binding:      2 => ChannelBinding,
  ? encryption_context: 3 => int,           ; The encryption_ref from CredentialQuery;
                                            ; absent when no application-layer encryption is used
  * int / tstr => any                       ; RFU / application-specific extensions
}

; ==========================================
; CHANNEL BINDING
; At most one engagement field and at most one transmission field are present per session.
; ==========================================

ChannelBinding = {
  ; --- Engagement fields (keys 1–9) ---
  ; Capture how the credential request was initiated.
  ? qr_device_engagement:              1 => bstr,  ; 18013-5 QR:              CBOR-encoded DeviceEngagement
  ? reverse_qr_device_engagement:      2 => bstr,  ; 18013-5 Reverse QR:      CBOR-encoded DeviceEngagement
  ? nfc_static_handover_engagement:    3 => bstr,  ; 18013-5 NFC static:      CBOR-encoded DeviceEngagement
  ? nfc_negotiated_handover_engagement: 4 => bstr, ; 18013-5 NFC negotiated:  CBOR-encoded DeviceEngagement
  ? oidc4vp_request_uri:               5 => tstr,  ; OID4VP:                  request_uri from the authorisation request
  ? oidc4vp_client_id:                 6 => tstr,  ; OID4VP:                  client_id from the authorisation request
  ? dc_api_origin:                     7 => tstr,  ; DC API:                  web origin (scheme://host[:port])

  ; --- Transmission fields (keys 10–19) ---
  ; Capture the data-transport channel over which the presentation is performed.
  ? ble_uuid:                 10 => bstr,           ; 18013-5 BLE (UUID):      EReaderKey bytes
  ? ble_l2cap:                11 => {               ; 18013-5 BLE L2CAP:       EReaderKey + PSM
                                   uuid: 1 => bstr, ;   Reader ephemeral public key
                                   psm:  2 => uint  ;   L2CAP Protocol/Service Multiplexer value
                                 },
  ? nfc_static_handover:      12 => bstr,           ; 18013-5 NFC static:      CBOR-encoded NFCHandover
  ? nfc_negotiated_handover:  13 => bstr,           ; 18013-5 NFC negotiated:  CBOR-encoded NFCHandover
  ? nfcv2:                    14 => bstr,           ; NFC v2:                  NFC v2 transmission data
  ? wifi_aware:               15 => bstr,           ; 18013-5 WiFi Aware:      engagement data

  * int / tstr => any                               ; RFU / application-specific extensions
}

```

# Conventions

In this document, the following verbal forms are used:

* "shall" indicates a requirement;
* "should" indicates a recommendation;
* "may" indicates a permission;
* "can" indicates a possibility or a capability.

These verbal forms are used in accordance with ISO/IEC Directives, Part 2,
Clause 7 (see <https://www.iso.org/directives-and-policies.html>).

{backmatter}

# Bibliography

[1] ISO/IEC Directives, Part 2, *Principles and rules for the structure and
drafting of ISO and IEC documents*

# Acknowledgements {#Acknowledgements}

We would like to thank TBD for their
valuable feedback and contributions to this specification.

# Document History

   [[ To be removed from the final specification ]]

   -00

   * initial working draft
