"""
Deploy ContentRegistry smart contract to Ganache
"""

from web3 import Web3
from solcx import compile_standard, install_solc
import json
import os
from dotenv import load_dotenv

load_dotenv()

def deploy_contract():
    """Deploy the ContentRegistry contract"""
    
    # Install Solidity compiler (matching your contract version)
    print("📦 Installing Solidity compiler...")
    install_solc('0.8.19')
    
    # Read contract source
    print("📖 Reading contract source...")
    contract_file = "ContentRegistry.sol"
    
    if not os.path.exists(contract_file):
        print(f"❌ {contract_file} not found!")
        print("Please make sure ContentRegistry.sol is in the same directory")
        return
    
    with open(contract_file, "r") as f:
        contract_source = f.read()
    
    # Compile contract
    print("🔨 Compiling contract...")
    try:
        compiled_sol = compile_standard(
            {
                "language": "Solidity",
                "sources": {"ContentRegistry.sol": {"content": contract_source}},
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                        }
                    }
                },
            },
            solc_version="0.8.19",
        )
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        return
    
    # Extract bytecode and ABI
    bytecode = compiled_sol["contracts"]["ContentRegistry.sol"]["ContentRegistry"]["evm"]["bytecode"]["object"]
    abi = compiled_sol["contracts"]["ContentRegistry.sol"]["ContentRegistry"]["abi"]
    
    # Save ABI for later use
    with open("contract_abi.json", "w") as f:
        json.dump(abi, f, indent=2)
    print("✅ ABI saved to contract_abi.json")
    
    # Connect to Ganache
    ganache_url = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
    w3 = Web3(Web3.HTTPProvider(ganache_url))
    
    if not w3.is_connected():
        print(f"❌ Failed to connect to Ganache at {ganache_url}")
        print("Make sure Ganache is running with: ganache --port 7545")
        return
    
    print(f"✅ Connected to Ganache at {ganache_url}")
    
    # Get account
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("❌ PRIVATE_KEY not found in .env")
        print("Add this to your .env file:")
        print("PRIVATE_KEY=0x16463531464e48e08bb4ec23e8e76b02003692e5a6f40b6e12dd85757a4573fa")
        return
    
    # Ensure proper format
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    try:
        account = w3.eth.account.from_key(private_key)
    except Exception as e:
        print(f"❌ Invalid private key: {e}")
        return
    
    print(f"📍 Deploying from account: {account.address}")
    
    # Get balance
    balance = w3.eth.get_balance(account.address)
    print(f"💰 Account balance: {w3.from_wei(balance, 'ether')} ETH")
    
    if balance == 0:
        print("❌ Account has no ETH!")
        return
    
    # Create contract instance
    ContentRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    print("🚀 Deploying contract...")
    nonce = w3.eth.get_transaction_count(account.address)
    
    transaction = ContentRegistry.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"📝 Transaction hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("⏳ Waiting for transaction receipt...")
    try:
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    except Exception as e:
        print(f"❌ Transaction failed: {e}")
        return
    
    contract_address = tx_receipt.contractAddress
    print(f"\n🎉 Contract deployed successfully!")
    print(f"📍 Contract address: {contract_address}")
    print(f"⛽ Gas used: {tx_receipt.gasUsed}")
    
    # Update .env file
    print("\n📝 Updating .env file...")
    env_path = ".env"
    
    try:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                env_content = f.read()
        else:
            env_content = ""
        
        if "CONTRACT_ADDRESS=" in env_content:
            # Update existing
            lines = env_content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("CONTRACT_ADDRESS="):
                    lines[i] = f"CONTRACT_ADDRESS={contract_address}"
            env_content = "\n".join(lines)
        else:
            # Add new
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f"CONTRACT_ADDRESS={contract_address}\n"
        
        with open(env_path, "w") as f:
            f.write(env_content)
        
        print(f"✅ Added CONTRACT_ADDRESS to .env")
    except Exception as e:
        print(f"⚠️  Could not update .env: {e}")
        print(f"Please manually add: CONTRACT_ADDRESS={contract_address}")
    
    # Test the contract
    print("\n🧪 Testing contract...")
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Test registration
    test_hash = "abc123def456789"
    test_owner = "Test Owner"
    test_type = "image/jpeg"
    
    print(f"   Registering test content: {test_hash}")
    
    try:
        nonce = w3.eth.get_transaction_count(account.address)
        txn = contract.functions.registerContent(
            test_hash, test_owner, test_type
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Verify registration
        result = contract.functions.getContent(test_hash).call()
        print(f"   ✅ Test registration successful!")
        print(f"   Owner: {result[2]}")  # ownerName
        print(f"   Type: {result[3]}")   # contentType
        print(f"   Timestamp: {result[4]}")  # timestamp
        
        # Test total registered
        total = contract.functions.getTotalRegistered().call()
        print(f"   Total registered: {total}")
        
    except Exception as e:
        print(f"   ⚠️  Test registration failed: {e}")
    
    print("\n" + "="*60)
    print("🎊 DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"Contract Address: {contract_address}")
    print(f"ABI File: contract_abi.json")
    print(f"Network: Ganache Local")
    print(f"Deployer: {account.address}")
    print("="*60)
    print("\nYour Authx app is now ready to use blockchain!")
    print("Run: python test_blockchain.py")

if __name__ == "__main__":
    deploy_contract()