"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting activities"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have activities
        assert len(data) > 0
        
        # Check that each activity has required fields
        for name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)
    
    def test_get_activities_includes_chess_club(self, client):
        """Test that Chess Club is in the activities"""
        response = client.get("/activities")
        data = response.json()
        
        assert "Chess Club" in data
        assert data["Chess Club"]["description"] == "Learn strategies and compete in chess tournaments"


class TestSignupForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_for_valid_activity(self, client):
        """Test successful signup for a valid activity"""
        response = client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post("/activities/Nonexistent%20Activity/signup?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        
        assert "detail" in data
        assert "already signed up" in data["detail"]


class TestUnregisterFromActivity:
    """Tests for unregistering from activities"""
    
    def test_unregister_existing_participant(self, client):
        """Test successfully unregistering a participant"""
        email = "test@mergington.edu"
        
        # First, sign up
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Unregistered" in data["message"]
        assert email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete("/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert data["detail"] == "Activity not found"
    
    def test_unregister_participant_not_signed_up(self, client):
        """Test unregistering a participant who isn't signed up"""
        response = client.delete("/activities/Chess%20Club/unregister?email=notsignedup@mergington.edu")
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "not signed up" in data["detail"]
    
    def test_unregister_preset_participant(self, client):
        """Test unregistering a participant that was in the initial data"""
        # Chess Club has "michael@mergington.edu" as a preset participant
        response = client.delete("/activities/Chess%20Club/unregister?email=michael@mergington.edu")
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity participant capacity"""
    
    def test_activity_has_max_participants(self, client):
        """Test that activities have a max_participants field"""
        response = client.get("/activities")
        data = response.json()
        
        for name, details in data.items():
            assert "max_participants" in details
            assert details["max_participants"] > 0
    
    def test_participants_count_accurate(self, client):
        """Test that participant count is accurate after signup and unregister"""
        email = "count@mergington.edu"
        
        # Get initial count
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Chess Club"]["participants"])
        
        # Sign up
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        response2 = client.get("/activities")
        new_count = len(response2.json()["Chess Club"]["participants"])
        assert new_count == initial_count + 1
        
        # Unregister
        client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        response3 = client.get("/activities")
        final_count = len(response3.json()["Chess Club"]["participants"])
        assert final_count == initial_count
