from django.contrib import admin
from .models import ProductVersion, VisitSession, UXIssue

admin.site.register(ProductVersion)
admin.site.register(VisitSession)
admin.site.register(UXIssue)

