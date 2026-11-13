from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def inicio(request):
    if request.user.is_staff:
        return redirect("admin:index")
    return render(request, "pedido/inicio.html")
