from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.db.models import Q, Count, Value
from django.contrib.auth import get_user_model
from .forms import CustomUserCreationForm, ProfileForm, CandidateSearchForm, ProjectFormSet, EducationFormSet, WorkExperienceFormSet
from .models import Profile, Education, WorkExperience


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
    
    # Always show results - either filtered or all candidates
    qs = Profile.objects.select_related("user").prefetch_related("skills", "projects")
    
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

    return render(request, "accounts/candidate_search.html", {"form": form, "results": results})

