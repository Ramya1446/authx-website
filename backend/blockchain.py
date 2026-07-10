"""
blockchain.py -
Blockchain integration module for Authx
Supports multiple blockchain networks with fallback to local simulation
"""

from web3 import Web3
# Handle different web3.py versions
try:
    from web3.middleware import geth_poa_middleware  # type: ignore
except ImportError:
    try:
        from web3.middleware.geth_poa import geth_poa_middleware  # type: ignore
    except ImportError:
        # If neither works, we'll handle it gracefully
        geth_poa_middleware = None
        
import json
import time
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class BlockchainManager:
    """
    Manages blockchain interactions for content registration
    Supports: Ethereum, Polygon, Ganache, or simulation mode
    """
    
    def __init__(self):
        self.mode = os.getenv("BLOCKCHAIN_MODE", "simulation")  # "ethereum", "polygon", "ganache", "simulation"
        self.w3 = None
        self.contract = None
        self.account = None
        
        if self.mode != "simulation":
            self._initialize_blockchain()
    
    def _initialize_blockchain(self):
        """Initialize Web3 connection based on mode"""
        try:
            if self.mode == "ganache":
                # Local Ganache instance
                provider_url = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
                self.w3 = Web3(Web3.HTTPProvider(provider_url))
                
            elif self.mode == "polygon":
                # Polygon Mumbai testnet or mainnet
                provider_url = os.getenv("POLYGON_RPC_URL", "https://rpc-mumbai.maticvigil.com")
                self.w3 = Web3(Web3.HTTPProvider(provider_url))
                if geth_poa_middleware:
                    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
            elif self.mode == "ethereum":
                # Ethereum Sepolia testnet or mainnet via Infura/Alchemy
                provider_url = os.getenv("ETH_RPC_URL", "https://sepolia.infura.io/v3/YOUR_KEY")
                self.w3 = Web3(Web3.HTTPProvider(provider_url))
            
            if self.w3 and self.w3.is_connected():
                print(f"✅ Connected to {self.mode} blockchain")
                
                # Load account from private key
                private_key = os.getenv("PRIVATE_KEY")
                if private_key:
                    # Ensure proper format
                    if not private_key.startswith('0x'):
                        private_key = '0x' + private_key
                    self.account = self.w3.eth.account.from_key(private_key)
                    print(f"✅ Account loaded: {self.account.address}")
                
                # Load smart contract
                self._load_contract()
            else:
                print(f"⚠️  Failed to connect to {self.mode}, using simulation mode")
                self.mode = "simulation"
                
        except Exception as e:
            print(f"⚠️  Blockchain init error: {e}, using simulation mode")
            self.mode = "simulation"
    
    def _load_contract(self):
        """Load deployed smart contract"""
        try:
            contract_address = os.getenv("CONTRACT_ADDRESS")
            if not contract_address:
                print("⚠️  No contract address found, skipping contract load")
                return
            
            # Load ABI from file
            with open("contract_abi.json", "r") as f:
                contract_abi = json.load(f)
            
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=contract_abi
            )
            print(f"✅ Contract loaded at {contract_address}")
            
        except Exception as e:
            print(f"⚠️  Contract load error: {e}")
    
    def register(self, sha256_hash: str, owner_name: str, content_type: str) -> Dict:
        """
        Register content hash on blockchain
        Returns transaction hash and block number
        """
        if self.mode == "simulation":
            return self._simulate_registration(sha256_hash, owner_name, content_type)
        
        try:
            if not self.contract or not self.account:
                print("⚠️  Contract or account not initialized, using simulation")
                return self._simulate_registration(sha256_hash, owner_name, content_type)
            
            # Check if already registered
            try:
                existing = self.contract.functions.contentExists(sha256_hash).call()
                if existing:
                    print(f"⚠️  Content already registered: {sha256_hash[:16]}...")
                    # Get existing record
                    result = self.contract.functions.getContent(sha256_hash).call()
                    return {
                        "tx_hash": "0x" + "0" * 64,  # Dummy hash
                        "block_number": 0,
                        "status": "already_registered",
                        "gas_used": 0,
                        "existing_owner": result[2],  # ownerName
                        "timestamp": result[4]  # timestamp
                    }
            except Exception as e:
                print(f"⚠️  Could not check existing registration: {e}")
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Estimate gas first
            try:
                gas_estimate = self.contract.functions.registerContent(
                    sha256_hash,
                    owner_name,
                    content_type
                ).estimate_gas({'from': self.account.address})
                gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
            except Exception as e:
                print(f"⚠️  Gas estimation failed: {e}")
                print(f"    Using default gas limit")
                gas_limit = 300000
            
            print(f"📊 Gas estimate: {gas_limit}")
            
            # Call smart contract function
            txn = self.contract.functions.registerContent(
                sha256_hash,
                owner_name,
                content_type
            ).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, self.account.key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            print(f"📝 Transaction sent: {tx_hash_hex}")
            
            # Wait for receipt (with timeout)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Check if transaction was successful
            if receipt['status'] == 0:
                print(f"❌ Transaction failed! Checking reason...")
                # Try to get revert reason
                try:
                    self.w3.eth.call(txn, receipt['blockNumber'])
                except Exception as e:
                    print(f"   Revert reason: {e}")
                
                return {
                    "tx_hash": tx_hash_hex,
                    "block_number": receipt['blockNumber'],
                    "status": "failed",
                    "gas_used": receipt['gasUsed'],
                    "error": "Transaction reverted"
                }
            
            print(f"✅ Transaction confirmed in block {receipt['blockNumber']}")
            
            return {
                "tx_hash": tx_hash_hex,
                "block_number": receipt['blockNumber'],
                "status": "confirmed",
                "gas_used": receipt['gasUsed']
            }
            
        except Exception as e:
            print(f"⚠️  Blockchain registration error: {e}")
            import traceback
            traceback.print_exc()
            return self._simulate_registration(sha256_hash, owner_name, content_type)
    
    def _simulate_registration(self, sha256_hash: str, owner_name: str, content_type: str) -> Dict:
        """
        Simulate blockchain registration for development/testing
        Generates realistic-looking transaction data
        """
        import random
        import hashlib
        
        # Generate deterministic but unique-looking transaction hash
        tx_data = f"{sha256_hash}{owner_name}{time.time()}"
        tx_hash = "0x" + hashlib.sha256(tx_data.encode()).hexdigest()
        
        # Simulate block number
        block_number = random.randint(1000000, 9999999)
        
        print(f"🔷 Simulated blockchain registration")
        print(f"   TX: {tx_hash}")
        print(f"   Block: {block_number}")
        
        return {
            "tx_hash": tx_hash,
            "block_number": block_number,
            "status": "simulated",
            "gas_used": 150000
        }
    
    def verify_registration(self, sha256_hash: str) -> Optional[Dict]:
        """
        Verify if content is registered on blockchain
        Returns registration details if found
        """
        if self.mode == "simulation":
            return None  # Simulation mode doesn't support verification
        
        try:
            if not self.contract:
                return None
            
            # Call smart contract view function
            result = self.contract.functions.getContent(sha256_hash).call()
            
            if result[0]:  # If content exists
                return {
                    "owner_address": result[1],  # owner (address)
                    "owner": result[2],  # ownerName (string)
                    "content_type": result[3],  # contentType
                    "timestamp": result[4],  # timestamp
                    "verified": True
                }
            return None
            
        except Exception as e:
            print(f"⚠️  Blockchain verification error: {e}")
            return None
    
    def get_transaction_info(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction details from blockchain"""
        if self.mode == "simulation":
            return {"status": "simulated", "message": "Simulated transaction"}
        
        try:
            if not self.w3:
                return None
            
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            tx = self.w3.eth.get_transaction(tx_hash)
            
            return {
                "block_number": receipt['blockNumber'],
                "from": receipt['from'],
                "to": receipt['to'],
                "gas_used": receipt['gasUsed'],
                "status": "confirmed" if receipt['status'] == 1 else "failed",
                "timestamp": self.w3.eth.get_block(receipt['blockNumber'])['timestamp']
            }
            
        except Exception as e:
            print(f"⚠️  Transaction lookup error: {e}")
            return None
    
    def get_owner_content(self, owner_address: str) -> list:
        """Get all content registered by an owner"""
        if self.mode == "simulation" or not self.contract:
            return []
        
        try:
            content_hashes = self.contract.functions.getOwnerContent(
                Web3.to_checksum_address(owner_address)
            ).call()
            return content_hashes
        except Exception as e:
            print(f"⚠️  Error getting owner content: {e}")
            return []
    
    def get_total_registered(self) -> int:
        """Get total number of registered content"""
        if self.mode == "simulation" or not self.contract:
            return 0
        
        try:
            return self.contract.functions.getTotalRegistered().call()
        except Exception as e:
            print(f"⚠️  Error getting total: {e}")
            return 0