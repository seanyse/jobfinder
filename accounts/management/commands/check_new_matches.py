"""
Management command to check for new candidate matches in saved searches
and send notifications to recruiters.

Run this command periodically (e.g., via cron) to check for new matches.
Example: python manage.py check_new_matches
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from django.urls import reverse
from accounts.models import SavedCandidateSearch, SearchMatchNotification, Profile
from accounts.views import _execute_saved_search_query
from django.db.models import Q


class Command(BaseCommand):
    help = 'Check for new candidate matches in saved searches and notify recruiters'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending emails or creating notifications',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all active saved searches
        active_searches = SavedCandidateSearch.objects.filter(is_active=True)
        
        if not active_searches.exists():
            self.stdout.write(self.style.WARNING('No active saved searches found.'))
            return
        
        total_new_matches = 0
        total_notifications_sent = 0
        
        for saved_search in active_searches:
            self.stdout.write(f'\nChecking search: "{saved_search.name}" (ID: {saved_search.id})')
            
            # Execute the search query
            matches = _execute_saved_search_query(saved_search)
            
            # Get list of already notified candidates
            notified_candidate_ids = SearchMatchNotification.objects.filter(
                saved_search=saved_search
            ).values_list('candidate_id', flat=True)
            
            # Find new matches (candidates not yet notified)
            new_matches = matches.exclude(user_id__in=notified_candidate_ids)
            new_match_count = new_matches.count()
            
            if new_match_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'  Found {new_match_count} new match(es)')
                )
                total_new_matches += new_match_count
                
                # Create notification records and send email
                if not dry_run:
                    # Create notification records for all new matches
                    notifications_created = 0
                    for match in new_matches:
                        SearchMatchNotification.objects.get_or_create(
                            saved_search=saved_search,
                            candidate=match.user
                        )
                        notifications_created += 1
                    
                    # Send email notification to recruiter
                    if saved_search.recruiter.email:
                        try:
                            self._send_notification_email(saved_search, new_match_count, new_matches)
                            total_notifications_sent += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  Email notification sent to {saved_search.recruiter.email}')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'  Failed to send email: {str(e)}')
                            )
                    
                    # Update last_checked timestamp
                    saved_search.last_checked = timezone.now()
                    saved_search.save(update_fields=['last_checked'])
                    
                    self.stdout.write(f'  Created {notifications_created} notification record(s)')
                else:
                    self.stdout.write(self.style.WARNING('  DRY RUN: Would create notifications and send email'))
            else:
                self.stdout.write('  No new matches found')
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(f'  Total new matches found: {total_new_matches}')
        if not dry_run:
            self.stdout.write(f'  Email notifications sent: {total_notifications_sent}')
        else:
            self.stdout.write(self.style.WARNING('  DRY RUN: No emails sent'))

    def _send_notification_email(self, saved_search, match_count, new_matches):
        """Send email notification to recruiter about new matches"""
        recruiter = saved_search.recruiter
        search_name = saved_search.name
        
        # Build email subject
        subject = f'[JobFinder] New matches for your saved search: {search_name}'
        
        # Build email body
        body_lines = [
            f'Hello {recruiter.get_full_name() or recruiter.username},',
            '',
            f'We found {match_count} new candidate(s) matching your saved search "{search_name}".',
            '',
            'New matches:',
        ]
        
        # List first 10 matches
        for i, match in enumerate(new_matches[:10], 1):
            profile = match
            body_lines.append(
                f'{i}. {profile.user.username} - {profile.headline}'
            )
            if profile.location:
                body_lines.append(f'   Location: {profile.location}')
            if profile.skills.exists():
                skills_list = ', '.join([s.name for s in profile.skills.all()[:5]])
                body_lines.append(f'   Skills: {skills_list}')
            body_lines.append('')
        
        if match_count > 10:
            body_lines.append(f'... and {match_count - 10} more match(es)')
            body_lines.append('')
        
        # Generate URL for the saved search detail page
        search_url_path = reverse('accounts.saved_search_detail', args=[saved_search.id])
        # Get base URL from settings or use default
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        if not base_url.endswith('/'):
            base_url += '/'
        if search_url_path.startswith('/'):
            search_url_path = search_url_path[1:]
        search_url = f'{base_url}{search_url_path}'
        
        body_lines.extend([
            'View all matches:',
            search_url,
            '',
            '---',
            'JobFinder',
        ])
        
        body = '\n'.join(body_lines)
        
        # Try to send email
        try:
            EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                to=[recruiter.email],
            ).send(fail_silently=False)
        except Exception as e:
            # Fallback to console backend
            conn = get_connection('django.core.mail.backends.console.EmailBackend')
            EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                to=[recruiter.email],
                connection=conn,
            ).send(fail_silently=True)
            raise e

