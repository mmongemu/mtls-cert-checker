import sys
import os
import csv
import argparse
import requests
from akamai.edgegrid import EdgeGridAuth, EdgeRc

def setup_argparse():
    parser = argparse.ArgumentParser(description="Akamai mTLS Certificate Auditor")
    parser.add_argument("-a", "--ask", help="Account Switch Key (e.g., 1-9197C)", required=True)
    parser.add_argument("--csv", action="store_true", help="Enable CSV export of the audit results")
    parser.add_argument("-o", "--output", help="Directory path to save the CSV (defaults to current directory)", default=".")
    return parser.parse_args()

def init_akamai_session():
    try:
        edgerc = EdgeRc(os.path.expanduser("~/.edgerc"))
        section = "default"
        baseurl = f"https://{edgerc.get(section, 'host')}"
        
        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(edgerc, section)
        return session, baseurl
    except Exception as e:
        print(f"❌ Error loading .edgerc configuration: {e}")
        sys.exit(1)

def get_all_contracts(session, baseurl, ask):
    contract_ids = []
    url = f"{baseurl}/papi/v1/contracts"
    params = {"accountSwitchKey": ask}
    headers = {"Accept": "application/json"}
    
    try:
        response = session.get(url, headers=headers, params=params)
        if response.status_code == 200:
            items = response.json().get("contracts", {}).get("items", [])
            for item in items:
                c_id = item.get("contractId")
                if c_id:
                    if c_id.startswith("ctr_"):
                        c_id = c_id[4:]
                    contract_ids.append(c_id)
        else:
            print(f"⚠️ PAPI Blocked (Status {response.status_code}): {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"⚠️ Error reaching Property Manager API: {e}")
        sys.exit(1)
        
    return contract_ids

def get_trust_set_mapping(session, baseurl, ask):
    mapping = {}
    url = f"{baseurl}/mtls-edge-truststore/v2/ca-sets"
    params = {"accountSwitchKey": ask}
    headers = {"Accept": "application/json"}
    
    try:
        response = session.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            ca_sets = data.get("caSets", data) if isinstance(data, dict) else data
            if isinstance(ca_sets, list):
                for ca in ca_sets:
                    ca_id = str(ca.get("caSetId", ca.get("id")))
                    ca_name = ca.get("caSetName", ca.get("name", "Unknown Name"))
                    if ca_id != "None":
                        mapping[ca_id] = ca_name
        else:
            print(f"⚠️ Truststore API Error (Status {response.status_code})")
    except Exception as e:
        print(f"⚠️ Error reaching Truststore API: {e}")
        
    return mapping

def main():
    args = setup_argparse()
    ask = args.ask
    
    session, baseurl = init_akamai_session()
    
    print("🔄 Initializing Global Account Audit...\n")
    print("📥 Discovering contracts via Property Manager API...")
    contracts = get_all_contracts(session, baseurl, ask)
    print(f"   Found {len(contracts)} active contracts.\n")
    
    if not contracts:
        print("❌ No contracts to process. Exiting.")
        sys.exit(0)

    print("📥 Loading Trust Set names from the mTLS Edge Truststore API...")
    trust_set_names = get_trust_set_mapping(session, baseurl, ask)
    print(f"   Loaded {len(trust_set_names)} Trust Sets.\n")

    audit_results = []
    total_mtls_found = 0

    for contract_id in contracts:
        print(f"📂 Checking Contract: {contract_id}")
        print("-" * 80)
        print(f"{'Slot Number':<15} | {'Common Name':<35} | {'mTLS Status'}")
        print("-" * 80)

        enrollments_url = f"{baseurl}/cps/v2/enrollments"
        params = {"contractId": contract_id, "accountSwitchKey": ask}
        headers = {"Accept": "application/vnd.akamai.cps.enrollments.v11+json"}
        
        try:
            response = session.get(enrollments_url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"❌ Error fetching contract {contract_id}")
                print("=" * 80 + "\n")
                continue
                
            enrollments = response.json().get("enrollments", [])
            contract_mtls_count = 0

            for enrollment in enrollments:
                mtls_config = enrollment.get("networkConfiguration", {}).get("clientMutualAuthentication")
                
                if mtls_config is not None:
                    contract_mtls_count += 1
                    total_mtls_found += 1
                    
                    enrollment_id = enrollment.get("id", "Unknown")
                    slots = enrollment.get("assignedSlots", [])
                    slot_number = ", ".join(str(s) for s in slots) if slots else "Unassigned"
                    common_name = enrollment.get("csr", {}).get("cn", "Unknown CN")
                    trust_set_id = str(mtls_config.get("setId", "N/A"))
                    
                    if trust_set_id == "hidden":
                        d_url = f"{baseurl}/cps/v2/enrollments/{enrollment_id}"
                        d_headers = {"Accept": "application/vnd.akamai.cps.enrollment.v11+json"}
                        try:
                            d_resp = session.get(d_url, headers=d_headers, params={"accountSwitchKey": ask})
                            if d_resp.status_code == 200:
                                d_mtls = d_resp.json().get("networkConfiguration", {}).get("clientMutualAuthentication", {})
                                trust_set_id = str(d_mtls.get("setId", "N/A"))
                        except Exception:
                            pass
                            
                    display_name = trust_set_names.get(trust_set_id, trust_set_id)
                    
                    print(f"{slot_number:<15} | {common_name:<35} | ✅ ENABLED (Trust Set: {display_name})")
                    
                    audit_results.append({
                        "Contract ID": contract_id,
                        "Slot Number": slot_number,
                        "Common Name": common_name,
                        "mTLS Status": "ENABLED",
                        "Trust Set Name": display_name
                    })

            print("-" * 80)
            print(f"📋 Contract {contract_id} check complete. Found {contract_mtls_count} mTLS certificates.")
            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ An error occurred while processing contract {contract_id}: {e}")
            print("=" * 80 + "\n")

    print("🎉 Global Audit Finished.")
    print(f"📊 Total mutual TLS certificates found: {total_mtls_found}")
    
    if args.csv and audit_results:
        os.makedirs(args.output, exist_ok=True)
        file_path = os.path.join(args.output, f"mtls_audit_results_{ask}.csv")
        
        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=audit_results[0].keys())
                writer.writeheader()
                writer.writerows(audit_results)
            print(f"💾 CSV successfully saved to: {file_path}")
        except Exception as e:
            print(f"❌ Failed to save CSV file: {e}")

if __name__ == "__main__":
    main()