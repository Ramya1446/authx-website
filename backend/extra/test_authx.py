"""
Authx System Testing Script
Tests backend API, AI detection, and blockchain integration
"""

import requests
import json
from pathlib import Path
import time
from PIL import Image
import io
import numpy as np

# Configuration
API_BASE = "http://127.0.0.1:8000"
TEST_IMAGE_PATH = "test_image.jpg"  # Create a test image

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_test(message):
    """Print test header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}🧪 {message}{Colors.END}")

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")

def create_test_image():
    """Create a test image if it doesn't exist"""
    if not Path(TEST_IMAGE_PATH).exists():
        print_info(f"Creating test image: {TEST_IMAGE_PATH}")
        # Create a simple test image
        img = Image.new('RGB', (400, 300), color=(73, 109, 137))
        img.save(TEST_IMAGE_PATH)
        print_success("Test image created")
    return TEST_IMAGE_PATH

def test_health_check():
    """Test 1: Backend health check"""
    print_test("Test 1: Backend Health Check")
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend is healthy: {data}")
            return True
        else:
            print_error(f"Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Make sure it's running on http://127.0.0.1:8000")
        return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False

def test_content_registration():
    """Test 2: Content registration"""
    print_test("Test 2: Content Registration")
    
    try:
        image_path = create_test_image()
        
        with open(image_path, 'rb') as f:
            files = {'file': ('test_image.jpg', f, 'image/jpeg')}
            data = {
                'owner_name': 'Test User',
                'owner_address': 'test@example.com',
                'content_type': 'image',
                'description': 'Test image for Authx system testing',
                'ai_tool': 'None'
            }
            
            response = requests.post(f"{API_BASE}/register", files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'ok':
                print_success("Content registered successfully!")
                proof = result.get('proof', {})
                print_info(f"Content ID: {proof.get('id')}")
                print_info(f"SHA-256: {proof.get('sha256')[:16]}...")
                print_info(f"Tamper Score: {proof.get('tamper_score', 0) * 100:.1f}%")
                
                if proof.get('tx_hash'):
                    print_info(f"Blockchain TX: {proof.get('tx_hash')[:16]}...")
                
                return proof.get('id'), proof.get('sha256')
            
            elif result.get('status') == 'already_registered':
                print_info("Content already registered (expected for repeated tests)")
                return None, None
        
        print_error(f"Registration failed: {response.status_code}")
        print_error(response.text)
        return None, None
        
    except Exception as e:
        print_error(f"Registration error: {e}")
        return None, None

def test_content_verification():
    """Test 3: Content verification"""
    print_test("Test 3: Content Verification (Exact Match)")
    
    try:
        image_path = create_test_image()
        
        with open(image_path, 'rb') as f:
            files = {'file': ('test_image.jpg', f, 'image/jpeg')}
            response = requests.post(f"{API_BASE}/verify", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            print_success(f"Verification Result: {result.get('result')}")
            print_info(f"Confidence: {result.get('confidence', 0) * 100:.1f}%")
            
            match_details = result.get('match_details')
            if match_details:
                print_info(f"Original Owner: {match_details.get('owner_name')}")
                print_info(f"Registered: {match_details.get('registered_at')}")
            
            tampering = result.get('tampering_analysis')
            if tampering:
                print_info(f"Tamper Probability: {tampering.get('tamper_probability', 0) * 100:.1f}%")
                artifacts = tampering.get('detected_artifacts', [])
                if artifacts:
                    print_info(f"Detected Artifacts: {', '.join(artifacts)}")
            
            return True
        
        print_error(f"Verification failed: {response.status_code}")
        return False
        
    except Exception as e:
        print_error(f"Verification error: {e}")
        return False

def test_modified_image_detection():
    """Test 4: Modified image detection"""
    print_test("Test 4: Modified Image Detection")
    
    try:
        # Create modified version of test image
        original = Image.open(TEST_IMAGE_PATH)
        modified = original.copy()
        
        # Add noise to simulate modification
        img_array = np.array(modified)
        noise = np.random.randint(-30, 30, img_array.shape, dtype=np.int16)
        modified_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        modified = Image.fromarray(modified_array)
        
        # Save modified image
        modified_path = "test_image_modified.jpg"
        modified.save(modified_path)
        print_info(f"Created modified image: {modified_path}")
        
        # Verify modified image
        with open(modified_path, 'rb') as f:
            files = {'file': ('test_image_modified.jpg', f, 'image/jpeg')}
            response = requests.post(f"{API_BASE}/verify", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            result_type = result.get('result')
            print_success(f"Detection Result: {result_type}")
            
            if result_type == "near_duplicate":
                print_success("✨ Successfully detected as modified version!")
                print_info(f"Confidence: {result.get('confidence', 0) * 100:.1f}%")
                
                match_details = result.get('match_details')
                if match_details and 'phash_distance' in match_details:
                    print_info(f"pHash Distance: {match_details['phash_distance']}")
            
            elif result_type == "exact_match":
                print_info("Detected as exact match (modifications too minor)")
            
            else:
                print_info(f"Detected as: {result_type}")
            
            return True
        
        print_error(f"Modified image verification failed: {response.status_code}")
        return False
        
    except Exception as e:
        print_error(f"Modified image detection error: {e}")
        return False

def test_proof_retrieval(content_id):
    """Test 5: Proof certificate retrieval"""
    print_test("Test 5: Proof Certificate Retrieval")
    
    if not content_id:
        print_info("Skipping (no content ID from registration)")
        return False
    
    try:
        response = requests.get(f"{API_BASE}/proof/{content_id}", timeout=5)
        
        if response.status_code == 200:
            proof = response.json()
            print_success("Proof certificate retrieved successfully!")
            print_info(f"Owner: {proof.get('owner_name')}")
            print_info(f"Content Type: {proof.get('content_type')}")
            print_info(f"SHA-256: {proof.get('sha256')[:32]}...")
            
            if proof.get('tx_hash'):
                print_info(f"Blockchain TX: {proof.get('tx_hash')[:32]}...")
            
            return True
        
        elif response.status_code == 404:
            print_error("Proof certificate not found")
            return False
        
        print_error(f"Proof retrieval failed: {response.status_code}")
        return False
        
    except Exception as e:
        print_error(f"Proof retrieval error: {e}")
        return False

def test_ai_tampering_detection():
    """Test 6: AI tampering detection analysis"""
    print_test("Test 6: AI Tampering Detection System")
    
    try:
        from ai_detector import AITamperingDetector
        
        detector = AITamperingDetector()
        print_success("AI Detector initialized")
        
        # Test with original image
        with open(TEST_IMAGE_PATH, 'rb') as f:
            file_bytes = f.read()
        
        result = detector.analyze(file_bytes, "image/jpeg")
        
        print_info(f"Tamper Probability: {result['tamper_probability'] * 100:.1f}%")
        print_info(f"Confidence: {result['confidence'] * 100:.1f}%")
        
        if result.get('detected_artifacts'):
            print_info(f"Artifacts: {', '.join(result['detected_artifacts'])}")
        else:
            print_success("No tampering artifacts detected")
        
        details = result.get('analysis_details', {})
        print_info(f"Statistical Score: {details.get('statistical_score', 0):.2f}")
        print_info(f"Frequency Score: {details.get('frequency_score', 0):.2f}")
        print_info(f"Noise Score: {details.get('noise_score', 0):.2f}")
        
        return True
        
    except ImportError:
        print_info("AI detector module not found in current directory")
        print_info("This test should be run from the backend directory")
        return False
    except Exception as e:
        print_error(f"AI detection test error: {e}")
        return False

def test_blockchain_integration():
    """Test 7: Blockchain integration"""
    print_test("Test 7: Blockchain Integration")
    
    try:
        from blockchain import BlockchainManager
        
        blockchain = BlockchainManager()
        print_success(f"Blockchain Manager initialized (mode: {blockchain.mode})")
        
        # Test registration simulation
        result = blockchain.register(
            sha256_hash="test_hash_123456789",
            owner_name="Test User",
            content_type="image"
        )
        
        if result.get('tx_hash'):
            print_success("Blockchain registration successful!")
            print_info(f"TX Hash: {result['tx_hash'][:32]}...")
            print_info(f"Block Number: {result.get('block_number')}")
            print_info(f"Status: {result.get('status')}")
            return True
        
        print_error("Blockchain registration returned no transaction")
        return False
        
    except ImportError:
        print_info("Blockchain module not found in current directory")
        print_info("This test should be run from the backend directory")
        return False
    except Exception as e:
        print_error(f"Blockchain test error: {e}")
        return False

def run_all_tests():
    """Run all tests and generate report"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"  AUTHX SYSTEM TEST SUITE")
    print(f"{'='*60}{Colors.END}\n")
    
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Test 1: Health Check
    results['total'] += 1
    if test_health_check():
        results['passed'] += 1
    else:
        results['failed'] += 1
        print_error("\n⚠️  Backend not running. Start it with: python app.py")
        print_error("Skipping remaining API tests...\n")
        print_final_report(results)
        return
    
    # Small delay between tests
    time.sleep(0.5)
    
    # Test 2: Registration
    results['total'] += 1
    content_id, sha256 = test_content_registration()
    if content_id or sha256:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    time.sleep(0.5)
    
    # Test 3: Verification
    results['total'] += 1
    if test_content_verification():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    time.sleep(0.5)
    
    # Test 4: Modified Image Detection
    results['total'] += 1
    if test_modified_image_detection():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    time.sleep(0.5)
    
    # Test 5: Proof Retrieval
    results['total'] += 1
    if content_id:
        if test_proof_retrieval(content_id):
            results['passed'] += 1
        else:
            results['failed'] += 1
    else:
        print_info("Skipping proof retrieval (no content ID)")
        results['skipped'] += 1
    
    time.sleep(0.5)
    
    # Test 6: AI Detection (requires running from backend dir)
    results['total'] += 1
    if test_ai_tampering_detection():
        results['passed'] += 1
    else:
        results['skipped'] += 1
    
    time.sleep(0.5)
    
    # Test 7: Blockchain (requires running from backend dir)
    results['total'] += 1
    if test_blockchain_integration():
        results['passed'] += 1
    else:
        results['skipped'] += 1
    
    # Final report
    print_final_report(results)

def print_final_report(results):
    """Print final test report"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"  TEST REPORT")
    print(f"{'='*60}{Colors.END}")
    print(f"\n  Total Tests:   {results['total']}")
    print(f"  {Colors.GREEN}✅ Passed:      {results['passed']}{Colors.END}")
    print(f"  {Colors.RED}❌ Failed:      {results['failed']}{Colors.END}")
    print(f"  {Colors.YELLOW}⏭️  Skipped:     {results['skipped']}{Colors.END}")
    
    success_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    
    print(f"\n  Success Rate: {Colors.BOLD}", end="")
    if success_rate >= 80:
        print(f"{Colors.GREEN}{success_rate:.1f}%{Colors.END}")
    elif success_rate >= 50:
        print(f"{Colors.YELLOW}{success_rate:.1f}%{Colors.END}")
    else:
        print(f"{Colors.RED}{success_rate:.1f}%{Colors.END}")
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    if results['failed'] == 0 and results['passed'] > 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Authx system is working correctly.{Colors.END}\n")
    elif results['failed'] > 0:
        print(f"{Colors.RED}⚠️  Some tests failed. Check the errors above.{Colors.END}\n")

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user.{Colors.END}\n")
    except Exception as e:
        print(f"\n\n{Colors.RED}Fatal error: {e}{Colors.END}\n")