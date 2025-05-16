from datetime import datetime
from enum import Enum
import os, json, uuid
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from .sql_db import DBLog


class FileType(Enum):
    JSON = "json"
    TXT = "txt"


class StudioLogger:
    def __init__(self):
        os.makedirs("./logs/txt", exist_ok=True)
        os.makedirs("./logs/json", exist_ok=True)

    def _get_file_path(self, type: FileType, date_string: str):
        return f"./logs/{type.value}/{date_string}.{type.value}"

    def _log_to_json(self, log: DBLog):
        file_path = self._get_file_path(
            FileType.JSON, date_string=datetime.now().strftime("%d-%m-%Y")
        )

        json_entry = {
            "id": log.id,
            "user": log.user_input,
            "assistant": log.model_input,
            "timestamp": log.timestamp,
        }

        if os.path.exists(file_path):
            with open(file_path, "r+") as file:
                json_logs = json.load(file)
                json_logs.append(json_entry)
                file.seek(0)
                json.dump(obj=json_logs, fp=file, indent=2)
        else:
            with open(file_path, "w") as file:
                json.dump([json_entry], file)

    def _log_to_txt(self, log: DBLog):
        file_path = self._get_file_path(
            FileType.TXT, date_string=datetime.now().strftime("%d-%m-%Y")
        )

        with open(file_path, "a") as file:
            file.write(f"[ID]: {str(log.id)}\n")
            file.write(f"[TS]: {log.timestamp}\n")
            file.write(f"[USER]: {log.user_input}\n")
            file.write(f"[ASSISTANT]: {log.model_input}\n\n")

    def log_interaction(self, user_input: str, model_input: str):
        log = DBLog(
            user_input=user_input,
            model_input=model_input,
            timestamp=datetime.now().isoformat(),
            id=str(uuid.uuid4()),
        )

        self._log_to_txt(log)
        self._log_to_json(log)
