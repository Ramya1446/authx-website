"""
Test script to verify blockchain integration is working
"""

from blockchain import BlockchainManager
import os
from dotenv import load_dotenv

load_dotenv()

def test_blockchain_connection():
    """Test the blockchain connection and contract interaction"""
    
    print("="*60)
    print("🧪 Testing Authx Blockchain Integration")
    print("="*60)
    
    # Initialize blockchain manager
    print("\n1️⃣ Initializing BlockchainManager...")
    bm = BlockchainManager()
    
    print(f"   Mode: {bm.mode}")
    print(f"   Connected: {bm.w3.is_connected() if bm.w3 else 'N/A (simulation mode)'}")
    
    if bm.mode != "simulation" and bm.w3:
        print(f"   Account: {bm.account.address if bm.account else 'Not loaded'}")
        if bm.account:
            balance = bm.w3.eth.get_balance(bm.account.address)
            print(f"   Balance: {bm.w3.from_wei(balance, 'ether')} ETH")
        
        if bm.contract:
            contract_address = os.getenv("CONTRACT_ADDRESS")
            print(f"   Contract: {contract_address}")
        else:
            print(f"   Contract: Not loaded")
    
    # Test registration
    print("\n2️⃣ Testing content registration...")
    test_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    test_owner = "Test User"
    test_type = "image/jpeg"
    
    print(f"   Hash: {test_hash[:16]}...")
    print(f"   Owner: {test_owner}")
    print(f"   Type: {test_type}")
    
    result = bm.register(test_hash, test_owner, test_type)
    
    print("\n3️⃣ Registration result:")
    print(f"   TX Hash: {result['tx_hash'][:16]}...")
    print(f"   Block: {result['block_number']}")
    print(f"   Status: {result['status']}")
    print(f"   Gas Used: {result.get('gas_used', 'N/A')}")
    
    # Test verification (if not in simulation mode)
    if bm.mode != "simulation" and bm.contract:
        print("\n4️⃣ Testing verification...")
        verification = bm.verify_registration(test_hash)
        
        if verification:
            print(f"   ✅ Content verified on blockchain!")
            print(f"   Owner: {verification['owner']}")
            print(f"   Timestamp: {verification['timestamp']}")
            print(f"   Type: {verification['content_type']}")
        else:
            print(f"   ⚠️ Content not found in registry")
    else:
        print("\n4️⃣ Skipping verification (simulation mode)")
    
    # Test transaction info
    if bm.mode != "simulation":
        print("\n5️⃣ Testing transaction lookup...")
        tx_info = bm.get_transaction_info(result['tx_hash'])
        
        if tx_info:
            print(f"   Block: {tx_info.get('block_number', 'N/A')}")
            print(f"   From: {tx_info.get('from', 'N/A')}")
            print(f"   Status: {tx_info.get('status', 'N/A')}")
        else:
            print(f"   ⚠️ Transaction info not available")
    
    print("\n" + "="*60)
    print("✅ Blockchain Integration Test Complete!")
    print("="*60)
    
    return result

def check_env_config():
    """Check if .env is properly configured"""
    print("\n🔍 Checking .env configuration...")
    
    mode = os.getenv("BLOCKCHAIN_MODE")
    print(f"   BLOCKCHAIN_MODE: {mode or '❌ Not set (will use simulation)'}")
    
    if mode == "ganache":
        ganache_url = os.getenv("GANACHE_URL")
        print(f"   GANACHE_URL: {ganache_url or '❌ Not set'}")
    elif mode == "polygon":
        polygon_url = os.getenv("POLYGON_RPC_URL")
        print(f"   POLYGON_RPC_URL: {polygon_url or '❌ Not set'}")
    elif mode == "ethereum":
        eth_url = os.getenv("ETH_RPC_URL")
        print(f"   ETH_RPC_URL: {eth_url or '❌ Not set'}")
    
    private_key = os.getenv("PRIVATE_KEY")
    print(f"   PRIVATE_KEY: {'✅ Set' if private_key else '❌ Not set'}")
    
    contract_address = os.getenv("CONTRACT_ADDRESS")
    print(f"   CONTRACT_ADDRESS: {contract_address or '❌ Not set'}")
    
    if contract_address:
        print(f"      Address: {contract_address}")

if __name__ == "__main__":
    check_env_config()
    print()
    test_blockchain_connection()