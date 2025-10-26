from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, ProfileForm, CandidateSearchForm, ProjectFormSet, EducationFormSet, WorkExperienceFormSet, MessageForm
from .models import Profile, Education, WorkExperience, Conversation, Message, CustomUser
from django.db.models import Q, Count, Value
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
    # Redirect to profile detail view for the current user
    return redirect("accounts.profile_detail", username=request.user.username)

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
    results = None
    
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