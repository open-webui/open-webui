from pydantic import BaseModel
from typing import List, Union, Optional
from peewee import *
from playhouse.shortcuts import model_to_dict

import json
import uuid
import time

from apps.web.internal.db import DB

####################
# Admin Settings DB Schema
####################


class AdminSetting(Model):
    name = CharField(max_length=255)
    value = TextField()

    class Meta:
        database = DB
        table_name = 'admin_settings'


class AdminSettingsModel(BaseModel):
    name: str
    value: str


####################
# Forms
####################


class AdminSettingsTable:
    def __init__(self, db):
        self.db = db
        db.create_tables([AdminSetting])

    def save_settings(self, settings: List[AdminSettingsModel]) -> List[AdminSettingsModel]:
        saved_settings = []

        for setting in settings:
            try:
                # Try to find existing setting by name
                existing_setting = AdminSetting.get(AdminSetting.name == setting.name)
                print("Setting found: ", existing_setting.name)

                # Update the existing setting's value
                existing_setting.value = setting.value
                existing_setting.save()
                saved_settings.append(setting)
            except AdminSetting.DoesNotExist:
                # Setting doesn't exist, create a new record
                new_setting = AdminSetting.create(name=setting.name, value=setting.value)
                saved_settings.append(setting)

        return saved_settings
    
    def get_settings(self, setting_names: List[str]) -> dict:
        settings_dict = {}
    
        try:
            settings = AdminSetting.select().where(AdminSetting.name.in_(setting_names))
            for setting in settings:
                settings_dict[setting.name] = setting.value
        except Exception as e:
            print(f"Error retrieving settings: {e}")
            # You can handle or log the error here

        return settings_dict


AdminSettings = AdminSettingsTable(DB)
