from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from .forms import RefillBalanceForm
from .models import *
from .forms import UserForm, CartAddForm
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, UpdateView, View
from django.urls import reverse
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from huey.contrib.djhuey import task


class UserUpdateView(UpdateView):
    model = User
    fields = ('username', 'first_name', 'last_name', 'email')
    template_name = 'app_shop/profile.html'

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context['orders'] = Order.objects.prefetch_related('cart_good').filter(user=self.request.user).order_by('-date')
        return context

    def get_success_url(self):
        return reverse('profile', kwargs={'pk': self.request.user.pk})


class MainView(ListView):

    model = Good
    queryset = Good.objects.select_related('shop', 'category').defer('amount', 'activity_flag'
                                                                       ).filter(amount__gt=0, activity_flag='a')
    context_object_name = 'goods'
    template_name = 'app_shop/main.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(MainView, self).get_context_data(**kwargs)
        context['avg_price'] = Good.objects.only('price').aggregate(avg_price=Avg('price')).get('avg_price')
        context['add_form'] = CartAddForm()
        return context


class CartView(LoginRequiredMixin, View):
    login_url = 'login'
    def get(self, *args, **kwargs):
        try:
            cart =GoodCart.objects.select_related('user', 'good').defer('payment_flag', 'good__activity_flag', 'good__amount').\
                filter(user=self.request.user, payment_flag='n')
            total_price = sum([i_item.good.price * i_item.good_num for i_item in cart])
        except GoodCart.DoesNotExist:
            cart = None

        return render(self.request, template_name='app_shop/cart.html', context={
            'cart':cart,
            'total_price':total_price
        })
@require_POST
def pay(request, pk):

    profile = get_object_or_404(Profile, user=request.user)
    with transaction.atomic():
        cart = GoodCart.objects.filter(
            user = request.user,
            payment_flag = 'n'
        )
        amount = sum([i_item.good.price * i_item.good_num for i_item in cart])
        if amount > profile.balance:
            messages.add_message(request, messages.ERROR, 'Недостаточно средств! Пополните баланс!')
            return redirect('refill')
        order = Order.objects.create(user=request.user, amount=amount)
        order.cart_good.add(*cart)
        cart.update(payment_flag='p')
        profile.sub_balance(amount)
        profile.update_status(amount)
        order.save()
    messages.add_message(request, messages.SUCCESS, 'Оплата прошла успешно!')
    return redirect('main')



@require_POST
@login_required(login_url='login', redirect_field_name='main')
def add_good_to_cart(request, *args, **kwargs):
    good = get_object_or_404(Good, pk=kwargs['pk'])
    form = CartAddForm(request.POST)
    user_cart, created = GoodCart.objects.get_or_create(user=request.user, good=good, payment_flag='n')
    if form.is_valid():
        good_num = form.cleaned_data['good_num']
        if created:
            if good_num == 0 or good_num > good.amount:
                messages.add_message(request, messages.INFO, 'Invalid good num')
                return redirect('main')
            with transaction.atomic():
                user_cart.good_num = good_num
                user_cart.save()
                good.sub_amount(good_num)
        else:
            if good_num <= 0 or good_num > good.amount:
                messages.add_message(request, messages.INFO, 'Invalid good num')
                return redirect('main')
            with transaction.atomic():
                user_cart.good_num += good_num
                user_cart.save()

    return redirect('cart')

class CustomLoginView(LoginView):
    template_name = 'app_shop/login.html'
    next_page = 'main'

    def form_valid(self, form):
        response = super(CustomLoginView,self).form_valid(form)
        return response

class CustomLogoutView(LogoutView):
    template_name = 'app_shop/logout.html'
    next_page = 'main'

def register_view(request):
    user_form = UserForm()
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()
            Profile.objects.create(
                user=user
            )
            username = user_form.cleaned_data['username']
            password = user_form.cleaned_data['password1']
            auth_user = authenticate(username=username, password=password)
            login(request, auth_user)
            return redirect('main')
        return render(request, template_name='app_shop/register.html', context={'user_form': user_form, 'errors': user_form.error_messages})
    else:
        return render(request, template_name='app_shop/register.html', context={'user_form': user_form})


class RefillBalanceView(View):
    template_name = 'app_shop/refill.html'

    def get(self, request):
        form = RefillBalanceForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RefillBalanceForm(request.POST)
        if form.is_valid():
            card_number = form.cleaned_data['card_number']
            ending_card = form.cleaned_data['ending_card']
            cvv = form.cleaned_data['cvv']
            amount = form.cleaned_data['amount']
            user = Profile.objects.get(user=self.request.user)
            print(user)
            user.add_balance(amount)
            messages.success(request, 'Баланс успешно пополнен!')
            return redirect(reverse('main'))
        return render(request, self.template_name, {'form': form})

@require_POST
@login_required(login_url='login', redirect_field_name='main')
def delete_cart(request, item_id):
    item = get_object_or_404(GoodCart, id=item_id)
    good = item.good
    good.add_amount(item.good_num)
    item.delete()
    return redirect('cart')


