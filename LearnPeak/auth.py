from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            
            # Redirect based on user type
            if email == 'admin@gmail.com':
                return redirect('admin_dashboard')
            elif hasattr(user, 'teacher'):
                return redirect('teacher_dashboard')
            elif hasattr(user, 'student'):
                return redirect('student_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'login.html') 