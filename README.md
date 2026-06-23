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
```
---

## 🖥️ Method 1: Standalone CLI Tool (```mtls_audit.py```)

The CLI script is optimized for quick local runs, cron jobs, and CI/CD pipelines.

### Installation
Install the required Akamai EdgeGrid authentication library:

```ini
pip install edgegrid-python requests
```

### Usage
Execute the script via terminal. The Account Switch Key (--ask) parameter is strictly required.

```ini
python mtls_audit.py --ask <YOUR_ACCOUNT_SWITCH_KEY>
```

### Command Line Arguments

| Argument | Short Flag | Description | Required |
| :--- | :--- | :--- | :--- |
| `--ask` | `-a` | The Account Switch Key to audit (e.g., `1-9197C`). | **Yes** |
| `--csv` | `N/A` | Flag to generate a `.csv` file containing the audit results. | No |
| `--output` | `-o` | Directory path to save the CSV file. Defaults to current directory. | No |

### Execution Examples
- Run a standard terminal printout:

```ini
python mtls_audit.py -a 1-9197C
```

- Run an audit, create a CSV, and save it to a specific directory:
```ini
python mtls_audit.py -a 1-9197C --csv --output /Users/admin/akamai_reports/
```

## 🌐 Method 2: Streamlit UI App (```mlts-audit-st.py```)

The Streamlit version provides an interactive web-based interface. Users input their Account Switch Key into a text field, observe execution logs via real-time container states, and extract tabular logs straight into local storage using a native download element.

### Installation
In addition to the EdgeGrid library, the UI requires Streamlit and Pandas:

```ini
pip install edgegrid-python requests streamlit pandas
```

### Deployment Strategy

#### Option A: Running as a Standalone Application
If executing by itself, navigate to the script workspace directory and run:

```ini
streamlit run mlts-audit-st.py
```

#### Option B: Integrating into an Existing Multi-Page App Workspace

1. Locate the workspace project root.

2. Ensure a child directory named pages/ exists alongside your primary landing execution entrypoint script.

3. Save the UI source code directly inside that path (e.g., pages/1_mTLS_Auditor.py). Streamlit will automatically map and display it inside the global web menu sidebar interface.

---

## 🛠️ Troubleshooting Guide
- **Error 403 Forbidden on Trust Sets** (pep-authz/deny): Your active API token configuration profile lacks the explicit context scope requirements. Update your specific API Client token settings via the Identity Management dashboard within the Control Center, check the radio option for mTLS Edge Truststore, select Read-Only access, and save.

- **Error 410 Gone**: This error occurs if a legacy application tries to contact the deprecated Trust Chain Manager API resource path layout. This script avoids this problem by strictly utilizing the active v2 endpoint structure.
**
- **No Contracts Discovered**: Ensure the provided Account Switch Key string matches your exact tenant identifier. If validation checks pass but the issue persists, verify that your API credentials have explicit Read-Only permissions active for the Property Manager (PAPI) API.


