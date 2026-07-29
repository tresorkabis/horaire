from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/edit/', views.edit_schedule, name='create_schedule'),
    path('schedules/edit/<int:pk>/', views.edit_schedule, name='edit_schedule'),
    path('schedules/publish/<int:pk>/', views.publish_schedule, name='publish_schedule'),
    path('schedules/confirm/<int:pk>/', views.confirm_schedule, name='confirm_schedule'),
    path('schedules/annotate/<int:pk>/', views.annotate_schedule, name='annotate_schedule'),
    path('availability/', views.submit_availability, name='submit_availability'),
    path('personnel/', views.manage_personnel, name='manage_personnel'),
    path('personnel/<int:pk>/edit/', views.manage_personnel, name='edit_personnel'),
    path('personnel/<int:pk>/delete/', views.delete_personnel, name='delete_personnel'),
    path('referentiels/<str:type_objet>/', views.manage_referentiel, name='manage_referentiel'),
    path('referentiels/<str:type_objet>/<int:pk>/edit/', views.manage_referentiel, name='edit_referentiel'),
    path('referentiels/<str:type_objet>/<int:pk>/delete/', views.delete_referentiel, name='delete_referentiel'),
    path('students/', views.manage_students, name='manage_students'),
    path('students/<int:pk>/edit/', views.manage_students, name='edit_student'),
    path('students/<int:pk>/delete/', views.delete_student, name='delete_student'),
]
