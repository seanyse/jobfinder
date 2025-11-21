from django.shortcuts import render
from jobs.models import Job
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from math import radians, sin, cos, asin, sqrt
from decimal import InvalidOperation

def is_seeker(user):
    return user.is_authenticated and getattr(user, "role", None) == "seeker"

# Create your views here.
def index(request):
    template_data = {}
    template_data['title'] = 'Careers'
    return render(request, 'home/index.html', {
        'template_data': template_data})

def about(request):
    template_data = {}
    template_data['title'] = 'About'
    return render(request, 'home/about.html', {'template_data': template_data})

def jobs_map(request):
    """
    Page with the interactive map. The browser will ask for the user's location,
    center the map, and fetch markers from /api/jobs/.
    Accessible to both job seekers and recruiters.
    """
    # Get user's preferred commute radius from their profile (for seekers)
    preferred_radius = 50  # default
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        preferred_radius = request.user.profile.commute_radius
    
    template_data = {
        'title': 'Jobs Near Me',
        'preferred_radius': preferred_radius
    }
    return render(request, 'home/jobs_map.html', {'template_data': template_data})

# --- Helpers for distance filtering ---
def _haversine_km(lat1, lon1, lat2, lon2):
    # Calculate the great circle distance between two points (km)
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))
    
def jobs_geojson(request):
    # /api/jobs/?lat=33.7756&lng=-84.3963&radius_km=50
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        lat = float(request.GET.get("lat"))
        lng = float(request.GET.get("lng"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "lat/lng required"}, status=400)

    try:
        radius_km = float(request.GET.get("radius_km", "50"))
    except (TypeError, ValueError):
        radius_km = 50.0

    qs = Job.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))

    features = []
    for j in qs:
        try:
            jlat = float(j.latitude); jlng = float(j.longitude)
        except (TypeError, ValueError, InvalidOperation):
            continue
        
        distance = haversine(lat, lng, jlat, jlng)
        if distance <= radius_km:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [jlng, jlat]},
                "properties": {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "distance_km": round(distance, 2),
                    "detail_url": request.build_absolute_uri(f"/jobs/{j.id}/"),
                },
            })

    return JsonResponse({"type": "FeatureCollection", "features": features})

