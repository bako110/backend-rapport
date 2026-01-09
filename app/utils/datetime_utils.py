from datetime import datetime, timedelta
import pytz
import re
from typing import List, Optional
from app.core.config import settings


def get_ouagadougou_timezone():
    """Obtenir le fuseau horaire de Ouagadougou"""
    return pytz.timezone(settings.timezone)


def get_current_time_ouagadougou():
    """Obtenir l'heure actuelle à Ouagadougou"""
    tz = get_ouagadougou_timezone()
    return datetime.now(tz)


def iso_week_to_date_range(week_iso: str) -> tuple[datetime, datetime]:
    """Convertir une semaine ISO en plage de dates"""
    # Format: YYYY-Www (ex: 2024-W01)
    year, week = week_iso.split('-W')
    year = int(year)
    week = int(week)
    
    # Premier jour de l'année
    jan_1 = datetime(year, 1, 1)
    
    # Trouver le premier lundi de l'année
    days_to_monday = (7 - jan_1.weekday()) % 7
    if jan_1.weekday() > 3:  # Si le 1er janvier est jeudi ou après
        days_to_monday += 7
    
    first_monday = jan_1 + timedelta(days=days_to_monday)
    
    # Calculer le début de la semaine demandée
    week_start = first_monday + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end


def date_to_iso_week(date: datetime) -> str:
    """Convertir une date en semaine ISO"""
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def get_current_iso_week() -> str:
    """Obtenir la semaine ISO actuelle"""
    now = get_current_time_ouagadougou()
    return date_to_iso_week(now)


def validate_iso_week_format(week_iso: str) -> bool:
    """Valider le format d'une semaine ISO"""
    pattern = r'^\d{4}-W\d{2}$'
    return bool(re.match(pattern, week_iso))


def get_week_range(start_week: str, end_week: str) -> List[str]:
    """Obtenir toutes les semaines entre deux semaines ISO"""
    if not validate_iso_week_format(start_week) or not validate_iso_week_format(end_week):
        raise ValueError("Format de semaine invalide")
    
    weeks = []
    current_week = start_week
    
    while current_week <= end_week:
        weeks.append(current_week)
        
        # Passer à la semaine suivante
        year, week = current_week.split('-W')
        year = int(year)
        week = int(week)
        
        if week == 52:  # Dernière semaine de l'année
            current_week = f"{year + 1}-W01"
        else:
            current_week = f"{year}-W{week + 1:02d}"
    
    return weeks


def format_datetime_for_display(dt: datetime) -> str:
    """Formatter une datetime pour l'affichage"""
    tz = get_ouagadougou_timezone()
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%d/%m/%Y %H:%M")


def truncate_text(text: str, max_length: int = 100) -> str:
    """Tronquer un texte à une longueur maximale"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."