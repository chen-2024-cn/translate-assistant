# Security and privacy

## Credentials

- `config.py` reads translation credentials from environment variables. Do not embed real credentials in source code, screenshots, build logs, commits, or executable defaults.
- `.env.example` is documentation only; the application does not load `.env` automatically.
- User environment variables are not encrypted secret storage. Protect the Windows account; never publish their values.
- If a credential was exposed, revoke/rotate it with the provider. Deleting a file or rewriting a commit does not revoke the credential.

## Data sent to services

Translation text is sent to the configured external provider over HTTPS. With fallback enabled, a failed request may be sent to MyMemory. English word lookup can also send the word to Baidu's web dictionary endpoint. These services have their own terms, quotas, privacy policies and availability limits.

Disable selection translation and do not submit confidential text if your policy does not allow external translation. The application does not provide an offline translation guarantee.

Vocabulary and selection settings are stored locally under `%APPDATA%\TranslateAssistant`. Do not publish databases or verification artifacts; they may contain personal words or example text. The selection monitor temporarily uses the system clipboard; its text-based restoration does not guarantee preservation of every non-text clipboard format.

## Reporting issues

Do not put credentials or private data in public issues. If the repository has GitHub private vulnerability reporting enabled, use that channel. Otherwise contact the repository owner privately through an available channel before sharing sensitive details. No dedicated security inbox or response-time guarantee is currently provided.

## Distribution

Use trusted builds and verify published hashes. This project does not bypass Windows security checks. A build succeeding is not proof of compatibility with every Windows version, input method, terminal or security product.
