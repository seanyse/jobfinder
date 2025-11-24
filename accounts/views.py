from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from math import radians, sin, cos, asin, sqrt
from decimal import InvalidOperation
from .forms import CustomUserCreationForm, ProfileForm, CandidateSearchForm, ProjectFormSet, EducationFormSet, WorkExperienceFormSet, MessageForm, ContactCandidateForm, SaveSearchForm
from .models import Profile, Education, WorkExperience, Conversation, Message, CustomUser, Project, SavedCandidateSearch, SearchMatchNotification
from .forms import CustomUserCreationForm, ProfileForm, CandidateSearchForm, ProjectFormSet, EducationFormSet, WorkExperienceFormSet, MessageForm
from .models import Profile, Education, WorkExperience, Conversation, Message, CustomUser, Project
from jobs.models import Job
from django.db.models import Q, Count, Value
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from django.utils import timezone
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
    
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and "privacy_level" in request.POST
    ):
        new_value = request.POST["privacy_level"]
        print("AJAX toggle received:", new_value)
        profile.privacy_level = new_value
        profile.save(update_fields=["privacy_level"])
        return JsonResponse({"status": "ok", "privacy_level": profile.privacy_level})

   
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        project_formset = ProjectFormSet(request.POST, prefix="projects")
        education_formset = EducationFormSet(request.POST, prefix="education")
        work_formset = WorkExperienceFormSet(request.POST, prefix="work")
        
        # Check form validity and log errors if any
        form_valid = form.is_valid()
        project_valid = project_formset.is_valid()
        education_valid = education_formset.is_valid()
        work_valid = work_formset.is_valid()
        
        if not form_valid:
            messages.error(request, f"Profile form errors: {form.errors}")
        if not project_valid:
            messages.error(request, f"Project formset errors: {project_formset.errors}")
        if not education_valid:
            messages.error(request, f"Education formset errors: {education_formset.errors}")
        if not work_valid:
            messages.error(request, f"Work experience formset errors: {work_formset.errors}")
        
        # Always try to save latitude/longitude even if formsets have errors
        # Get latitude and longitude from POST data
        lat_value = None
        lng_value = None
        
        if 'latitude' in request.POST:
            lat_str = request.POST['latitude'].strip()
            if lat_str:
                try:
                    lat_value = float(lat_str)
                    # Validate latitude range
                    if -90 <= lat_value <= 90:
                        pass  # Valid
                    else:
                        lat_value = None
                except (ValueError, TypeError):
                    lat_value = None
        
        if 'longitude' in request.POST:
            lng_str = request.POST['longitude'].strip()
            if lng_str:
                try:
                    lng_value = float(lng_str)
                    # Validate longitude range
                    if -180 <= lng_value <= 180:
                        pass  # Valid
                    else:
                        lng_value = None
                except (ValueError, TypeError):
                    lng_value = None
        
        if form_valid and project_valid and education_valid and work_valid:
            # Save form without committing first
            profile = form.save(commit=False)
            
            # Set latitude/longitude on the instance BEFORE saving
            if lat_value is not None:
                profile.latitude = lat_value
            elif 'latitude' in request.POST and not request.POST['latitude'].strip():
                # Explicitly clear if empty string was sent
                profile.latitude = None
                
            if lng_value is not None:
                profile.longitude = lng_value
            elif 'longitude' in request.POST and not request.POST['longitude'].strip():
                # Explicitly clear if empty string was sent
                profile.longitude = None
            
            # Save the instance (this saves all fields including coordinates)
            profile.save()
            
            # Save ManyToMany fields (skills)
            form.save_m2m()
            
            # Add any new skills typed in
            new_skills_csv = form.cleaned_data.get("new_skills") or ""
            for skill_name in [s.strip() for s in new_skills_csv.split(',') if s.strip()]:
                skill_obj, _ = Profile._meta.get_field('skills').remote_field.model.objects.get_or_create(name=skill_name)
                profile.skills.add(skill_obj)

            # Handle projects from formset - always create new instances to avoid sharing
            profile.projects.clear()
            for f in project_formset:
                if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                    # Always create a new project instance for this profile
                    proj = Project.objects.create(
                        title=f.cleaned_data.get('title', ''),
                        url=f.cleaned_data.get('url', ''),
                        description=f.cleaned_data.get('description', '')
                    )
                    profile.projects.add(proj)

            # Handle education from formset - always create new instances to avoid sharing
            profile.education.clear()
            for f in education_formset:
                if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                    # Always create a new education instance for this profile
                    edu = Education.objects.create(
                        school=f.cleaned_data.get('school', ''),
                        graduation_month=f.cleaned_data.get('graduation_month', 1),
                        graduation_year=f.cleaned_data.get('graduation_year', 2024),
                        major=f.cleaned_data.get('major', ''),
                        degree=f.cleaned_data.get('degree', '')
                    )
                    profile.education.add(edu)

            # Handle work experience from formset - always create new instances to avoid sharing
            profile.work_experience.clear()
            for f in work_formset:
                if f.cleaned_data and not f.cleaned_data.get('DELETE', False):
                    # Always create a new work experience instance for this profile
                    work = WorkExperience.objects.create(
                        company=f.cleaned_data.get('company', ''),
                        description=f.cleaned_data.get('description', '')
                    )
                    profile.work_experience.add(work)
            
            messages.success(request, "Profile saved successfully!")
            # Refresh profile from database to ensure we have the latest data
            profile.refresh_from_db()
            return redirect("accounts.profile_edit")
    else:
        # Refresh profile from database to ensure we have the latest data
        profile.refresh_from_db()
        # Explicitly reload related objects
        profile = Profile.objects.select_related('user').prefetch_related('projects', 'education', 'work_experience', 'skills').get(pk=profile.pk)
        form = ProfileForm(instance=profile)
        
        # Explicitly set initial values for latitude/longitude to ensure they're in the form
        # Use getattr with default None to handle cases where fields might not exist yet
        lat_value = getattr(profile, 'latitude', None)
        lng_value = getattr(profile, 'longitude', None)
        if lat_value is not None:
            form.initial['latitude'] = str(lat_value)
            form.fields['latitude'].initial = str(lat_value)
        if lng_value is not None:
            form.initial['longitude'] = str(lng_value)
            form.fields['longitude'].initial = str(lng_value)
        
        # Initialize projects formset with queryset
        project_formset = ProjectFormSet(
            queryset=profile.projects.all(),
            prefix="projects"
        )
        
        # Initialize education formset with queryset
        education_formset = EducationFormSet(
            queryset=profile.education.all(),
            prefix="education"
        )
        
        # Initialize work experience formset with queryset
        work_formset = WorkExperienceFormSet(
            queryset=profile.work_experience.all(),
            prefix="work"
        )
        
    return render(request, "accounts/profile_form.html", {
        "form": form, 
        "project_formset": project_formset,
        "education_formset": education_formset,
        "work_formset": work_formset
    })

