from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Meal, ScheduledMeal


class MealModelTest(TestCase):
    def test_meal_str(self):
        meal = Meal(name='Pasta')
        self.assertEqual(str(meal), 'Pasta')

    def test_scheduled_meal_str(self):
        meal = Meal(name='Salad')
        scheduled = ScheduledMeal(meal=meal, date='2024-01-15', meal_type='lunch')
        self.assertEqual(str(scheduled), 'Salad on 2024-01-15 (lunch)')


class MealAPITest(APITestCase):
    def setUp(self):
        self.meal = Meal.objects.create(name='Pizza', description='Cheesy', calories=800)

    def test_list_meals(self):
        url = reverse('meal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_meal(self):
        url = reverse('meal-list')
        data = {'name': 'Burger', 'description': 'Juicy', 'calories': 600}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Burger')

    def test_retrieve_meal(self):
        url = reverse('meal-detail', args=[self.meal.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Pizza')

    def test_update_meal(self):
        url = reverse('meal-detail', args=[self.meal.pk])
        data = {'name': 'Pizza Updated', 'calories': 900}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Pizza Updated')

    def test_delete_meal(self):
        url = reverse('meal-detail', args=[self.meal.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ScheduledMealAPITest(APITestCase):
    def setUp(self):
        self.meal = Meal.objects.create(name='Oatmeal', calories=300)
        self.scheduled = ScheduledMeal.objects.create(
            meal=self.meal, date='2024-01-15', meal_type='breakfast'
        )

    def test_list_scheduled_meals(self):
        url = reverse('scheduled-meal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_date(self):
        url = reverse('scheduled-meal-list')
        response = self.client.get(url, {'date': '2024-01-15'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_create_scheduled_meal(self):
        url = reverse('scheduled-meal-list')
        data = {'meal': self.meal.pk, 'date': '2024-01-16', 'meal_type': 'dinner'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_serializer_includes_meal_name(self):
        url = reverse('scheduled-meal-detail', args=[self.scheduled.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['meal_name'], 'Oatmeal')
