from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_only(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated and has admin credentials
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('login')
        
        if request.user.email != 'admin@gmail.com':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
            
        return view_func(request, *args, **kwargs)
    return wrapper 