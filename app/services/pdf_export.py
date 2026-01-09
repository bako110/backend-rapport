from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
from typing import List, Dict, Any
from datetime import datetime
from app.utils.datetime_utils import format_datetime_for_display


class PDFExportService:
    """Service pour l'export PDF des rapports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle', 
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=12
        )
    
    def export_reports_to_pdf(self, reports: List[Dict[str, Any]], title: str = "Rapports Hebdomadaires") -> io.BytesIO:
        """
        Exporter les rapports vers un fichier PDF
        
        Args:
            reports: Liste des rapports à exporter
            title: Titre du document
            
        Returns:
            BytesIO contenant le PDF
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Construire le contenu
        story = []
        
        # Titre
        story.append(Paragraph(title, self.title_style))
        story.append(Paragraph(f"Généré le {format_datetime_for_display(datetime.utcnow())}", self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        if not reports:
            story.append(Paragraph("Aucun rapport trouvé pour les critères sélectionnés.", self.styles['Normal']))
        else:
            # Résumé
            total_reports = len(reports)
            total_hours = sum(report['total_hours'] for report in reports)
            unique_employees = len(set(report.get('user_name', '') for report in reports))
            
            summary_data = [
                ['Nombre de rapports:', str(total_reports)],
                ['Total des heures:', f"{total_hours:.1f}h"],
                ['Employés ayant reporté:', str(unique_employees)]
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 1*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(Paragraph("Résumé", self.subtitle_style))
            story.append(summary_table)
            story.append(Spacer(1, 24))
            
            # Détail des rapports
            story.append(Paragraph("Détail des Rapports", self.subtitle_style))
            
            # En-têtes du tableau
            data = [['Semaine', 'Employé', 'Tâches', 'Heures', 'Date']]
            
            for report in reports:
                # Première ligne avec infos principales
                tasks_summary = f"{len(report.get('tasks', []))} tâche(s)"
                data.append([
                    report['week_iso'],
                    report.get('user_name', '')[:20],  # Limiter la longueur
                    tasks_summary,
                    f"{report['total_hours']:.1f}h",
                    format_datetime_for_display(report['created_at'])[:10]  # Date seulement
                ])
                
                # Ligne pour les tâches si demandé
                if report.get('tasks'):
                    for i, task in enumerate(report['tasks'][:3]):  # Limiter à 3 tâches
                        task_info = f"• {task.get('title', '')} ({task.get('hours', 0)}h)"
                        if len(task_info) > 40:
                            task_info = task_info[:37] + "..."
                        data.append(['', '', task_info, '', ''])
                    
                    if len(report['tasks']) > 3:
                        data.append(['', '', f"... et {len(report['tasks']) - 3} autre(s)", '', ''])
            
            # Créer le tableau
            table = Table(data, colWidths=[1*inch, 1.5*inch, 2.5*inch, 0.8*inch, 1*inch])
            table.setStyle(TableStyle([
                # En-tête
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                
                # Contenu
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Colonne heures centrée
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                
                # Alternance des couleurs
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(table)
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def export_weekly_summary_to_pdf(self, week_stats: Dict[str, Any], reports: List[Dict[str, Any]]) -> io.BytesIO:
        """Exporter un résumé hebdomadaire en PDF"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        story = []
        
        # Titre
        week_iso = week_stats.get('week_iso', 'Semaine inconnue')
        story.append(Paragraph(f"Résumé Hebdomadaire - {week_iso}", self.title_style))
        story.append(Spacer(1, 12))
        
        # Statistiques générales
        stats_data = [
            ['Nombre de rapports:', str(week_stats.get('total_reports', 0))],
            ['Total des heures:', f"{week_stats.get('total_hours', 0):.1f}h"],
            ['Employés ayant reporté:', str(week_stats.get('employees_reported', 0))],
            ['Moyenne heures/employé:', f"{week_stats.get('average_hours_per_employee', 0):.1f}h"]
        ]
        
        stats_table = Table(stats_data, colWidths=[2.5*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("Statistiques", self.subtitle_style))
        story.append(stats_table)
        story.append(Spacer(1, 24))
        
        # Détail par employé
        if reports:
            story.append(Paragraph("Détail par Employé", self.subtitle_style))
            
            # Grouper par employé
            employee_reports = {}
            for report in reports:
                employee_name = report.get('user_name', 'Inconnu')
                if employee_name not in employee_reports:
                    employee_reports[employee_name] = []
                employee_reports[employee_name].append(report)
            
            for employee, emp_reports in employee_reports.items():
                total_emp_hours = sum(r['total_hours'] for r in emp_reports)
                
                story.append(Paragraph(f"{employee} - {total_emp_hours:.1f}h", self.styles['Heading3']))
                
                # Tableau des tâches pour cet employé
                task_data = [['Tâche', 'Heures', 'Projet', 'Notes']]
                
                for report in emp_reports:
                    for task in report.get('tasks', []):
                        task_data.append([
                            task.get('title', '')[:30],
                            f"{task.get('hours', 0):.1f}h",
                            task.get('project', '')[:15],
                            task.get('notes', '')[:20]
                        ])
                
                task_table = Table(task_data, colWidths=[2.5*inch, 0.8*inch, 1*inch, 1.5*inch])
                task_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
                ]))
                
                story.append(task_table)
                story.append(Spacer(1, 12))
        
        doc.build(story)
        buffer.seek(0)
        return buffer