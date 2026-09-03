# Release status

## LohnMail 2.0.3 — build 2026.09.03.1

Status: verified for the main Windows update channel.

- Windows CI completed successfully with 132 tests passing.
- The update package was published through the production update endpoint.
- The published ZIP size and SHA-256 checksum were verified after downloading it back from the server.
- ZIP integrity verification completed without errors.
- A real update on Windows was completed successfully and confirmed on 3 September 2026.
- Existing settings, companies and local application data remained outside the replaced `App` directory.

Production manifest:
`https://license-server-lm.vercel.app/api/updates/windows/latest`
