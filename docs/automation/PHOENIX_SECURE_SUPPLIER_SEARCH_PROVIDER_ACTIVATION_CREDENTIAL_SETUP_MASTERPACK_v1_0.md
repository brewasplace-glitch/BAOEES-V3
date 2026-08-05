# Phoenix Secure Supplier Search Provider Activation & Credential Setup Masterpack v1.0

Activeert Brave Search API als primaire supplier-discovery provider. De API-key wordt niet in Git, Phoenix-configuratie, documentatie of logs opgeslagen. De installer vraagt de key via een verborgen PowerShell SecureString-prompt en schrijft hem uitsluitend als Windows User Environment Variable `PHOENIX_BRAVE_SEARCH_API_KEY`.

Voor repositorywijzigingen wordt een echte HTTPS smoke test uitgevoerd. Daarna volgen dedicated tests, volledige Phoenix-regressies, graph-cleanup, secret-leak scan, git diff/check, commit en push.

Serper blijft uitgeschakeld als optionele fallback. Automatisch bestellen/betalen en automatische professionele goedkeuring blijven uitgeschakeld. Production release blijft LOCKED.

Opmerking: een Windows User Environment Variable voorkomt repository-lekkage maar is geen hardware-backed secret vault. Deze v1.0 volgt bewust het bestaande Phoenix provider-contract.
