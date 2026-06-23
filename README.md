# 🔒 Akamai mTLS Certificate Auditor

An automated diagnostic tool designed to globally audit Mutual TLS (mTLS) configurations across an Akamai account. 

Instead of manually clicking through the Certificate Provisioning System (CPS) UI for every single contract, this tool dynamically discovers all active contracts via the Property Manager API (PAPI), queries the mTLS Edge Truststore for human-readable Trust Set names, and scans CPS to report exactly which certificates have mTLS enabled.

---

## ✨ Features

* **Dynamic Contract Discovery:** Automatically finds all active contracts associated with an Account Switch Key.
* **Intelligent Name Mapping:** Bypasses masked `"hidden"` values and meaningless numeric IDs to fetch the actual human-readable names of your mTLS Trust Sets.
* **Dual Execution Modes:** Available as a lightweight Command Line Interface (CLI) tool or an interactive Streamlit Web App.
* **CSV Export:** Cleanly packages the audit results into a structured CSV file for reporting and compliance tracking.

---

## 🔐 Prerequisites & API Setup

To use this tool, you must have an active Akamai API Client credential stored locally in an `~/.edgerc` file, and your credential must have the correct permissions.

### 1. Required API Permissions
Your API Client token in the Akamai Control Center must have **READ-ONLY** (or higher) access to the following three APIs:

1. **Certificate Provisioning System (CPS)** - Required to read the certificate details.
2. **Property Manager (PAPI)** - Required to fetch the list of active contracts.
3. **mTLS Edge Truststore** - Required to map the numeric IDs to actual Trust Set names. *(Note: If this is missing, the API will return a 403 Forbidden error and fail to load the names).*

### 2. The `.edgerc` File
Ensure your credentials are saved in your home directory (`~/.edgerc` on Mac/Linux, or `C:\Users\YourName\.edgerc` on Windows) under the `[default]` section:

```ini
[default]
client_secret = your_client_secret
host = your_host.luna.akamaiapis.net
access_token = your_access_token
client_token = your_client_token
