from django.shortcuts import render

def home(request):
    return render(request, 'LearnPeak/index.html') 