def can_view_profile(viewer, profile_owner, profile: Profile) -> bool:
    # Owner can always view
    if viewer.is_authenticated and viewer == profile_owner:
        return True
    # Public is world-visible (including recruiters)
    if profile.privacy_level == Profile.PRIVACY_PUBLIC:
        return True
    # Private blocks non-owners (including recruiters)
    return False

@login_required
def my_profile(request):
    # Redirect directly to profile edit page
    return redirect("accounts.profile_edit")

def profile_detail(request, username):
    User = get_user_model()
    user_obj = get_object_or_404(User, username=username)

    # Some users may not have a profile yet
    profile = getattr(user_obj, "profile", None)
    if profile is None:
        # Owner sees their empty profile page to encourage editing,
        # others get a friendly private message
        if request.user.is_authenticated and request.user == user_obj:
            return render(request, "accounts/profile_detail.html", {"user_obj": user_obj, "profile": profile})
        return render(request, "accounts/profile_private.html", {"user_obj": user_obj}, status=403)

    # Enforce privacy settings
    if not can_view_profile(request.user, user_obj, profile):
        return render(request, "accounts/profile_private.html", {"user_obj": user_obj}, status=403)

    return render(request, "accounts/profile_detail.html", {"user_obj": user_obj, "profile": profile})

