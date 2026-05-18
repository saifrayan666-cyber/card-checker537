import json
import os
from typing import Dict, List
from datetime import datetime

class Database:
    """Simple JSON-based database for user management"""
    
    def __init__(self):
        self.db_file = "users.json"
        self.users = self.load()
    
    def load(self) -> Dict:
        """Load database from file"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "admins": [],        # Admin user IDs
            "approved": [],      # Approved user IDs
            "pending": [],       # Pending approval user IDs
            "blocked": [],       # Blocked user IDs
            "users_info": {}     # User details {user_id: {name, username, joined, approved_by}}
        }
    
    def save(self):
        """Save database to file"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return str(user_id) in self.users["admins"]
    
    def is_approved(self, user_id: int) -> bool:
        """Check if user is approved"""
        return str(user_id) in self.users["approved"]
    
    def is_pending(self, user_id: int) -> bool:
        """Check if user is pending"""
        return str(user_id) in self.users["pending"]
    
    def is_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return str(user_id) in self.users["blocked"]
    
    def add_admin(self, user_id: int):
        """Add admin"""
        uid = str(user_id)
        if uid not in self.users["admins"]:
            self.users["admins"].append(uid)
            if uid not in self.users["approved"]:
                self.users["approved"].append(uid)
            self.save()
    
    def add_pending(self, user_id: int, user_info: Dict):
        """Add user to pending list"""
        uid = str(user_id)
        if uid not in self.users["pending"]:
            self.users["pending"].append(uid)
            self.users["users_info"][uid] = {
                "id": user_id,
                "username": user_info.get("username", ""),
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
                "requested_at": datetime.now().isoformat(),
                "approved_at": None,
                "approved_by": None
            }
            self.save()
    
    def approve_user(self, user_id: int, approved_by: int) -> bool:
        """Approve a pending user"""
        uid = str(user_id)
        if uid in self.users["pending"]:
            self.users["pending"].remove(uid)
            if uid not in self.users["approved"]:
                self.users["approved"].append(uid)
                if uid in self.users["users_info"]:
                    self.users["users_info"][uid]["approved_at"] = datetime.now().isoformat()
                    self.users["users_info"][uid]["approved_by"] = str(approved_by)
            self.save()
            return True
        return False
    
    def reject_user(self, user_id: int):
        """Reject a pending user"""
        uid = str(user_id)
        if uid in self.users["pending"]:
            self.users["pending"].remove(uid)
            if uid in self.users["users_info"]:
                del self.users["users_info"][uid]
            self.save()
    
    def block_user(self, user_id: int):
        """Block a user"""
        uid = str(user_id)
        if uid not in self.users["blocked"]:
            self.users["blocked"].append(uid)
            if uid in self.users["approved"]:
                self.users["approved"].remove(uid)
            if uid in self.users["pending"]:
                self.users["pending"].remove(uid)
            self.save()
    
    def unblock_user(self, user_id: int):
        """Unblock a user"""
        uid = str(user_id)
        if uid in self.users["blocked"]:
            self.users["blocked"].remove(uid)
            self.save()
    
    def get_pending_users(self) -> List[Dict]:
        """Get list of pending users"""
        pending = []
        for uid in self.users["pending"]:
            if uid in self.users["users_info"]:
                pending.append(self.users["users_info"][uid])
        return pending
    
    def get_approved_users(self) -> List[Dict]:
        """Get list of approved users"""
        approved = []
        for uid in self.users["approved"]:
            if uid in self.users["users_info"]:
                approved.append(self.users["users_info"][uid])
        return approved
    
    def get_user_info(self, user_id: int) -> Dict:
        """Get user info"""
        return self.users["users_info"].get(str(user_id), {})