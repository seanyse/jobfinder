from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Job

# Create your views here.
def index(request):
    # Start with all jobs
    jobs = Job.objects.all()

    # Filtering
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

    template_data = {}
    template_data['title'] = 'Jobs'
    template_data['jobs'] = jobs
    template_data['filters'] = request.GET  # so form keeps current valuesjobs = Job.objects.all()

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
        job.remote_or_on_site = request.POST.get('remote_or_on_site')
        job.visa_sponsorship = request.POST.get('visa_sponsorship')
        job.posted_by = request.user
        job.save()
        return redirect('jobs.index')  # Redirect to job listings page

    #return render(request, 'jobs/job_listings.html')