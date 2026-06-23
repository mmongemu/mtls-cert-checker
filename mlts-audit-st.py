import os
import requests
import pandas as pd
import streamlit as st
from akamai.edgegrid import EdgeGridAuth, EdgeRc

# ==============================================================================
# UI SETUP
# ==============================================================================
st.set_page_config(page_title="Akamai mTLS Auditor", page_icon="🔒", layout="wide")
st.title("🔒 Akamai mTLS Certificate Auditor")
st.markdown("Automatically discover contracts and audit mTLS certificate deployments across an Akamai account.")

# ==============================================================================
# CORE FUNCTIONS
# ==============================================================================
@st.cache_resource
def init_akamai_session():
    """Initializes and caches the Akamai API session."""
    try:
        edgerc = EdgeRc(os.path.expanduser("~/.edgerc"))
        section = "default"
        baseurl = f"https://{edgerc.get(section, 'host')}"
        
        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(edgerc, section)
        return session, baseurl, None
    except Exception as e:
        return None, None, str(e)

def get_all_contracts(session, baseurl, ask):
    """Fetches all available contracts for the account via PAPI."""
    contract_ids = []
    url = f"{baseurl}/papi/v1/contracts"
    params = {"accountSwitchKey": ask} if ask else {}
    headers = {"Accept": "application/json"}
    
    response = session.get(url, headers=headers, params=params)
    if response.status_code == 200:
        items = response.json().get("contracts", {}).get("items", [])
        for item in items:
            c_id = item.get("contractId")
            if c_id:
                if c_id.startswith("ctr_"):
                    c_id = c_id[4:]
                contract_ids.append(c_id)
        return contract_ids, None
    else:
        return [], f"PAPI Error {response.status_code}: {response.text}"

def get_trust_set_mapping(session, baseurl, ask):
    """Fetches dictionary mapping numeric CA Set IDs to names."""
    mapping = {}
    url = f"{baseurl}/mtls-edge-truststore/v2/ca-sets"
    params = {"accountSwitchKey": ask} if ask else {}
    headers = {"Accept": "application/json"}
    
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
    return mapping

# ==============================================================================
# MAIN APP EXECUTION
# ==============================================================================
with st.form("audit_form"):
    account_switch_key = st.text_input("Account Switch Key", placeholder="e.g., 1-9197C", help="Enter the specific Akamai account ID to audit.")
    submit_button = st.form_submit_button("Run Global Audit")

if submit_button:
    if not account_switch_key.strip():
        st.warning("⚠️ Please enter an Account Switch Key before running the audit.")
    else:
        ask = account_switch_key.strip()
        
        session, baseurl, error = init_akamai_session()
        if error:
            st.error(f"❌ Failed to load `.edgerc` credentials: {error}")
            st.stop()

        audit_results = []
        
        with st.status("Initializing Audit...", expanded=True) as status:
            
            status.update(label="Discovering contracts...", state="running")
            contracts, papi_error = get_all_contracts(session, baseurl, ask)
            
            if papi_error:
                status.update(label="Error fetching contracts", state="error")
                st.error(papi_error)
                st.stop()
            if not contracts:
                status.update(label="No contracts found", state="error")
                st.warning("No active contracts found for this account.")
                st.stop()
                
            st.write(f"✅ Found {len(contracts)} contracts.")

            status.update(label="Loading Trust Set dictionary...")
            trust_set_names = get_trust_set_mapping(session, baseurl, ask)
            st.write(f"✅ Loaded {len(trust_set_names)} Trust Set definitions.")

            progress_bar = st.progress(0)
            
            for index, contract_id in enumerate(contracts):
                status.update(label=f"Scanning Contract: {contract_id} ({index + 1}/{len(contracts)})")
                
                enrollments_url = f"{baseurl}/cps/v2/enrollments"
                params = {"contractId": contract_id, "accountSwitchKey": ask}
                headers = {"Accept": "application/vnd.akamai.cps.enrollments.v11+json"}
                
                try:
                    response = session.get(enrollments_url, headers=headers, params=params)
                    if response.status_code != 200:
                        continue
                        
                    enrollments = response.json().get("enrollments", [])
                    
                    for enrollment in enrollments:
                        net_config = enrollment.get("networkConfiguration", {})
                        mtls_config = net_config.get("clientMutualAuthentication")
                        
                        if mtls_config is not None:
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
                                except:
                                    pass
                                    
                            display_name = trust_set_names.get(trust_set_id, trust_set_id)
                            
                            audit_results.append({
                                "Contract": contract_id,
                                "Slot Number": slot_number,
                                "Common Name": common_name,
                                "mTLS Status": "ENABLED",
                                "Trust Set": display_name
                            })
                except Exception as e:
                    pass 
                    
                progress_bar.progress((index + 1) / len(contracts))

            status.update(label="Audit Complete!", state="complete")

        if audit_results:
            df = pd.DataFrame(audit_results)
            st.success(f"🎉 Audit finished successfully! Found {len(df)} mTLS certificates.")
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name=f"akamai_mtls_audit_{ask}.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.info("The audit completed successfully, but no certificates with mTLS enabled were found.")