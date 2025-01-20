import requests
import sys
import time
from typing import Optional, Dict, List
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Default to localhost if no server URL is provided
DEFAULT_SERVER_URL = "http://127.0.0.1:5000"

class DnDClient:
    def __init__(self, server_url: Optional[str] = None, api_key: Optional[str] = None):
        self.campaign_id: Optional[int] = None
        self.world_id: Optional[int] = None
        self.session_id: Optional[int] = None
        self.server_url = server_url or DEFAULT_SERVER_URL
        self.api_key = api_key or os.getenv('DND_API_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided either in constructor or DND_API_KEY environment variable")
        
        # Set up common headers
        self.headers = {'X-API-Key': self.api_key}

    def check_server(self) -> bool:
        """Check if the server is running."""
        try:
            # Try to connect to the base URL with API key
            requests.get(self.server_url, headers=self.headers)
            return True
        except requests.RequestException:
            return False

    def wait_for_server(self, timeout: int = 30) -> bool:
        """Wait for server to become available."""
        print("Checking server connection...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.check_server():
                print("Server is running!")
                return True
            print(f"Server not available at {self.server_url}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
        
        print(f"\nServer connection timed out after {timeout} seconds.")
        return False

    def list_sessions(self, campaign_id: int) -> List[Dict]:
        """List all sessions for a campaign."""
        try:
            response = requests.get(
                f"{self.server_url}/campaigns/{campaign_id}/sessions",
                headers=self.headers
            )
            response.raise_for_status()
            sessions = response.json()
            return sessions
        except requests.RequestException as e:
            print(f"Error listing sessions: {e}")
            return []

    def load_session(self, session_id: int, campaign_id: int, world_id: int) -> bool:
        """Load an existing session."""
        if not self.check_server():
            if not self.wait_for_server():
                return False

        self.campaign_id = campaign_id
        self.world_id = world_id
        self.session_id = session_id
        return True

    def start_session(self, campaign_id: int, world_id: int) -> bool:
        """Start a new D&D session."""
        if not self.check_server():
            if not self.wait_for_server():
                return False

        self.campaign_id = campaign_id
        self.world_id = world_id
        
        try:
            response = requests.post(
                f"{self.server_url}/sessions/start",
                json={"campaign_id": campaign_id},
                headers=self.headers
            )
            response.raise_for_status()
            self.session_id = response.json()["session_id"]
            return True
        except requests.RequestException as e:
            print(f"Error starting session: {e}")
            print("\nPlease verify that:")
            print("1. The campaign ID exists in the database")
            print("2. The server is running properly")
            print("3. Your API key is correct")
            return False

    def send_message(self, user_input: str) -> Optional[str]:
        """Send a message to the DM and get response."""
        if not all([self.campaign_id, self.world_id, self.session_id]):
            print("Session not initialized!")
            return None

        try:
            response = requests.post(
                f"{self.server_url}/sessions/{self.session_id}/interact",
                json={
                    "user_input": user_input,
                    "campaign_id": self.campaign_id,
                    "world_id": self.world_id
                },
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("dm_response", "").replace("<br>", "\n")
        except requests.RequestException as e:
            print(f"Error sending message: {e}")
            if not self.check_server():
                print("Server connection lost!")
            return None

    def end_session(self) -> Optional[str]:
        """End the current session and get a recap."""
        if not self.session_id:
            return None

        try:
            response = requests.post(
                f"{self.server_url}/sessions/{self.session_id}/end",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("recap")
        except requests.RequestException as e:
            print(f"Error ending session: {e}")
            return None

def main():
    # Get server URL and API key from environment variable or command line
    server_url = os.environ.get('DND_SERVER_URL') or (sys.argv[3] if len(sys.argv) > 3 else None)
    api_key = os.environ.get('DND_API_KEY') or (sys.argv[4] if len(sys.argv) > 4 else None)
    
    # Debug information
    print("\nDebug Info:")
    print(f"API Key from environment: {'Present' if os.environ.get('DND_API_KEY') else 'Not found'}")
    print(f"Server URL: {server_url}")
    if not api_key:
        print("Warning: No API key found in environment or command line arguments")
    
    try:
        # Initialize client
        client = DnDClient(server_url, api_key)
        
        # Get campaign and world IDs from command line or use defaults
        campaign_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        world_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    except (IndexError, ValueError) as e:
        if isinstance(e, ValueError) and str(e).startswith("API key must be provided"):
            print("\nError: API key is required. You can provide it in two ways:")
            print("1. Set DND_API_KEY environment variable")
            print("2. Pass it as the fourth argument")
        else:
            print("\nUsage: python cli_client.py [campaign_id] [world_id] [server_url] [api_key]")
            print("Or set environment variables:")
            print("  DND_SERVER_URL - for server URL")
            print("  DND_API_KEY - for API key")
            print("\nUsing default values: campaign_id=1, world_id=1")
        return
    
    # List existing sessions
    print("\nExisting sessions for this campaign:")
    sessions = client.list_sessions(campaign_id)
    if sessions:
        for i, session in enumerate(sessions, 1):
            created_at = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00'))
            print(f"{i}. Session {session['session_id']} (Created: {created_at.strftime('%Y-%m-%d %H:%M:%S')})")
        
        # Ask if user wants to load an existing session
        choice = input("\nEnter session number to load, or press Enter for new session: ").strip()
        if choice and choice.isdigit() and 1 <= int(choice) <= len(sessions):
            session = sessions[int(choice) - 1]
            if client.load_session(session['session_id'], campaign_id, world_id):
                print(f"\nLoaded session {session['session_id']}")
            else:
                print("Failed to load session. Exiting.")
                return
        else:
            # Start new session
            print("\nStarting new D&D session...")
            if not client.start_session(campaign_id, world_id):
                print("Failed to start session. Exiting.")
                return
    else:
        # No existing sessions, start new one
        print("\nNo existing sessions found. Starting new D&D session...")
        if not client.start_session(campaign_id, world_id):
            print("Failed to start session. Exiting.")
            return

    print("\nWelcome to the D&D AI DM! Type 'quit' or 'exit' to end the session.")
    print("Session started. You can begin your adventure!\n")

    # Main chat loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                break
            
            response = client.send_message(user_input)
            if response:
                print(f"\nDM: {response}")
        except KeyboardInterrupt:
            print("\nReceived interrupt signal. Ending session...")
            break
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            print("Ending session...")
            break

    # End session and show recap
    print("\nEnding session...")
    recap = client.end_session()
    if recap:
        print("\nSession Recap:")
        print(recap)

if __name__ == "__main__":
    main() 