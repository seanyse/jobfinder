from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Case, When, IntegerField
from .models import Job, Application, SavedJob
from accounts.models import Profile
from django.http import JsonResponse
from django.views.decorators.http import require_GET

def is_seeker(user):
    return user.is_authenticated and getattr(user, "role", None) == "seeker"

@login_required
def index(request):
    jobs = Job.objects.all()
    filters = {}
    user_applications = []
    user_saved_jobs = []
    filter_applied = 0

    if request.user.role == 'seeker':
        # Apply filters for job seekers
        title = request.GET.get('title', '').strip()
        skills = request.GET.get('skills', '').strip()
        location = request.GET.get('location', '').strip()
        min_salary = request.GET.get('min_salary', '').strip()
        max_salary = request.GET.get('max_salary', '').strip()
        remote_or_on_site = request.GET.get('remote_or_on_site', '')
        visa_sponsorship = request.GET.get('visa_sponsorship', '')

        if title:
            jobs = jobs.filter(title__icontains=title)
        if skills:
            for skill in skills.split(','):
                skill = skill.strip()
                jobs = jobs.filter(skills__icontains=skill)
        if location:
            jobs = jobs.filter(location__icontains=location)
        if min_salary:
            jobs = jobs.filter(salary__gte=min_salary)
        if max_salary:
            jobs = jobs.filter(salary__lte=max_salary)
        if remote_or_on_site:
            jobs = jobs.filter(remote_or_on_site=remote_or_on_site)
        if visa_sponsorship:
            jobs = jobs.filter(visa_sponsorship=visa_sponsorship)

        filters = request.GET

        # Applications + saved
        user_applications = Application.objects.filter(
            applicant=request.user
        ).values_list('job_id', flat=True)

        user_saved_jobs = SavedJob.objects.filter(
            user=request.user
        ).values_list('job_id', flat=True)

        # Job Recommendation functionality
        recommended_jobs = []
        other_jobs = []
        # check if user created a profile
        try:
            user_profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            other_jobs = list(jobs)
        else:
            user_skills = {s.name.lower().strip() for s in user_profile.skills.all()}

            used_filters = any([
                title,
                skills,
                location,
                min_salary,
                max_salary,
                remote_or_on_site,
                visa_sponsorship,
            ])
            
            # if a filter is used then do not apply the recommendation job functionality
            if used_filters:
                filter_applied = 1
                other_jobs = list(jobs)
            else:
                for job in jobs:
                    job_skill_names = {
                        s.lower().strip()
                        for s in job.skills.split(",")
                        if s.strip() != ""
                    }

                    overlap = len(user_skills & job_skill_names)

                    if overlap >= 2:
                        recommended_jobs.append(job)
                    else:
                        other_jobs.append(job)

    elif request.user.role == 'recruiter':
        jobs = jobs.annotate(
            is_mine=Case(
                When(posted_by=request.user, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('is_mine', '-created_at')

        recommended_jobs = []
        other_jobs = list(jobs)

    template_data = {
        'title': 'Jobs',
        'filters': filters,
        'user_applications': user_applications,
        'user_saved_jobs': user_saved_jobs,
        'recommended_jobs': recommended_jobs,
        'other_jobs': other_jobs,
        'filter_applied': filter_applied,
    }
    return render(request, 'jobs/job_listings.html', {'template_data': template_data})


def is_recruiter(user):
    return user.is_authenticated and user.role == 'recruiter'



@login_required
@user_passes_test(is_recruiter)
def create_job(request):
    if request.method == 'POST':
        job = Job()
        job.title = request.POST.get('title')
        job.skills = request.POST.get('skills')
        job.salary = request.POST.get('salary') or None
        job.location = request.POST.get('location') or ''
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        job.latitude = lat or None
        job.longitude = lon or None

        job.remote_or_on_site = request.POST.get('remote_or_on_site')
        job.visa_sponsorship = request.POST.get('visa_sponsorship')
        job.posted_by = request.user
        job.save()
        messages.success(request, 'Job posted successfully!')
        return redirect('jobs.index')
@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.user != job.posted_by:
        messages.error(request, 'You can only edit your own job postings.')
        return redirect('jobs.index')

    if request.method == 'GET':
        template_data = {}
        template_data['title'] = 'Edit Job'
        template_data['job'] = job
        return render(request, 'jobs/edit_job.html',
                      {'template_data': template_data})

    elif request.method == 'POST':
        job.title = request.POST.get('title')
        job.skills = request.POST.get('skills')
        job.salary = request.POST.get('salary') or None
        job.location = request.POST.get('location')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        job.latitude = lat or None
        job.longitude = lon or None
        job.remote_or_on_site = request.POST.get('remote_or_on_site')
        job.visa_sponsorship = request.POST.get('visa_sponsorship')
        job.save()
        messages.success(request, 'Job updated successfully!')
        return redirect('jobs.index')

@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.user != job.posted_by:
        messages.error(request, 'You can only delete your own job postings.')
        return redirect('jobs.index')
    
    job.delete()
    messages.success(request, 'Job deleted successfully!')
    return redirect('jobs.index')

@login_required
@user_passes_test(is_seeker)
def apply_to_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user already applied
    existing_application = Application.objects.filter(job=job, applicant=request.user).first()
    if existing_application:
        messages.warning(request, 'You have already applied to this job.')
        return redirect('jobs.index')
    
    if request.method == 'GET':
        template_data = {
            'title': 'Apply to Job',
            'job': job,
        }
        return render(request, 'jobs/apply_job.html', {'template_data': template_data})
    
    elif request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '')
        
        application = Application.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter
        )
        
        messages.success(request, f'Successfully applied to {job.title}!')
        return redirect('jobs.my_applications')

@login_required
@user_passes_test(is_seeker)
def my_applications(request):
    applications = Application.objects.filter(applicant=request.user).order_by('-applied_at')
    
    template_data = {
        'title': 'My Applications',
        'applications': applications,
    }
    
    return render(request, 'jobs/my_applications.html', {'template_data': template_data})

@login_required
@user_passes_test(is_recruiter)
def manage_applications(request):
    # Get applications for jobs posted by this recruiter
    applications = Application.objects.filter(job__posted_by=request.user).order_by('-applied_at')
    
    template_data = {
        'title': 'Manage Applications',
        'applications': applications,
    }
    
    return render(request, 'jobs/manage_applications.html', {'template_data': template_data})

@login_required
@user_passes_test(is_recruiter)
def pipeline(request, job_id=None):
    """
    Kanban board view for managing applications in a pipeline.
    If job_id is provided, shows applications for that specific job.
    Otherwise, shows all applications for all jobs posted by the recruiter.
    """
    # Get all jobs posted by this recruiter
    recruiter_jobs = Job.objects.filter(posted_by=request.user)
    
    # If a specific job is selected, filter to that job
    selected_job = None
    if job_id:
        selected_job = get_object_or_404(Job, id=job_id, posted_by=request.user)
        applications = Application.objects.filter(job=selected_job).select_related('applicant', 'job').prefetch_related('applicant__profile__skills')
    else:
        # Show all applications for all jobs
        applications = Application.objects.filter(job__in=recruiter_jobs).select_related('applicant', 'job').prefetch_related('applicant__profile__skills')
    
    # Organize applications by status
    status_columns = {
        'applied': [],
        'review': [],
        'interview': [],
        'offer': [],
        'closed': []
    }
    
    for app in applications:
        if app.status in status_columns:
            status_columns[app.status].append(app)
    
    # Get job statistics
    job_stats = {}
    for job in recruiter_jobs:
        job_apps = Application.objects.filter(job=job)
        job_stats[job.id] = {
            'total': job_apps.count(),
            'by_status': {}
        }
        for status_code, status_label in Application.STATUS_CHOICES:
            job_stats[job.id]['by_status'][status_code] = job_apps.filter(status=status_code).count()
    
    template_data = {
        'title': 'Application Pipeline',
        'status_columns': status_columns,
        'status_choices': Application.STATUS_CHOICES,
        'recruiter_jobs': recruiter_jobs,
        'selected_job': selected_job,
        'job_stats': job_stats,
    }
    
    return render(request, 'jobs/pipeline.html', {'template_data': template_data})

@login_required
@user_passes_test(is_recruiter)
def application_detail(request, application_id):
    """
    View application details for recruiters with ability to move to next/previous stages
    """
    application = get_object_or_404(Application, id=application_id)
    
    # Ensure the recruiter owns the job
    if application.job.posted_by != request.user:
        messages.error(request, 'You can only view applications for your own job postings.')
        return redirect('jobs.pipeline')
    
    # Get applicant profile if available
    applicant_profile = None
    try:
        applicant_profile = application.applicant.profile
    except:
        pass
    
    # Get status flow for navigation
    status_flow = [choice[0] for choice in Application.STATUS_CHOICES]
    current_index = status_flow.index(application.status) if application.status in status_flow else 0
    next_status = status_flow[current_index + 1] if current_index < len(status_flow) - 1 else None
    prev_status = status_flow[current_index - 1] if current_index > 0 else None
    
    template_data = {
        'title': f'Application Details - {application.applicant.username}',
        'application': application,
        'applicant_profile': applicant_profile,
        'status_choices': Application.STATUS_CHOICES,
        'next_status': next_status,
        'prev_status': prev_status,
        'current_status_index': current_index,
    }
    
    return render(request, 'jobs/application_detail.html', {'template_data': template_data})

@login_required
@user_passes_test(is_recruiter)
def update_application_status(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    
    # Ensure the recruiter owns the job
    if application.job.posted_by != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'You can only update applications for your own job postings.'}, status=403)
        messages.error(request, 'You can only update applications for your own job postings.')
        return redirect('jobs.manage_applications')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'status': application.status,
                    'status_display': application.get_status_display(),
                    'message': f'Application status updated to {application.get_status_display()}'
                })
            
            messages.success(request, f'Application status updated to {application.get_status_display()}')
            
            # Redirect back to application detail if coming from there, otherwise pipeline
            referer = request.META.get('HTTP_REFERER', '')
            if 'application_detail' in referer or 'applications/' in referer:
                return redirect('jobs.application_detail', application_id=application_id)
            return redirect('jobs.pipeline')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid status selected.'}, status=400)
            messages.error(request, 'Invalid status selected.')
    
    # Default redirect
    referer = request.META.get('HTTP_REFERER', '')
    if 'application_detail' in referer or 'applications/' in referer:
        return redirect('jobs.application_detail', application_id=application_id)
    return redirect('jobs.pipeline')

