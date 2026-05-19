import json
import os
from typing import Dict, List
from datetime import datetime

class Database:
    """User Management Database"""
    
    def __init__(self):
        self.db_file = "users.json"
        self.users = self.load()
    
    def load(self) -> Dict:
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure all keys exist
                    for key in ["admins", "approved", "pending", "blocked", "users_info", "check_history", "broadcast_history"]:
                        if key not in data:
                            data[key] = [] if key != "users_info" else {}
                    return data
            except:
                pass
        return {
            "admins": [],
            "approved": [],
            "pending": [],
            "blocked": [],
            "users_info": {},
            "check_history": [],
            "broadcast_history": []
        }
    
    def save(self):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Database save error: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        return str(user_id) in self.users["admins"]
    
    def is_approved(self, user_id: int) -> bool:
        return str(user_id) in self.users["approved"]
    
    def is_pending(self, user_id: int) -> bool:
        return str(user_id) in self.users["pending"]
    
    def is_blocked(self, user_id: int) -> bool:
        return str(user_id) in self.users["blocked"]
    
    def add_admin(self, user_id: int):
        uid = str(user_id)
        if uid not in self.users["admins"]:
            self.users["admins"].append(uid)
            if uid not in self.users["approved"]:
                self.users["approved"].append(uid)
            self.users["users_info"][uid] = {
                "id": user_id,
                "username": "Admin",
                "first_name": "Admin",
                "last_name": "",
                "requested_at": datetime.now().isoformat(),
                "approved_at": datetime.now().isoformat(),
                "approved_by": "system",
                "total_checks": 0,
                "total_approved": 0
            }
            self.save()
    
    def add_pending(self, user_id: int, user_info: Dict):
        uid = str(user_id)
        if uid not in self.users["pending"] and uid not in self.users["approved"] and uid not in self.users["blocked"]:
            self.users["pending"].append(uid)
            self.users["users_info"][uid] = {
                "id": user_id,
                "username": user_info.get("username", ""),
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
                "requested_at": datetime.now().isoformat(),
                "approved_at": None,
                "approved_by": None,
                "total_checks": 0,
                "total_approved": 0
            }
            self.save()
    
    def approve_user(self, user_id: int, approved_by: int) -> bool:
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
        uid = str(user_id)
        if uid in self.users["pending"]:
            self.users["pending"].remove(uid)
            if uid in self.users["users_info"]:
                del self.users["users_info"][uid]
            self.save()
    
    def block_user(self, user_id: int):
        uid = str(user_id)
        if uid not in self.users["blocked"]:
            self.users["blocked"].append(uid)
            if uid in self.users["approved"]:
                self.users["approved"].remove(uid)
            if uid in self.users["pending"]:
                self.users["pending"].remove(uid)
            self.save()
    
    def unblock_user(self, user_id: int):
        uid = str(user_id)
        if uid in self.users["blocked"]:
            self.users["blocked"].remove(uid)
            self.save()
    
    def remove_user(self, user_id: int):
        uid = str(user_id)
        for key in ["approved", "pending", "blocked"]:
            if uid in self.users[key]:
                self.users[key].remove(uid)
        if uid in self.users["users_info"]:
            del self.users["users_info"][uid]
        self.save()
    
    def get_pending_users(self) -> List[Dict]:
        pending = []
        for uid in self.users["pending"]:
            if uid in self.users["users_info"]:
                pending.append(self.users["users_info"][uid])
        return pending
    
    def get_approved_users(self) -> List[Dict]:
        approved = []
        for uid in self.users["approved"]:
            if uid in self.users["users_info"]:
                approved.append(self.users["users_info"][uid])
        return approved
    
    def get_blocked_users(self) -> List[Dict]:
        blocked = []
        for uid in self.users["blocked"]:
            if uid in self.users["users_info"]:
                blocked.append(self.users["users_info"][uid])
        return blocked
    
    def get_all_users(self) -> List[Dict]:
        return list(self.users["users_info"].values())
    
    def get_stats(self) -> Dict:
        return {
            "total_users": len(self.users["users_info"]),
            "approved_users": len(self.users["approved"]),
            "pending_users": len(self.users["pending"]),
            "blocked_users": len(self.users["blocked"]),
            "total_checks": len(self.users.get("check_history", [])),
            "broadcasts": len(self.users.get("broadcast_history", []))
        }
    
    def add_check_history(self, user_id: int, card: str, status: str, gateway: str):
        self.users["check_history"].append({
            "user_id": str(user_id),
            "timestamp": datetime.now().isoformat(),
            "card": card,
            "status": status,
            "gateway": gateway
        })
        if len(self.users["check_history"]) > 1000:
            self.users["check_history"] = self.users["check_history"][-1000:]
        self.save()
    
    def add_broadcast(self, message: str, sent_to: int):
        self.users["broadcast_history"].append({
            "message": message[:100],
            "sent_to": sent_to,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.users["broadcast_history"]) > 100:
            self.users["broadcast_history"] = self.users["broadcast_history"][-100:]
        self.save()
    
    def update_user_stats(self, user_id: int, approved_count: int = 0):
        uid = str(user_id)
        if uid in self.users["users_info"]:
            self.users["users_info"][uid]["total_checks"] = self.users["users_info"][uid].get("total_checks", 0) + 1
            if approved_count > 0:
                self.users["users_info"][uid]["total_approved"] = self.users["users_info"][uid].get("total_approved", 0) + approved_count
            self.save()