def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        print("POST privacy_level =", request.POST.get("privacy_level"))  # TEMP debug
        if form.is_valid():
            obj = form.save()     # <- save instance
            print("SAVED privacy_level =", obj.privacy_level)  # TEMP debug
            messages.success(request, "Profile updated.")
            return redirect("profile_settings")  # PRG pattern
        else:
            print("FORM ERRORS:", form.errors)   # TEMP debug
    else:
        form = ProfileForm(instance=profile)
    return render(request, "accounts/profile_form.html", {"form": form})

def candidate_search(request):
    # US-11: recruiter searches candidates
    form = CandidateSearchForm(request.GET or None)
    filters_applied = False
    # Start with all job seekers (users with role='seeker')
    User = get_user_model()
    seeker_users = User.objects.filter(role='seeker')
    
    # Get profiles for these users with public privacy level
    qs = Profile.objects.filter(
        user__in=seeker_users,
        privacy_level=Profile.PRIVACY_PUBLIC
    ).select_related("user").prefetch_related("skills", "projects")
    
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
        filters_applied = bool(
            form.cleaned_data.get("location") or
            form.cleaned_data.get("project_keyword") or
            (form.cleaned_data.get("skills") and len(form.cleaned_data.get("skills")) > 0)
        )

    # Always set results to the queryset (even if form is not valid, show all results)
    results = qs.distinct()

    # candidate recommedation functionality
    matches = {}   # job → list of matching profiles
    if not filters_applied:
        for job in Job.objects.filter(posted_by=request.user):
            # convert job skills text field into a lowercase set
            job_skill_set = {
                s.lower().strip()
                for s in job.skills.split(",")
                if s.strip() != ""
            }

            matches[job] = []  # initialize list for this job

            # Loop through every candidate profile you already iterated earlier
            for profile in qs:   # <-- use your existing qs from above
                candidate_skill_set = {
                    s.name.lower().strip()
                    for s in profile.skills.all()
                }

                overlap = len(job_skill_set & candidate_skill_set)

                if overlap >= 2:
                    matches[job].append(profile)

    # Only exclude recommended IDs if we have matches
    recommended_ids = [p.id for profiles in matches.values() for p in profiles]
    if recommended_ids:
        results = results.exclude(id__in=recommended_ids)
    has_matches = any(matches.values()) # bool that returns true if there are any candidate recommendations
    return render(request, "accounts/candidate_search.html", {"form": form, "results": results, "users_without_profiles": users_without_profiles, "matches": matches, "has_matches": has_matches})

def _execute_saved_search_query(saved_search):
    """
    Helper function to execute a saved search query and return matching profiles.
    This replicates the logic from candidate_search view.
    """
    User = get_user_model()
    seeker_users = User.objects.filter(role='seeker')
    
    # Get profiles for these users with public privacy level
    qs = Profile.objects.filter(
        user__in=seeker_users,
        privacy_level=Profile.PRIVACY_PUBLIC
    ).select_related("user").prefetch_related("skills", "projects")
    
    # Apply location filter
    if saved_search.location:
        qs = qs.filter(location__icontains=saved_search.location)
    
    # Apply project keyword filter
    if saved_search.project_keyword:
        qs = qs.filter(Q(projects__title__icontains=saved_search.project_keyword) | 
                      Q(projects__description__icontains=saved_search.project_keyword))
    
    # Apply skills filter
    sel_skills = list(saved_search.skills.all())
    if sel_skills:
        if saved_search.match_all_skills:
            for s in sel_skills:
                qs = qs.filter(skills=s)  # AND
            qs = qs.annotate(matched=Value(len(sel_skills)))
        else:
            qs = qs.filter(skills__in=sel_skills)  # OR
            qs = qs.annotate(
                matched=Count("skills", filter=Q(skills__in=sel_skills), distinct=True)
            )
        qs = qs.order_by("-matched", "user__username")
    else:
        qs = qs.order_by("user__username")
    
    return qs.distinct()