def job_map(request):
    # Get user's preferred commute radius from their profile
    preferred_radius = 50  # default
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        preferred_radius = request.user.profile.commute_radius
    
    template_data = {
        'title': 'Jobs Near Me',
        'preferred_radius': preferred_radius
    }
    jobs = Job.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    return render(request, 'jobs/job_map.html', {'template_data': template_data, 'jobs': jobs})

@require_GET
def jobs_geo_api(request):
    jobs = Job.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(j.longitude), float(j.latitude)]},
        "properties": {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "salary": float(j.salary) if j.salary is not None else None,
            "detail_url": request.build_absolute_uri(f"/jobs/{j.id}/"),
        },
    } for j in jobs]
    return JsonResponse({"type": "FeatureCollection", "features": features})


@login_required
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Get user's application for this job (if they're a seeker)
    user_application = None
    if request.user.role == 'seeker':
        user_application = Application.objects.filter(job=job, applicant=request.user).first()
    
    # Get all applications for this job (if user is the recruiter who posted it)
    job_applications = []
    if request.user.role == 'recruiter' and job.posted_by == request.user:
        job_applications = Application.objects.filter(job=job).order_by('-applied_at')
    
    # Split skills into a list
    skills_list = [skill.strip() for skill in job.skills.split(',') if skill.strip()]
    
    # Get user's saved jobs (for seekers)
    user_saved_jobs = []
    if request.user.is_authenticated and request.user.role == 'seeker':
        user_saved_jobs = SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)
    
    template_data = {
        'title': f'Job Details - {job.title}',
        'job': job,
        'user_application': user_application,
        'job_applications': job_applications,
        'skills_list': skills_list,
        'user_saved_jobs': user_saved_jobs,
    }
    
    return render(request, 'jobs/job_detail.html', {'template_data': template_data})

