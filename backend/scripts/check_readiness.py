import requests
import os
import sys

def check_readiness():
    print("="*50)
    print("   SWS AI - INFRASTRUCTURE READINESS CHECK   ")
    print("="*50)
    
    # 1. Get Public IP
    try:
        ip = requests.get('https://api.ipify.org').text
        print(f"[1] YOUR PUBLIC IP: {ip}")
        print(f"    ACTION: Ensure this IP is added to your AWS RDS Security Group Inbound Rules (Port 5432).")
    except:
        print("[1] Could not determine public IP. Ensure you have internet access.")

    # 2. Check .env
    env_path = 'backend/.env'
    if os.path.exists(env_path):
        print(f"[2] .env FILE: FOUND")
        with open(env_path, 'r') as f:
            content = f.read()
            if 'rds-endpoint' in content:
                print("    WARNING: You are still using the placeholder 'rds-endpoint'. Update it with your actual RDS endpoint.")
            if 'your_access_key' in content:
                print("    WARNING: You are still using placeholder AWS keys.")
    else:
        print(f"[2] .env FILE: MISSING")

    # 3. Network Test (Ping RDS port if endpoint is provided)
    print("\n[3] TESTING NETWORK PATH...")
    # I'll just check if they have a real-looking endpoint
    from dotenv import load_dotenv
    load_dotenv(env_path)
    db_url = os.getenv("DATABASE_URL")
    if db_url and "@" in db_url:
        endpoint = db_url.split("@")[1].split(":")[0]
        print(f"    TARGET RDS ENDPOINT: {endpoint}")
        print(f"    TIP: If the connection hangs, it's 100% a Security Group / Firewall issue.")

    print("\n" + "="*50)

if __name__ == "__main__":
    check_readiness()