@login_required
def save_candidate_search(request):
    """Save the current candidate search with a name"""
    if request.user.role != 'recruiter':
        messages.error(request, 'Only recruiters can save searches.')
        return redirect('accounts.candidate_search')
    
    if request.method == 'POST':
        save_form = SaveSearchForm(request.POST)
        # Get search parameters from POST (they'll be included as hidden fields)
        search_data = {
            'location': request.POST.get('location', ''),
            'project_keyword': request.POST.get('project_keyword', ''),
            'skills': request.POST.getlist('skills'),
            'match_all_skills': request.POST.get('match_all_skills') == 'on'
        }
        search_form = CandidateSearchForm(search_data)
        
        if save_form.is_valid() and search_form.is_valid():
            name = save_form.cleaned_data['name']
            
            # Check if a search with this name already exists for this user
            existing = SavedCandidateSearch.objects.filter(
                recruiter=request.user,
                name=name
            ).first()
            
            if existing:
                messages.error(request, f'A search named "{name}" already exists. Please choose a different name.')
                # Redirect back with search parameters
                params = request.POST.urlencode() if hasattr(request.POST, 'urlencode') else ''
                return redirect('accounts.candidate_search?' + params)
            
            # Create the saved search
            saved_search = SavedCandidateSearch.objects.create(
                recruiter=request.user,
                name=name,
                location=search_form.cleaned_data.get('location', ''),
                project_keyword=search_form.cleaned_data.get('project_keyword', ''),
                match_all_skills=search_form.cleaned_data.get('match_all_skills', True)
            )
            
            # Add skills
            skills = search_form.cleaned_data.get('skills', [])
            if skills:
                saved_search.skills.set(skills)
            
            messages.success(request, f'Search "{name}" saved successfully!')
            return redirect('accounts.saved_searches')
        else:
            messages.error(request, 'Please provide a name for this search.')
            # Redirect back with original GET parameters if available
            if request.GET:
                return redirect('accounts.candidate_search?' + request.GET.urlencode())
            return redirect('accounts.candidate_search')
    
    return redirect('accounts.candidate_search')

@login_required
def saved_searches_list(request):
    """List all saved searches for the current recruiter"""
    if request.user.role != 'recruiter':
        messages.error(request, 'Only recruiters can view saved searches.')
        return redirect('home.index')
    
    saved_searches = SavedCandidateSearch.objects.filter(
        recruiter=request.user
    ).prefetch_related('skills').order_by('-created_at')
    
    # For each saved search, count current matches
    for search in saved_searches:
        matches = _execute_saved_search_query(search)
        search.match_count = matches.count()
        # Count new matches (candidates not yet notified)
        if search.is_active:
            notified_candidate_ids = SearchMatchNotification.objects.filter(
                saved_search=search
            ).values_list('candidate_id', flat=True)
            new_matches = matches.exclude(user_id__in=notified_candidate_ids)
            search.new_match_count = new_matches.count()
        else:
            search.new_match_count = 0
    
    return render(request, 'accounts/saved_searches.html', {
        'saved_searches': saved_searches
    })

@login_required
def saved_search_detail(request, search_id):
    """View matches for a specific saved search"""
    saved_search = get_object_or_404(
        SavedCandidateSearch,
        id=search_id,
        recruiter=request.user
    )
    
    results = _execute_saved_search_query(saved_search)
    
    # Get list of already notified candidates
    notified_candidate_ids = SearchMatchNotification.objects.filter(
        saved_search=saved_search
    ).values_list('candidate_id', flat=True)
    
    # Mark which candidates are new (not yet notified)
    for result in results:
        result.is_new_match = (
            saved_search.is_active and 
            result.user_id not in notified_candidate_ids
        )
    
    return render(request, 'accounts/saved_search_detail.html', {
        'saved_search': saved_search,
        'results': results,
        'notified_count': len(notified_candidate_ids)
    })

@login_required
def delete_saved_search(request, search_id):
    """Delete a saved search"""
    saved_search = get_object_or_404(
        SavedCandidateSearch,
        id=search_id,
        recruiter=request.user
    )
    
    if request.method == 'POST':
        name = saved_search.name
        saved_search.delete()
        messages.success(request, f'Search "{name}" deleted successfully.')
        return redirect('accounts.saved_searches')
    
    return redirect('accounts.saved_searches')

