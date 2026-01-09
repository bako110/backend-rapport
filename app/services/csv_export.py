import csv
import io
from typing import List, Dict, Any
from datetime import datetime
from app.utils.datetime_utils import format_datetime_for_display


class CSVExportService:
    """Service pour l'export CSV des rapports"""
    
    @staticmethod
    def export_reports_to_csv(reports: List[Dict[str, Any]], include_tasks_detail: bool = True) -> io.StringIO:
        """
        Exporter les rapports vers un fichier CSV
        
        Args:
            reports: Liste des rapports à exporter
            include_tasks_detail: Inclure le détail des tâches ou seulement le résumé
            
        Returns:
            StringIO contenant le CSV
        """
        output = io.StringIO()
        
        if include_tasks_detail:
            # Export détaillé avec une ligne par tâche
            fieldnames = [
                'Semaine ISO',
                'Nom Employé', 
                'Email Employé',
                'Tâche',
                'Heures',
                'Notes Tâche',
                'Projet',
                'Difficultés',
                'Remarques',
                'Total Heures Rapport',
                'Date Création',
                'Date Mise à jour'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quotechar='"')
            writer.writeheader()
            
            for report in reports:
                base_row = {
                    'Semaine ISO': report['week_iso'],
                    'Nom Employé': report.get('user_name', ''),
                    'Email Employé': report.get('user_email', ''),
                    'Difficultés': report.get('difficulties', ''),
                    'Remarques': report.get('remarks', ''),
                    'Total Heures Rapport': report['total_hours'],
                    'Date Création': format_datetime_for_display(report['created_at']),
                    'Date Mise à jour': format_datetime_for_display(report['updated_at'])
                }
                
                # Une ligne par tâche
                for task in report.get('tasks', []):
                    row = base_row.copy()
                    row.update({
                        'Tâche': task.get('title', ''),
                        'Heures': task.get('hours', 0),
                        'Notes Tâche': task.get('notes', ''),
                        'Projet': task.get('project', '')
                    })
                    writer.writerow(row)
        else:
            # Export résumé avec une ligne par rapport
            fieldnames = [
                'Semaine ISO',
                'Nom Employé',
                'Email Employé', 
                'Nombre Tâches',
                'Total Heures',
                'Difficultés',
                'Remarques',
                'Date Création',
                'Date Mise à jour'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quotechar='"')
            writer.writeheader()
            
            for report in reports:
                writer.writerow({
                    'Semaine ISO': report['week_iso'],
                    'Nom Employé': report.get('user_name', ''),
                    'Email Employé': report.get('user_email', ''),
                    'Nombre Tâches': len(report.get('tasks', [])),
                    'Total Heures': report['total_hours'],
                    'Difficultés': report.get('difficulties', ''),
                    'Remarques': report.get('remarks', ''),
                    'Date Création': format_datetime_for_display(report['created_at']),
                    'Date Mise à jour': format_datetime_for_display(report['updated_at'])
                })
        
        output.seek(0)
        return output
    
    @staticmethod
    def export_users_to_csv(users: List[Dict[str, Any]]) -> io.StringIO:
        """Exporter les utilisateurs vers un fichier CSV"""
        output = io.StringIO()
        
        fieldnames = [
            'Nom',
            'Email',
            'Rôle', 
            'Statut',
            'Date Création',
            'Date Mise à jour'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quotechar='"')
        writer.writeheader()
        
        for user in users:
            writer.writerow({
                'Nom': user['name'],
                'Email': user['email'],
                'Rôle': user['role'],
                'Statut': user['status'],
                'Date Création': format_datetime_for_display(user['created_at']),
                'Date Mise à jour': format_datetime_for_display(user['updated_at'])
            })
        
        output.seek(0)
        return output
    
    @staticmethod
    def export_messages_to_csv(messages: List[Dict[str, Any]]) -> io.StringIO:
        """Exporter les messages vers un fichier CSV"""
        output = io.StringIO()
        
        fieldnames = [
            'Expéditeur',
            'Destinataire',
            'Sujet',
            'Contenu',
            'Lu',
            'Date Lecture',
            'Date Envoi'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=';', quotechar='"')
        writer.writeheader()
        
        for message in messages:
            writer.writerow({
                'Expéditeur': message.get('sender_name', ''),
                'Destinataire': message.get('receiver_name', ''),
                'Sujet': message.get('subject', ''),
                'Contenu': message['content'],
                'Lu': 'Oui' if message['read_status'] else 'Non',
                'Date Lecture': format_datetime_for_display(message['read_at']) if message.get('read_at') else '',
                'Date Envoi': format_datetime_for_display(message['created_at'])
            })
        
        output.seek(0)
        return output