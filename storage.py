import json
import os
from typing import Dict, Any


class Storage:
    def __init__(self, filename="data/users.json"):
        self.filename = filename
        self._ensure_directory()
        self._ensure_file()

    def _ensure_directory(self):
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

    def _ensure_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def load_all_users(self) -> Dict[str, Any]:
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_all_users(self, data: Dict[str, Any]):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user(self, user_id: str) -> Dict[str, Any]:
        users = self.load_all_users()
        user_data = users.get(str(user_id))

        if not user_data:
            # Создаем нового пользователя с дефолтными значениями
            user_data = self._create_default_user(user_id)
            users[str(user_id)] = user_data
            self.save_all_users(users)

        return user_data

    def _create_default_user(self, user_id: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "user_name": "",
            "current_scene": "start",
            "inventory": [],
            "money": 1500,
            "health": 100,
            "points": 0,
            "has_talked_stalker": False,
            "has_found_key": False,
            "has_door_open": False,
            "has_killed": False,
            "has_found_doc": False
        }

    def update_user(self, user_id: str, updates: Dict[str, Any]):
        users = self.load_all_users()
        user_id_str = str(user_id)

        if user_id_str not in users:
            users[user_id_str] = self._create_default_user(user_id_str)

        user_data = users[user_id_str]

        # Для вложенных структур нужно обновлять корректно
        for key, value in updates.items():
            if key == "inventory" and isinstance(value, list):
                user_data[key] = value
            elif key == "equipment" and isinstance(value, dict):
                if "equipment" not in user_data:
                    user_data["equipment"] = {}
                user_data["equipment"].update(value)
            else:
                user_data[key] = value

        self.save_all_users(users)

    def add_item(self, user_id: str, item_id: str):
        user = self.get_user(user_id)
        if item_id not in user["inventory"]:
            user["inventory"].append(item_id)
            self.update_user(user_id, {"inventory": user["inventory"]})

    def remove_item(self, user_id: str, item_id: str):
        user = self.get_user(user_id)
        if item_id in user["inventory"]:
            user["inventory"].remove(item_id)
            self.update_user(user_id, {"inventory": user["inventory"]})