@login_required
def toggle_saved_search_active(request, search_id):
    """Toggle the active status of a saved search"""
    saved_search = get_object_or_404(
        SavedCandidateSearch,
        id=search_id,
        recruiter=request.user
    )
    
    if request.method == 'POST':
        saved_search.is_active = not saved_search.is_active
        saved_search.save()
        status = 'activated' if saved_search.is_active else 'deactivated'
        messages.success(request, f'Search "{saved_search.name}" {status}.')
    
    return redirect('accounts.saved_searches')

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

def safe_send_email(subject, body, to_email, from_email=None):
    """
    Try the configured backend first. If it fails, fall back to console backend.
    Returns (sent_ok: bool, fallback_used: bool, error_message: str|None)
    """
    try:
        # Try the configured backend (from settings)
        EmailMessage(subject, body, from_email, [to_email]).send(fail_silently=False)
        return True, False, None
    except Exception as e:
        # Fallback: console backend (prints to terminal instead of connecting)
        try:
            conn = get_connection("django.core.mail.backends.console.EmailBackend")
            EmailMessage(subject, body, from_email, [to_email], connection=conn).send(fail_silently=True)
            return True, True, str(e)
        except Exception as e2:
            return False, True, f"{e} | fallback failed: {e2}"

@login_required
def contact_candidate(request, username):
    # Only recruiters can send messages
    if not hasattr(request.user, "role") or request.user.role != "recruiter":
        return HttpResponseForbidden("Only recruiters can contact candidates.")

    # Use AUTH_USER_MODEL for safety
    User = get_user_model()
    candidate = get_object_or_404(User, username=username, role="seeker")
    if not candidate.email:
        messages.error(request, "This candidate has no email on file.")
        return redirect("accounts.profile_detail", username=username)

    if request.method == "POST":
        form = ContactCandidateForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            msg = form.cleaned_data["message"]

            email_subject = f"[JobFinder] {subject}"
            body = (
                f"Hello {candidate.first_name or candidate.username},\n\n"
                f"{msg}\n\n"
                f"---\nSent via JobFinder by "
                f"{request.user.get_full_name() or request.user.username} ({request.user.email})"
            )

            # Try configured backend first; on failure, fall back to console backend
            try:
                EmailMessage(
                    subject=email_subject,
                    body=body,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    to=[candidate.email],
                ).send(fail_silently=False)
                messages.success(request, f"Email sent to {candidate.username}.")
            except Exception as e:
                # Fallback: send to console so dev flow still “succeeds”
                conn = get_connection("django.core.mail.backends.console.EmailBackend")
                EmailMessage(
                    subject=email_subject,
                    body=body,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    to=[candidate.email],
                    connection=conn,
                ).send(fail_silently=True)
                messages.success(request, f"Email sent to {candidate.username} (console fallback).")

            return redirect("accounts.profile_detail", username=username)
    else:
        form = ContactCandidateForm(initial={
            "subject": "Opportunity regarding your profile",
            "message": (
                f"Hi {candidate.first_name or candidate.username},\n\n"
                "I came across your profile on JobFinder and think you'd be a great fit for a role "
                "we're hiring for. If you're open to it, I'd love to share details and set up a quick chat.\n\n"
                f"Best,\n{request.user.get_full_name() or request.user.username}"
            ),
        })

    return render(request, "accounts/contact_candidate.html", {"form": form, "candidate": candidate})

def is_recruiter(user):
    return user.is_authenticated and getattr(user, "role", None) == "recruiter"

@user_passes_test(is_recruiter)
def applicant_clusters_map(request):
    """
    Page showing clusters of applicants by location on a map.
    Only accessible to recruiters.
    """
    template_data = {
        'title': 'Applicant Clusters Map'
    }
    return render(request, 'accounts/applicant_clusters_map.html', {'template_data': template_data})

