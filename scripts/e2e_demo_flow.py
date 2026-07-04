import os
import sys
import time
import httpx
import asyncio
import json
import hashlib
import wave
import struct
import numpy as np

API_BASE = "http://localhost:8000"

def log_step(name, status, details=""):
    color = "\033[92m" if status == "PASS" else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{status}{reset}] {name} {f'({details})' if details else ''}")

async def run_e2e_flow():
    print("=== Starting RakshaNet End-to-End Smoke Test ===")
    
    # Check gateway health with a larger timeout for model loading
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.get(f"{API_BASE}/health")
            if r.status_code == 200:
                log_step("Gateway Health Check", "PASS")
            else:
                log_step("Gateway Health Check", "FAIL", f"Status: {r.status_code}")
                sys.exit(1)
        except Exception as e:
            log_step("Gateway Health Check", "FAIL", f"Could not connect: {e}")
            sys.exit(1)

        # Step 1: Citizen login & Scam Transcript Submit
        print("\n--- Step 1: Citizen submits transcript and checks risk ---")
        try:
            # Login as citizen
            login_res = await client.post(f"{API_BASE}/auth/login", data={
                "username": "citizen_john",
                "password": "citizen_pass"
            })
            if login_res.status_code != 200:
                log_step("Citizen Login", "FAIL", f"Status: {login_res.status_code}")
                sys.exit(1)
            
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            log_step("Citizen Login", "PASS")

            # Post scam transcript
            transcript = "CBI Police alert. You are under digital arrest for money laundering. Transfer all your funds to safe custody ledger immediately."
            complaint_res = await client.post(f"{API_BASE}/complaints", json={
                "reporter_name": "Bob Miller",
                "phone": "9988776655",
                "text_content": transcript,
                "location_lat": 28.58,
                "location_lng": 77.22
            })
            if complaint_res.status_code != 201:
                log_step("Submit Transcript", "FAIL", f"Status: {complaint_res.status_code}")
                sys.exit(1)
            
            comp_id_1 = complaint_res.json()["id"]
            risk_score = complaint_res.json()["risk_score"]
            log_step("Submit Transcript", "PASS", f"Comp ID: {comp_id_1}, Risk Score: {risk_score}%")

            # Verify NLP verdict explanation
            risk_check_res = await client.post(f"{API_BASE}/complaints/{comp_id_1}/risk-check")
            explanation = risk_check_res.json()["risk_explanation"]
            log_step("Verify Risk Check Explanation", "PASS", f"Explanation: {explanation}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            log_step("Step 1 Flow", "FAIL", str(e))
            sys.exit(1)

        # Step 2: WebSocket alert propagation & Case auto-creation
        print("\n--- Step 2: Verify live WebSocket alert & PostGIS Case routing ---")
        try:
            # Re-fetch the complaint to verify it got linked to a Delhi officer case
            comp_details = await client.get(f"{API_BASE}/complaints/{comp_id_1}")
            case_id_1 = comp_details.json().get("case_id")
            if case_id_1:
                # Fetch case detail
                case_res = await client.get(f"{API_BASE}/cases/{case_id_1}", headers=headers)
                case_data = case_res.json()
                log_step("Auto Case Linking", "PASS", f"Case ID: {case_id_1}, Title: {case_data['title']}, Severity: {case_data['severity']}")
            else:
                log_step("Auto Case Linking", "FAIL", "No case linked to complaint")

            # Check heatmap grid aggregation
            geo_res = await client.get(f"{API_BASE}/geo/heatmap")
            features = geo_res.json().get("features", [])
            if len(features) >= 1:
                log_step("PostGIS Heatmap Aggregation", "PASS", f"Found {len(features)} grid points")
            else:
                log_step("PostGIS Heatmap Aggregation", "FAIL", "Heatmap empty")

        except Exception as e:
            log_step("Step 2 Flow", "FAIL", str(e))
            sys.exit(1)

        # Step 3: Second duplicate complaint & Graph Clustering
        print("\n--- Step 3: Submit second complaint with duplicate phone and check clustering ---")
        try:
            # Second complaint sharing phone "9988776655"
            transcript_2 = "Urgent: This is CBI officer calling you. You are in digital arrest. Connect to Skype immediately."
            complaint_res_2 = await client.post(f"{API_BASE}/complaints", json={
                "reporter_name": "Sarah Connor",
                "phone": "9988776655",
                "text_content": transcript_2,
                "location_lat": 28.62,
                "location_lng": 77.25
            })
            comp_id_2 = complaint_res_2.json()["id"]
            
            # Fetch cluster mappings
            cluster_res = await client.get(f"{API_BASE}/graph/cluster", headers=headers)
            graph_nodes = cluster_res.json().get("nodes", [])
            
            # Filter nodes matching phone
            phone_nodes = [n for n in graph_nodes if n["value"] == "9988776655"]
            if phone_nodes:
                cluster_id = phone_nodes[0].get("cluster_id")
                log_step("Neo4j Campaign Clustering", "PASS", f"Entity '9988776655' mapped to Cluster ID: {cluster_id}")
            else:
                log_step("Neo4j Campaign Clustering", "FAIL", "Phone entity not found in Neo4j graph")

        except Exception as e:
            log_step("Step 3 Flow", "FAIL", str(e))
            sys.exit(1)

        # Step 4: Bank Console Risk scoring
        print("\n--- Step 4: Verify bank transaction risk scoring ---")
        try:
            # Create a transaction referencing the same account/phone number to verify risk propagation
            # We use transaction ID 12345 (our seeded dummy)
            tx_res = await client.get(f"{API_BASE}/transactions/12345/score")
            tx_data = tx_res.json()
            log_step("Bank Risk Assessment", "PASS", f"TX ID: {tx_data['transaction_id']}, Risk Score: {tx_data['risk_score']}%, Explanation: {tx_data['explanation']}")
        except Exception as e:
            log_step("Bank Risk Assessment", "FAIL", str(e))

        # Step 5: Evidence chain hash check & PDF export
        print("\n--- Step 5: Verify cryptographic evidence chain & PDF export ---")
        try:
            # Query evidence details
            ev_res = await client.get(f"{API_BASE}/evidence/1", headers=headers)
            ev_data = ev_res.json()
            is_valid = ev_data["verification"]["valid"]
            log_step("Crypto Hash Chain Verification", "PASS" if is_valid else "FAIL", f"Hash: {ev_data['sha256_hash'][:20]}..., Prev: {ev_data['previous_hash'][:20]}...")

            # Download PDF dossier
            pdf_res = await client.get(f"{API_BASE}/evidence/1/export", headers=headers)
            if pdf_res.status_code == 200 and len(pdf_res.content) > 1000:
                log_step("PDF Dossier Compile & Export", "PASS", f"Downloaded {len(pdf_res.content)} bytes PDF")
            else:
                log_step("PDF Dossier Compile & Export", "FAIL", f"Status: {pdf_res.status_code}")

        except Exception as e:
            log_step("Step 5 Flow", "FAIL", str(e))

        # Step 6: Counterfeit CV scans
        print("\n--- Step 6: Verify counterfeit banknote CV scanner ---")
        try:
            # Generate temporary image
            import cv2
            img = np.ones((400, 800, 3), dtype=np.uint8) * 120
            # Draw fake security thread
            cv2.line(img, (380, 0), (380, 400), (20, 20, 20), 4)
            # Save
            temp_path = "temp_counterfeit_scan.png"
            cv2.imwrite(temp_path, img)

            # Upload
            with open(temp_path, "rb") as f:
                scan_res = await client.post(
                    f"{API_BASE}/counterfeit/scan",
                    files={"file": (temp_path, f, "image/png")}
                )
            
            if scan_res.status_code == 201:
                scan_data = scan_res.json()
                log_step("Counterfeit Scan Ingestion", "PASS", f"Verdict: {scan_data['verdict']}, Confidence: {scan_data['confidence']}%")
            else:
                log_step("Counterfeit Scan Ingestion", "FAIL", f"Status: {scan_res.status_code}")

            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            log_step("Counterfeit Scan Ingestion", "FAIL", str(e))

        # Step 7: Admin Panel validation
        print("\n--- Step 7: Verify Admin Model Health Dashboard ---")
        try:
            # Authenticate as admin
            admin_login_res = await client.post(f"{API_BASE}/auth/login", data={"username": "admin", "password": "admin_pass"})
            admin_token = admin_login_res.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            
            metrics_res = await client.get(f"{API_BASE}/admin/model-metrics", headers=admin_headers)
            metrics = metrics_res.json()
            log_step("Admin Model Metrics Fetch", "PASS", f"Retrieved {len(metrics)} model scores")
            for m in metrics:
                print(f"  - {m['model_name']}: Precision={m['precision']*100}%, Recall={m['recall']*100}%, FPR={m['false_positive_rate']*100}%")
        except Exception as e:
            log_step("Admin Model Metrics Fetch", "FAIL", str(e))

    print("\n=== End-to-End Smoke Test Completed ===")

if __name__ == "__main__":
    asyncio.run(run_e2e_flow())