@login_required
@user_passes_test(is_seeker)
def track_status(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Get user's application for this job
    application = get_object_or_404(Application, job=job, applicant=request.user)
    
    # Define the status flow with descriptions
    status_flow = [
        {
            'key': 'applied',
            'title': 'Applied',
            'description': 'Your application has been submitted successfully',
            'icon': '📝'
        },
        {
            'key': 'review',
            'title': 'Under Review',
            'description': 'The employer is reviewing your application',
            'icon': '👀'
        },
        {
            'key': 'interview',
            'title': 'Interview',
            'description': 'You have been selected for an interview',
            'icon': '💬'
        },
        {
            'key': 'offer',
            'title': 'Offer',
            'description': 'Congratulations! You have received a job offer',
            'icon': '🎉'
        },
        {
            'key': 'closed',
            'title': 'Closed',
            'description': 'This application has been closed',
            'icon': '✅'
        }
    ]
    
    # Find current status index
    current_status_index = next((i for i, status in enumerate(status_flow) if status['key'] == application.status), 0)
    
    # Split skills into a list
    skills_list = [skill.strip() for skill in job.skills.split(',') if skill.strip()]
    
    template_data = {
        'title': f'Track Application - {job.title}',
        'job': job,
        'application': application,
        'status_flow': status_flow,
        'current_status_index': current_status_index,
        'skills_list': skills_list,
    }
    
    return render(request, 'jobs/track_status.html', {'template_data': template_data})

@login_required
@user_passes_test(is_seeker)
def toggle_save_job(request, job_id):
    """Toggle saving/unsaving a job"""
    job = get_object_or_404(Job, id=job_id)
    
    saved_job, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    
    if created:
        messages.success(request, f'Job "{job.title}" saved!')
    else:
        saved_job.delete()
        messages.info(request, f'Job "{job.title}" removed from saved jobs')
    
    # Redirect back to where they came from, or job list
    return redirect(request.META.get('HTTP_REFERER', 'jobs.index'))

@login_required
@user_passes_test(is_seeker)
def saved_jobs(request):
    """View all saved jobs for the current user"""
    saved_jobs = SavedJob.objects.filter(user=request.user).select_related('job')
    
    template_data = {
        'title': 'My Saved Jobs',
        'saved_jobs': saved_jobs,
    }
    
    return render(request, 'jobs/saved_jobs.html', {'template_data': template_data})
