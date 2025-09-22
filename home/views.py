from django.shortcuts import render

# Create your views here.
def index(request):
    template_data = {}
    template_data['title'] = 'Movies Store'
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
    """
    template_data = {'title': 'Jobs Near Me'}
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
    """
    Return jobs as JSON. Optional query params:
      - lat, lng (floats): user's location
      - radius_km (float): filter radius (default 50km)
    If lat/lng given, filters; otherwise returns all jobs.
    """
    qs = Job.objects.all()
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    radius_km = float(request.GET.get("radius_km", 50.0))

    jobs = []
    if lat and lng:
        try:
            user_lat = float(lat)
            user_lng = float(lng)
            for j in qs:
                d = _haversine_km(user_lat, user_lng, j.latitude, j.longitude)
                if d <= radius_km:
                    jobs.append({
                        "id": j.id,
                        "title": j.title,
                        "company": j.company,
                        "description": j.description,
                        "lat": j.latitude,
                        "lng": j.longitude,
                        "city": j.city,
                        "state": j.state,
                        "distance_km": round(d, 2),
                    })
        except ValueError:
            # Fallback: if bad lat/lng, just return all
            for j in qs:
                jobs.append({
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "description": j.description,
                    "lat": j.latitude,
                    "lng": j.longitude,
                    "city": j.city,
                    "state": j.state,
                })
    else:
        for j in qs:
            jobs.append({
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "description": j.description,
                "lat": j.latitude,
                "lng": j.longitude,
                "city": j.city,
                "state": j.state,
            })

    return JsonResponse({"jobs": jobs})

