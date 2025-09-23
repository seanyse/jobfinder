from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from django import forms
from .models import Profile, Skill, Project

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "role")

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role')

class ProfileForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(), required=False, widget=forms.CheckboxSelectMultiple
    )
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Profile
        fields = [
            "headline", "bio", "location",
            "website", "github", "linkedin",
            "skills", "projects",
        ]

class CandidateSearchForm(forms.Form):
    skills = forms.ModelMultipleChoiceField(queryset=Skill.objects.all(), required=False)
    location = forms.CharField(required=False)
    project_keyword = forms.CharField(required=False, help_text="Search project titles/descriptions")
    match_all_skills = forms.BooleanField(required=False, initial=True)
