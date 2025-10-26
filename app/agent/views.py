from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

# Create your views here.

@ensure_csrf_cookie
def chat_ui(request):
    return render(request, "chat_ui.html")

def handle_user_input(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "")
        # Simulate a response from the model
        model_response = f"You said: {user_message}. This is a simulated response."
        return JsonResponse({"response": model_response})
    return JsonResponse({"error": "Invalid request method."}, status=400)
