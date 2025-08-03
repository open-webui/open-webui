"""
Polish Holiday Calendar for NBP Exchange Rate Integration

Provides accurate Polish public holiday information to handle NBP non-publication days.
Based on official Polish holiday calendar.
"""

import logging
from datetime import date, timedelta
from typing import Set, Dict, List

log = logging.getLogger(__name__)

class PolishHolidayCalendar:
    """Polish public holiday calendar with accurate holiday data"""
    
    # Official Polish holidays for 2025
    HOLIDAYS_2025 = {
        date(2025, 1, 1): "Nowy Rok, Świętej Bożej Rodzicielki Maryi",
        date(2025, 1, 6): "Trzech Króli (Objawienie Pańskie)", 
        date(2025, 4, 20): "Wielkanoc",
        date(2025, 4, 21): "Poniedziałek Wielkanocny",
        date(2025, 5, 1): "Święto Pracy",
        date(2025, 5, 3): "Święto Konstytucji 3 Maja",
        date(2025, 6, 8): "Zesłanie Ducha Świętego (Zielone Świątki)",
        date(2025, 6, 19): "Boże Ciało",
        date(2025, 8, 15): "Święto Wojska Polskiego, Wniebowzięcie Najświętszej Maryi Panny",
        date(2025, 11, 1): "Wszystkich Świętych",
        date(2025, 11, 11): "Święto Niepodległości",
        date(2025, 12, 24): "Wigilia Bożego Narodzenia",
        date(2025, 12, 25): "Boże Narodzenie (pierwszy dzień)",
        date(2025, 12, 26): "Boże Narodzenie (drugi dzień)"
    }
    
    # Template for recurring fixed holidays (month, day)
    FIXED_HOLIDAYS = {
        (1, 1): "Nowy Rok",
        (1, 6): "Trzech Króli", 
        (5, 1): "Święto Pracy",
        (5, 3): "Święto Konstytucji 3 Maja",
        (8, 15): "Wniebowzięcie Najświętszej Maryi Panny",
        (11, 1): "Wszystkich Świętych",
        (11, 11): "Święto Niepodległości",
        (12, 24): "Wigilia Bożego Narodzenia",
        (12, 25): "Boże Narodzenie (pierwszy dzień)",
        (12, 26): "Boże Narodzenie (drugi dzień)"
    }
    
    def __init__(self):
        self._all_holidays = self.HOLIDAYS_2025.copy()
    
    def is_holiday(self, check_date: date) -> bool:
        """Check if a given date is a Polish public holiday"""
        # For 2025, use exact holiday data
        if check_date.year == 2025:
            return check_date in self.HOLIDAYS_2025
        
        # For other years, use fixed holidays (approximation)
        month_day = (check_date.month, check_date.day)
        return month_day in self.FIXED_HOLIDAYS
    
    def is_working_day(self, check_date: date) -> bool:
        """Check if a date is a working day (not weekend, not holiday)"""
        return (check_date.weekday() < 5 and  # Not weekend (Mon=0, Sun=6)
                not self.is_holiday(check_date))
    
    def get_last_working_day_before(self, target_date: date, max_days_back: int = 10) -> date:
        """
        Find the last working day before the target date.
        Handles weekends, holidays, and extended holiday periods.
        
        Args:
            target_date: The date to work backwards from
            max_days_back: Maximum number of days to search backwards
            
        Returns:
            The last working day before target_date
        """
        current_date = target_date - timedelta(days=1)
        days_checked = 0
        
        while days_checked < max_days_back:
            if self.is_working_day(current_date):
                log.debug(f"Last working day before {target_date}: {current_date}")
                return current_date
            
            current_date -= timedelta(days=1)
            days_checked += 1
        
        # Fallback: if we can't find a working day, return the furthest date checked
        log.warning(f"Could not find working day within {max_days_back} days before {target_date}")
        return current_date
    
    def get_next_working_day_after(self, target_date: date, max_days_forward: int = 10) -> date:
        """
        Find the next working day after the target date.
        
        Args:
            target_date: The date to work forwards from
            max_days_forward: Maximum number of days to search forward
            
        Returns:
            The next working day after target_date
        """
        current_date = target_date + timedelta(days=1)
        days_checked = 0
        
        while days_checked < max_days_forward:
            if self.is_working_day(current_date):
                log.debug(f"Next working day after {target_date}: {current_date}")
                return current_date
            
            current_date += timedelta(days=1)
            days_checked += 1
        
        # Fallback: if we can't find a working day, return the furthest date checked
        log.warning(f"Could not find working day within {max_days_forward} days after {target_date}")
        return current_date
    
    def get_holiday_name(self, check_date: date) -> str:
        """Get the name of the holiday for a given date"""
        if check_date.year == 2025 and check_date in self.HOLIDAYS_2025:
            return self.HOLIDAYS_2025[check_date]
        
        # For other years, return generic names
        month_day = (check_date.month, check_date.day)
        if month_day in self.FIXED_HOLIDAYS:
            return self.FIXED_HOLIDAYS[month_day]
        
        return "Unknown Holiday"
    
    def get_working_days_in_range(self, start_date: date, end_date: date) -> List[date]:
        """Get all working days in a date range"""
        working_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_working_day(current_date):
                working_days.append(current_date)
            current_date += timedelta(days=1)
        
        return working_days
    
    def get_upcoming_holidays(self, start_date: date, days_ahead: int = 30) -> List[Dict[str, any]]:
        """Get list of upcoming holidays within specified days"""
        upcoming = []
        current_date = start_date
        end_date = start_date + timedelta(days=days_ahead)
        
        while current_date <= end_date:
            if self.is_holiday(current_date):
                upcoming.append({
                    'date': current_date,
                    'name': self.get_holiday_name(current_date),
                    'weekday': current_date.strftime('%A'),
                    'is_weekend': current_date.weekday() >= 5
                })
            current_date += timedelta(days=1)
        
        return upcoming
    
    def get_nbp_rate_strategy(self, target_date: date) -> Dict[str, any]:
        """
        Get the recommended strategy for fetching NBP rates for a given date.
        Returns information about whether to expect data and what fallback to use.
        """
        today = date.today()
        weekday = target_date.weekday()
        
        strategy = {
            'target_date': target_date,
            'is_working_day': self.is_working_day(target_date),
            'is_weekend': weekday >= 5,
            'is_holiday': self.is_holiday(target_date),
            'expect_nbp_data': False,
            'fallback_date': None,
            'reason': ''
        }
        
        if self.is_working_day(target_date):
            strategy['expect_nbp_data'] = True
            strategy['reason'] = 'Working day - NBP should publish data'
        elif weekday >= 5:  # Weekend
            strategy['reason'] = 'Weekend - NBP does not publish'
            strategy['fallback_date'] = self.get_last_working_day_before(target_date)
        elif self.is_holiday(target_date):
            holiday_name = self.get_holiday_name(target_date)
            strategy['reason'] = f'Polish holiday: {holiday_name}'
            strategy['fallback_date'] = self.get_last_working_day_before(target_date)
        else:
            strategy['reason'] = 'Unknown non-working day'
            strategy['fallback_date'] = self.get_last_working_day_before(target_date)
        
        return strategy
    
    def debug_holiday_period(self, start_date: date, end_date: date) -> None:
        """Debug helper to analyze a holiday period"""
        print(f"\nHoliday Analysis: {start_date} to {end_date}")
        print("=" * 50)
        
        current = start_date
        while current <= end_date:
            day_type = "WORKING"
            if current.weekday() >= 5:
                day_type = "WEEKEND"
            elif self.is_holiday(current):
                day_type = f"HOLIDAY ({self.get_holiday_name(current)})"
            
            print(f"{current} ({current.strftime('%A')}) - {day_type}")
            current += timedelta(days=1)


# Global singleton instance
polish_holidays = PolishHolidayCalendar()