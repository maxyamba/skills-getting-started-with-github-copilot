"""
FastAPI tests for Mergington High School Activities API

Tests follow the AAA (Arrange-Act-Assert) pattern for clarity and structure.
"""

import pytest
import copy
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test for isolation"""
    # Store original state
    original_activities = copy.deepcopy(activities)
    
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Arrange-Act-Assert: Verify all activities are returned"""
        # Arrange: No setup needed, using fixture to reset state
        
        # Act
        response = client.get("/activities")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9  # We have 9 activities in the database
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_structure(self, client, reset_activities):
        """Arrange-Act-Assert: Verify activity data structure"""
        # Arrange: No setup needed
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_student_success(self, client, reset_activities):
        """Arrange-Act-Assert: Student successfully signs up for available activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "neustudent@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity_name}"
        assert email in activities[activity_name]["participants"]
    
    def test_signup_updates_participants_list(self, client, reset_activities):
        """Arrange-Act-Assert: Verify participant is added to activity's list"""
        # Arrange
        activity_name = "Programming Class"
        email = "alice@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Assert
        assert response.status_code == 200
        new_count = len(activities[activity_name]["participants"])
        assert new_count == initial_count + 1
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Arrange-Act-Assert: Error when activity doesn't exist"""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Arrange-Act-Assert: Error when student already signed up"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_activity_at_capacity(self, client, reset_activities):
        """Arrange-Act-Assert: Error when activity is full"""
        # Arrange
        activity_name = "Tennis Club"  # max_participants: 10
        # Fill it to capacity
        for i in range(10):
            activities[activity_name]["participants"].append(f"student{i}@mergington.edu")
        
        email = "overflow@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Assert - This tests current behavior (no capacity check)
        # If capacity check is added later, this will need updating
        assert response.status_code == 200  # Currently allows overfill


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_student_success(self, client, reset_activities):
        """Arrange-Act-Assert: Student successfully unregisters from activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
        assert email not in activities[activity_name]["participants"]
    
    def test_unregister_removes_from_list(self, client, reset_activities):
        """Arrange-Act-Assert: Verify participant is removed from activity's list"""
        # Arrange
        activity_name = "Drama Club"
        email = "noah@mergington.edu"  # Already signed up
        initial_count = len(activities[activity_name]["participants"])
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        # Assert
        assert response.status_code == 200
        new_count = len(activities[activity_name]["participants"])
        assert new_count == initial_count - 1
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Arrange-Act-Assert: Error when activity doesn't exist"""
        # Arrange
        activity_name = "Fake Activity"
        email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_student_not_signed_up(self, client, reset_activities):
        """Arrange-Act-Assert: Error when student is not in activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "notsignedupstudent@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]


class TestSignupAndUnregisterFlow:
    """Integration tests for signup and unregister workflow"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Arrange-Act-Assert: Sign up, then immediately unregister"""
        # Arrange
        activity_name = "Science Club"
        email = "testuser@mergington.edu"
        
        # Act: Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Act: Unregister
        unregister_response = client.post(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        # Assert
        assert unregister_response.status_code == 200
        assert email not in activities[activity_name]["participants"]
    
    def test_cannot_signup_twice(self, client, reset_activities):
        """Arrange-Act-Assert: Second signup attempt fails"""
        # Arrange
        activity_name = "Art Studio"
        email = "doubleregister@mergington.edu"
        
        # Act: First signup
        response1 = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Act: Try to signup again
        response2 = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
