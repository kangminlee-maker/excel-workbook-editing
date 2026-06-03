# OAuth Client Binding Check

Status: `pending_console_evidence`

The active broker audience must be the Chrome App OAuth client id bound to the
fixed managed extension id.

## Fixed Extension Id

```text
jahlkdjaokmjbipfhlhnjggcgjmpeiij
```

## Active Candidate Client Id

```text
862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com
```

## Required Evidence

- Google Cloud OAuth client type is Chrome App.
- OAuth client Application ID equals
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
- Extension manifest `oauth2.client_id` equals the same OAuth client id.
- Cloud Run `BROKER_AUDIENCE` equals the same OAuth client id.
- A token obtained by the installed extension validates against the broker
  audience.

If any value differs, update the extension package or Cloud Run broker audience
before pilot expansion.
