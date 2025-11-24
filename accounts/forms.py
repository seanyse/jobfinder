from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from django import forms
from .models import Profile, Skill, Project, Education, WorkExperience, Conversation, Message, SavedCandidateSearch
from django.forms import formset_factory, modelformset_factory, TextInput, URLInput, Textarea, Select

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
    new_skills = forms.CharField(required=False, help_text="Comma-separated new skills to add")
    commute_radius = forms.IntegerField(
        min_value=1,
        max_value=500,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Preferred commute radius in kilometers"
    )
    latitude = forms.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Profile
        fields = [
            "profile_picture",
            "headline", "bio", "location",
            "website", "github", "linkedin",
            "commute_radius",
            "skills", "privacy_level",
            "latitude", "longitude"
        ]
        widgets = {"privacy_level": forms.RadioSelect()}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Force the choices to exactly what's on the model
            self.fields["privacy_level"].choices = Profile.PRIVACY_CHOICES
            # Ensure latitude/longitude are initialized from instance if available
            # For hidden fields, we need to set the value directly, not just initial
            if self.instance and self.instance.pk:
                if self.instance.latitude is not None:
                    self.fields["latitude"].initial = str(self.instance.latitude)
                    # Also set the value if form is not bound (GET request)
                    if not self.is_bound:
                        self.initial["latitude"] = str(self.instance.latitude)
                if self.instance.longitude is not None:
                    self.fields["longitude"].initial = str(self.instance.longitude)
                    # Also set the value if form is not bound (GET request)
                    if not self.is_bound:
                        self.initial["longitude"] = str(self.instance.longitude)

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
   
        fields = ["title", "url", "description"]   
        widgets = {
            "title": TextInput(attrs={"class": "form-control"}),
            "url": URLInput(attrs={"class": "form-control"}),
            "description": Textarea(attrs={"class": "form-control"}),
        }

ProjectFormSet = modelformset_factory(Project, form=ProjectForm, extra=0, can_delete=True)

class ContactCandidateForm(forms.Form):
    subject = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Subject"})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "class": "form-control", "placeholder": "Write your message"})
    )
    
class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ["school", "graduation_month", "graduation_year", "major", "degree"]
        widgets = {
            "school": TextInput(attrs={"class": "form-control"}),
            "graduation_month": Select(attrs={"class": "form-control"}),
            "graduation_year": TextInput(attrs={"class": "form-control", "type": "number"}),
            "major": TextInput(attrs={"class": "form-control"}),
            "degree": TextInput(attrs={"class": "form-control"}),
        }

class WorkExperienceForm(forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = ["company", "description"]
        widgets = {
            "company": TextInput(attrs={"class": "form-control"}),
            "description": Textarea(attrs={"class": "form-control"}),
        }

EducationFormSet = modelformset_factory(Education, form=EducationForm, extra=0, can_delete=True)
WorkExperienceFormSet = modelformset_factory(WorkExperience, form=WorkExperienceForm, extra=0, can_delete=True)

class CandidateSearchForm(forms.Form):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(), 
        required=False, 
        widget=forms.CheckboxSelectMultiple
    )
    location = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Atlanta, GA'})
    )
    project_keyword = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., React, Python, Machine Learning'}),
        help_text="Search project titles/descriptions"
    )
    match_all_skills = forms.BooleanField(
        required=False, 
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class MessageForm(forms.ModelForm):
    """Form for sending messages"""
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...'
            })
        }

class SaveSearchForm(forms.Form):
    """Form for saving a candidate search"""
    name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Python Developers in NYC'
        }),
        help_text="Give this search a memorable name"
    )
