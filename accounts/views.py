from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.db.models import Q, Count, Value
from django.contrib.auth import get_user_model
from .forms import CustomUserCreationForm, ProfileForm, CandidateSearchForm, ProjectFormSet, EducationFormSet, WorkExperienceFormSet, MessageForm
from .models import Profile, Education, WorkExperience, Conversation, Message, CustomUser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@login_required
def logout(request):
    auth_logout(request)
    return redirect('home.index')

def signup(request):
    template_data = {}
    template_data['title'] = 'Sign Up'
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts.login')
        else:
            template_data['form'] = form
    else:
        template_data['form'] = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'template_data': template_data})

def login(request):
    template_data = {}
    template_data['title'] = 'Login'
    if request.method == 'GET':
        return render(request, 'accounts/login.html', {
            'template_data': template_data
        })
    elif request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user is None:
            template_data['error'] = 'The username or password is incorrect.'
            return render(request, 'accounts/login.html', {
                'template_data': template_data
            })
        else:
            auth_login(request, user)
            return redirect('home.index')

User = get_user_model()

@login_required
def profile_edit(request):
    # US-1: create/edit own profile
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        project_formset = ProjectFormSet(request.POST, prefix="projects")
        education_formset = EducationFormSet(request.POST, prefix="education")
        work_formset = WorkExperienceFormSet(request.POST, prefix="work")
        if form.is_valid() and project_formset.is_valid() and education_formset.is_valid() and work_formset.is_valid():
            profile = form.save()
            # Add any new skills typed in
            new_skills_csv = form.cleaned_data.get("new_skills") or ""
            for skill_name in [s.strip() for s in new_skills_csv.split(',') if s.strip()]:
                skill_obj, _ = Profile._meta.get_field('skills').remote_field.model.objects.get_or_create(name=skill_name)
                profile.skills.add(skill_obj)

            # Handle projects from formset
            profile.projects.clear()
            for i, f in enumerate(project_formset):
                if f.cleaned_data:
                    delete_key = f'projects-{i}-DELETE'
                    is_deleted = request.POST.get(delete_key) == 'on'
                    if not is_deleted:
                        project_id = None
                        for key, value in request.POST.items():
                            if key.startswith(f'projects-{i}-') and key.endswith('-id') and value:
                                project_id = value
                                break
                        if project_id:
                            try:
                                existing_project = Project.objects.get(id=project_id)
                                existing_project.title = f.cleaned_data['title']
                                existing_project.url = f.cleaned_data['url']
                                existing_project.description = f.cleaned_data['description']
                                existing_project.save()
                                profile.projects.add(existing_project)
                            except Project.DoesNotExist:
                                pass
                        else:
                            proj = f.save()
                            profile.projects.add(proj)

            # Handle education from formset
            profile.education.clear()
            for i, f in enumerate(education_formset):
                if f.cleaned_data:
                    delete_key = f'education-{i}-DELETE'
                    is_deleted = request.POST.get(delete_key) == 'on'
                    if not is_deleted:
                        education_id = None
                        for key, value in request.POST.items():
                            if key.startswith(f'education-{i}-') and key.endswith('-id') and value:
                                education_id = value
                                break
                        if education_id:
                            try:
                                existing_education = Education.objects.get(id=education_id)
                                existing_education.school = f.cleaned_data['school']
                                existing_education.graduation_month = f.cleaned_data['graduation_month']
                                existing_education.graduation_year = f.cleaned_data['graduation_year']
                                existing_education.major = f.cleaned_data['major']
                                existing_education.degree = f.cleaned_data['degree']
                                existing_education.save()
                                profile.education.add(existing_education)
                            except Education.DoesNotExist:
                                pass
                        else:
                            edu = f.save()
                            profile.education.add(edu)

            # Handle work experience from formset
            profile.work_experience.clear()
            for i, f in enumerate(work_formset):
                if f.cleaned_data:
                    delete_key = f'work-{i}-DELETE'
                    is_deleted = request.POST.get(delete_key) == 'on'
                    if not is_deleted:
                        work_id = None
                        for key, value in request.POST.items():
                            if key.startswith(f'work-{i}-') and key.endswith('-id') and value:
                                work_id = value
                                break
                        if work_id:
                            try:
                                existing_work = WorkExperience.objects.get(id=work_id)
                                existing_work.company = f.cleaned_data['company']
                                existing_work.description = f.cleaned_data['description']
                                existing_work.save()
                                profile.work_experience.add(existing_work)
                            except WorkExperience.DoesNotExist:
                                pass
                        else:
                            work = f.save()
                            profile.work_experience.add(work)

            return redirect("accounts.profile_detail", username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
        
        # Initialize projects formset
        project_initial = []
        for p in profile.projects.all():
            project_initial.append({
                "title": p.title,
                "url": p.url,
                "description": p.description,
                "id": p.id
            })
        project_formset = ProjectFormSet(initial=project_initial, prefix="projects")
        
        # Initialize education formset
        education_initial = []
        for e in profile.education.all():
            education_initial.append({
                "school": e.school,
                "graduation_month": e.graduation_month,
                "graduation_year": e.graduation_year,
                "major": e.major,
                "degree": e.degree,
                "id": e.id
            })
        education_formset = EducationFormSet(initial=education_initial, prefix="education")
        
        # Initialize work experience formset
        work_initial = []
        for w in profile.work_experience.all():
            work_initial.append({
                "company": w.company,
                "description": w.description,
                "id": w.id
            })
        work_formset = WorkExperienceFormSet(initial=work_initial, prefix="work")
        
    return render(request, "accounts/profile_form.html", {
        "form": form, 
        "project_formset": project_formset,
        "education_formset": education_formset,
        "work_formset": work_formset
    })

@login_required
def my_profile(request):
    # Redirect to profile detail view for the current user
    return redirect("accounts.profile_detail", username=request.user.username)

def profile_detail(request, username):
    user = User.objects.filter(username=username).first()
    if not user:
        return redirect("home.index")
    profile = getattr(user, "profile", None)
    return render(request, "accounts/profile_detail.html", {"user_obj": user, "profile": profile})

def candidate_search(request):
    # US-11: recruiter searches candidates
    form = CandidateSearchForm(request.GET or None)
    results = None
    
    # Start with all job seekers (users with role='seeker')
    User = get_user_model()
    seeker_users = User.objects.filter(role='seeker')
    
    # Get profiles for these users, including those without profiles
    qs = Profile.objects.filter(user__in=seeker_users).select_related("user").prefetch_related("skills", "projects")
    
    # Also get users without profiles to include them in search results
    users_without_profiles = seeker_users.filter(profile__isnull=True)
    
    if form.is_valid():
        loc = form.cleaned_data.get("location")
        if loc:
            qs = qs.filter(location__icontains=loc)

        kw = form.cleaned_data.get("project_keyword")
        if kw:
            qs = qs.filter(Q(projects__title__icontains=kw) | Q(projects__description__icontains=kw))

        sel_skills = list(form.cleaned_data.get("skills") or [])
        if sel_skills:
            if form.cleaned_data.get("match_all_skills"):
                for s in sel_skills:
                    qs = qs.filter(skills=s)       # AND
                # For AND matching, all selected skills must match, so count is the number of selected skills
                qs = qs.annotate(matched=Value(len(sel_skills)))
            else:
                qs = qs.filter(skills__in=sel_skills)  # OR
                # For OR matching, count how many of the selected skills each candidate has
                qs = qs.annotate(
                    matched=Count("skills", filter=Q(skills__in=sel_skills), distinct=True)
                )
            qs = qs.order_by("-matched", "user__username")
        else:
            # Order by username when no skills selected
            qs = qs.order_by("user__username")
    
    results = qs.distinct()

    return render(request, "accounts/candidate_search.html", {"form": form, "results": results, "users_without_profiles": users_without_profiles})

def update_commute_radius(request):
    """API endpoint to update user's preferred commute radius"""
    # Only allow POST requests
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Check authentication manually to return JSON instead of redirecting
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        commute_radius = data.get('commute_radius')
        
        if not commute_radius or not isinstance(commute_radius, (int, float)):
            return JsonResponse({'error': 'Invalid commute radius'}, status=400)
        
        if commute_radius < 1 or commute_radius > 500:
            return JsonResponse({'error': 'Commute radius must be between 1 and 500 km'}, status=400)
        
        # Get or create user profile
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile.commute_radius = int(commute_radius)
        profile.save()
        
        return JsonResponse({'success': True, 'commute_radius': profile.commute_radius})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Messaging views
@login_required
def conversations_list(request):
    """List all conversations for the current user"""
    if request.user.role == 'recruiter':
        conversations = Conversation.objects.filter(recruiter=request.user).order_by('-updated_at')
        template_name = 'accounts/recruiter_conversations.html'
    elif request.user.role == 'seeker':
        conversations = Conversation.objects.filter(candidate=request.user).order_by('-updated_at')
        template_name = 'accounts/candidate_conversations.html'
    else:
        return redirect('home.index')
    
    template_data = {
        'title': 'Messages',
        'conversations': conversations
    }
    
    return render(request, template_name, {'template_data': template_data})

@login_required
def conversation_detail(request, conversation_id):
    """View and send messages in a conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Check if user is part of this conversation
    if request.user not in [conversation.recruiter, conversation.candidate]:
        messages.error(request, 'You are not authorized to view this conversation.')
        return redirect('accounts.conversations_list')
    
    # Get messages for this conversation
    messages_list = conversation.messages.all()
    
    # Mark messages as read for the current user
    messages_list.exclude(sender=request.user).update(is_read=True)
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            
            # Update conversation timestamp
            conversation.save()
            
            return redirect('accounts.conversation_detail', conversation_id=conversation.id)
    else:
        form = MessageForm()
    
    # Determine the other participant
    other_user = conversation.candidate if request.user == conversation.recruiter else conversation.recruiter
    
    template_data = {
        'title': f'Conversation with {other_user.username}',
        'conversation': conversation,
        'messages': messages_list,
        'form': form,
        'other_user': other_user
    }
    
    return render(request, 'accounts/conversation_detail.html', {'template_data': template_data})

@login_required
def start_conversation(request, candidate_id):
    """Start a new conversation with a candidate (recruiters only)"""
    if request.user.role != 'recruiter':
        messages.error(request, 'Only recruiters can start conversations.')
        return redirect('home.index')
    
    candidate = get_object_or_404(CustomUser, id=candidate_id, role='seeker')
    
    # Check if conversation already exists
    conversation, created = Conversation.objects.get_or_create(
        recruiter=request.user,
        candidate=candidate
    )
    
    if created:
        messages.success(request, f'Started conversation with {candidate.username}')
    else:
        messages.info(request, f'Conversation with {candidate.username} already exists')
    
    return redirect('accounts.conversation_detail', conversation_id=conversation.id)

@login_required
def start_conversation_with_job(request, candidate_id, job_id):
    """Start a new conversation with a candidate about a specific job"""
    if request.user.role != 'recruiter':
        messages.error(request, 'Only recruiters can start conversations.')
        return redirect('home.index')
    
    candidate = get_object_or_404(CustomUser, id=candidate_id, role='seeker')
    job = get_object_or_404('jobs.Job', id=job_id)
    
    # Verify the recruiter owns the job
    if job.posted_by != request.user:
        messages.error(request, 'You can only start conversations about your own jobs.')
        return redirect('home.index')
    
    # Check if conversation already exists for this job
    conversation, created = Conversation.objects.get_or_create(
        recruiter=request.user,
        candidate=candidate,
        job=job
    )
    
    if created:
        messages.success(request, f'Started conversation with {candidate.username} about {job.title}')
    else:
        messages.info(request, f'Conversation with {candidate.username} about {job.title} already exists')
    
    return redirect('accounts.conversation_detail', conversation_id=conversation.id)

