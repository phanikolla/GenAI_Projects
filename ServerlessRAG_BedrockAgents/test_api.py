"""
Test script for Serverless RAG API
Tests authentication, document upload, and query functionality
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
TEST_EMAIL = 'test@example.com'
TEST_PASSWORD = 'TestPass123!'
TEST_DOCUMENT = 'test_document.pdf'


class RAGAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.document_id = None
    
    def test_health(self):
        """Test health endpoint"""
        print("\n1. Testing health endpoint...")
        response = requests.get(f"{self.base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        print("   ✓ Health check passed")
    
    def test_signup(self):
        """Test user signup"""
        print("\n2. Testing user signup...")
        response = requests.post(
            f"{self.base_url}/auth/signup",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": "Test User"
            }
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
            print("   ✓ Signup successful")
        else:
            print(f"   Note: User may already exist - {response.text}")
    
    def test_login(self):
        """Test user login"""
        print("\n3. Testing user login...")
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            print(f"   Access token: {self.access_token[:20]}...")
            print("   ✓ Login successful")
        else:
            print(f"   Error: {response.text}")
            raise Exception("Login failed")
    
    def test_upload_document(self):
        """Test document upload"""
        print("\n4. Testing document upload...")
        
        # Create a dummy PDF if test file doesn't exist
        if not os.path.exists(TEST_DOCUMENT):
            print("   Creating dummy PDF for testing...")
            with open(TEST_DOCUMENT, 'wb') as f:
                # Minimal PDF structure
                f.write(b'%PDF-1.4\n')
                f.write(b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n')
                f.write(b'2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n')
                f.write(b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n')
                f.write(b'xref\n0 4\n0000000000 65535 f\n')
                f.write(b'0000000009 00000 n\n0000000056 00000 n\n0000000115 00000 n\n')
                f.write(b'trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n')
        
        with open(TEST_DOCUMENT, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/documents/upload",
                headers={"Authorization": f"Bearer {self.access_token}"},
                files={"file": (TEST_DOCUMENT, f, "application/pdf")}
            )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.document_id = data.get('document_id')
            print(f"   Document ID: {self.document_id}")
            print(f"   Status: {data.get('status')}")
            print("   ✓ Upload successful")
            print("   Note: Indexing may take a few minutes...")
        else:
            print(f"   Error: {response.text}")
    
    def test_list_documents(self):
        """Test listing documents"""
        print("\n5. Testing document listing...")
        response = requests.get(
            f"{self.base_url}/documents",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total documents: {data.get('count')}")
            print("   ✓ List successful")
        else:
            print(f"   Error: {response.text}")
    
    def test_query(self):
        """Test RAG query"""
        print("\n6. Testing RAG query...")
        print("   Waiting 30 seconds for indexing to complete...")
        time.sleep(30)
        
        response = requests.post(
            f"{self.base_url}/query",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={
                "question": "What is this document about?"
            }
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Answer: {data.get('answer')[:200]}...")
            print(f"   Sources: {len(data.get('sources', []))} documents")
            print("   ✓ Query successful")
        else:
            print(f"   Error: {response.text}")
    
    def test_refresh_token(self):
        """Test token refresh"""
        print("\n7. Testing token refresh...")
        response = requests.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get('access_token')
            print(f"   New access token: {self.access_token[:20]}...")
            print("   ✓ Refresh successful")
        else:
            print(f"   Error: {response.text}")
    
    def test_delete_document(self):
        """Test document deletion"""
        print("\n8. Testing document deletion...")
        if not self.document_id:
            print("   Skipping - no document to delete")
            return
        
        response = requests.delete(
            f"{self.base_url}/documents/{self.document_id}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
            print("   ✓ Delete successful")
        else:
            print(f"   Error: {response.text}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Serverless RAG API Test Suite")
        print("=" * 60)
        
        try:
            self.test_health()
            self.test_signup()
            self.test_login()
            self.test_upload_document()
            self.test_list_documents()
            self.test_query()
            self.test_refresh_token()
            self.test_delete_document()
            
            print("\n" + "=" * 60)
            print("All tests completed successfully! ✓")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            raise


if __name__ == "__main__":
    tester = RAGAPITester(API_BASE_URL)
    tester.run_all_tests()