@user_passes_test(is_recruiter)
def applicant_clusters_api(request):
    """
    API endpoint that returns clustered applicant data.
    Clusters are defined by a 50-mile radius, and a cluster must have more than 1 candidate.
    """
    from jobs.models import Application
    import traceback
    
    try:
        # Get all unique applicants who have applied to jobs posted by this recruiter
        recruiter_jobs = Job.objects.filter(posted_by=request.user)
        
        # Handle case where recruiter has no jobs
        if not recruiter_jobs.exists():
            return JsonResponse({
                "type": "FeatureCollection",
                "features": [],
                "debug": {
                    "total_applications": 0,
                    "unique_applicants": 0,
                    "applicants_with_coords": 0,
                    "total_clusters": 0,
                    "valid_clusters": 0,
                    "recruiter_jobs_count": 0
                }
            })
        
        applications = Application.objects.filter(job__in=recruiter_jobs).select_related('applicant')
        
        # Get unique applicants with valid coordinates
        applicants_with_coords = []
        seen_applicants = set()
        
        for app in applications:
            applicant = app.applicant
            if applicant.id in seen_applicants:
                continue
            seen_applicants.add(applicant.id)
            
            # Check if applicant has a profile with coordinates
            try:
                profile = applicant.profile
            except (Profile.DoesNotExist, AttributeError):
                continue
            
            if profile and hasattr(profile, 'latitude') and hasattr(profile, 'longitude') and profile.latitude is not None and profile.longitude is not None:
                try:
                    lat = float(profile.latitude)
                    lng = float(profile.longitude)
                    # Validate coordinates are reasonable (latitude: -90 to 90, longitude: -180 to 180)
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        applicants_with_coords.append({
                            'id': applicant.id,
                            'username': applicant.username,
                            'lat': lat,
                            'lng': lng,
                            'location': profile.location or '',
                        })
                except (TypeError, ValueError, InvalidOperation):
                    continue
        
        # Cluster applicants by 50-mile radius (approximately 80.47 km)
        CLUSTER_RADIUS_KM = 80.47  # 50 miles in kilometers
        
        def haversine_km(lat1, lon1, lat2, lon2):
            """Calculate distance between two points in kilometers"""
            R = 6371.0
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            return 2 * R * asin(sqrt(a))
        
        clusters = []
        
        for applicant in applicants_with_coords:
            assigned = False
            # Check if this applicant belongs to any existing cluster
            for cluster in clusters:
                cluster_center_lat = cluster['center_lat']
                cluster_center_lng = cluster['center_lng']
                distance = haversine_km(
                    cluster_center_lat, cluster_center_lng,
                    applicant['lat'], applicant['lng']
                )
                
                if distance <= CLUSTER_RADIUS_KM:
                    # Add to existing cluster
                    cluster['applicants'].append(applicant)
                    # Update cluster center (average of all points)
                    total_lat = sum(a['lat'] for a in cluster['applicants'])
                    total_lng = sum(a['lng'] for a in cluster['applicants'])
                    count = len(cluster['applicants'])
                    cluster['center_lat'] = total_lat / count
                    cluster['center_lng'] = total_lng / count
                    cluster['count'] = count
                    assigned = True
                    break
            
            if not assigned:
                # Create new cluster
                clusters.append({
                    'center_lat': applicant['lat'],
                    'center_lng': applicant['lng'],
                    'applicants': [applicant],
                    'count': 1
                })
        
        # Filter clusters to only include those with more than 1 candidate
        valid_clusters = [c for c in clusters if c['count'] > 1]
        
        # Convert to GeoJSON format
        features = []
        for cluster in valid_clusters:
            # Get list of applicant usernames for the popup
            applicant_names = [a['username'] for a in cluster['applicants']]
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [cluster['center_lng'], cluster['center_lat']]
                },
                "properties": {
                    "count": cluster['count'],
                    "applicants": applicant_names,
                    "center_lat": cluster['center_lat'],
                    "center_lng": cluster['center_lng']
                }
            })
        
        # Add debug information (can be removed in production)
        debug_info = {
            "total_applications": applications.count(),
            "unique_applicants": len(seen_applicants),
            "applicants_with_coords": len(applicants_with_coords),
            "total_clusters": len(clusters),
            "valid_clusters": len(valid_clusters),
            "recruiter_jobs_count": recruiter_jobs.count()
        }
        
        return JsonResponse({
            "type": "FeatureCollection", 
            "features": features,
            "debug": debug_info
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        # Log the error to help with debugging
        print(f"Error in applicant_clusters_api: {str(e)}")
        print(error_trace)
        return JsonResponse({
            "error": str(e),
            "traceback": error_trace,
            "type": "FeatureCollection",
            "features": []
        }, status=500)