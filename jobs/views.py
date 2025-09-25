from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Case, When, IntegerField
from .models import Job, Application
from django.http import JsonResponse
from django.views.decorators.http import require_GET

def is_seeker(user):
    return user.is_authenticated and getattr(user, "role", None) == "seeker"

@login_required
def index(request):
    jobs = Job.objects.all()
    filters = {}

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
        
        # Get user's applications to show which jobs they've already applied to
        user_applications = Application.objects.filter(applicant=request.user).values_list('job_id', flat=True)

    elif request.user.role == 'recruiter':
        # For recruiters, sort their jobs on top
        jobs = jobs.annotate(
            is_mine=Case(
                When(posted_by=request.user, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('is_mine', '-created_at')
        user_applications = []

    template_data = {
        'title': 'Jobs',
        'jobs': jobs,
        'filters': filters,
        'user_applications': user_applications,
    }

    return render(request, 'jobs/job_listings.html', {'template_data': template_data})

def is_recruiter(user):
    return user.is_authenticated and user.role == 'recruiter'

def is_seeker(user):
    return user.is_authenticated and user.role == 'seeker'

@login_required
@user_passes_test(is_recruiter)
def create_job(request):
    if request.method == 'POST':
        job = Job()
        job.title = request.POST.get('title')
        job.skills = request.POST.get('skills')
        job.salary = request.POST.get('salary') or None
        job.location = request.POST.get('location') or ''
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
def update_application_status(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    
    # Ensure the recruiter owns the job
    if application.job.posted_by != request.user:
        messages.error(request, 'You can only update applications for your own job postings.')
        return redirect('jobs.manage_applications')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            messages.success(request, f'Application status updated to {application.get_status_display()}')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('jobs.manage_applications')

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
    
    template_data = {
        'title': f'Job Details - {job.title}',
        'job': job,
        'user_application': user_application,
        'job_applications': job_applications,
        'skills_list': skills_list,
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
