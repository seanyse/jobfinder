from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from .forms import CustomUserCreationForm, ProfileForm, CandidateSearchForm
from .models import Profile


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
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts.profile_detail", username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, "accounts/profile_form.html", {"form": form})

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
    if form.is_valid():
        qs = Profile.objects.select_related("user").prefetch_related("skills", "projects")

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
            else:
                qs = qs.filter(skills__in=sel_skills)  # OR
        results = qs.distinct()

        if sel_skills:
            results = results.annotate(
                matched=Count("skills", filter=Q(skills__in=sel_skills), distinct=True)
            ).order_by("-matched", "user__username")

    return render(request, "accounts/candidate_search.html", {"form": form, "results": results})

